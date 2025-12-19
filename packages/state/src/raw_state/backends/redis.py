"""Redis backend for state management."""

from typing import Any

from pydantic import Field
from redis.asyncio import ConnectionPool, Redis

from raw_state.backends.base import StateBackend, StateConfig


class RedisConfig(StateConfig):
    """Configuration for Redis state backend.

    Supports connection pooling and SSL for production deployments.
    """

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    ssl: bool = False
    max_connections: int = 10
    decode_responses: bool = True

    class Config:
        frozen = True


class RedisBackend:
    """Redis implementation of StateBackend protocol.

    Uses connection pooling for efficient resource usage. Supports
    all standard Redis operations including TTL and pattern matching.
    """

    def __init__(self, config: RedisConfig):
        """Initialize Redis backend with configuration.

        Args:
            config: Redis connection configuration

        Note:
            Connection pool is created lazily on first use via _ensure_client.
        """
        self.config = config
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    async def _ensure_client(self) -> Redis:
        """Ensure Redis client is initialized with connection pool.

        Lazy initialization allows configuration without immediate connection.
        Connection pool is reused across all operations for efficiency.
        """
        if self._client is None:
            self._pool = ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                ssl=self.config.ssl,
                max_connections=self.config.max_connections,
                decode_responses=self.config.decode_responses,
            )
            self._client = Redis(connection_pool=self._pool)
        return self._client

    async def get(self, key: str) -> str | None:
        """Retrieve value by key.

        Args:
            key: The state key to retrieve

        Returns:
            The value as a string, or None if not found
        """
        client = await self._ensure_client()
        value = await client.get(key)
        return value if value is None else str(value)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Store value with optional TTL.

        Args:
            key: The state key to store
            value: The value to store as a string
            ttl: Optional time-to-live in seconds
        """
        client = await self._ensure_client()
        if ttl is not None:
            await client.setex(key, ttl, value)
        else:
            await client.set(key, value)

    async def delete(self, key: str) -> bool:
        """Delete key from state.

        Args:
            key: The state key to delete

        Returns:
            True if key was deleted, False if not found
        """
        client = await self._ensure_client()
        result = await client.delete(key)
        return result > 0

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: The state key to check

        Returns:
            True if key exists, False otherwise
        """
        client = await self._ensure_client()
        result = await client.exists(key)
        return result > 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key.

        Args:
            key: The state key to expire
            ttl: Time-to-live in seconds

        Returns:
            True if TTL was set, False if key not found
        """
        client = await self._ensure_client()
        result = await client.expire(key, ttl)
        return bool(result)

    async def keys(self, pattern: str = "*") -> list[str]:
        """List keys matching pattern.

        Args:
            pattern: Pattern to match (default: "*" for all keys)

        Returns:
            List of matching key names
        """
        client = await self._ensure_client()
        keys = await client.keys(pattern)
        return [str(k) for k in keys]

    async def close(self) -> None:
        """Close Redis connection pool.

        Should be called during application shutdown to properly
        release resources.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None

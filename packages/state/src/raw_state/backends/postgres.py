"""PostgreSQL backend for state management."""

from datetime import datetime, timedelta, timezone

import asyncpg
from pydantic import Field

from raw_state.backends.base import StateConfig


class PostgresConfig(StateConfig):
    """Configuration for PostgreSQL state backend.

    Uses connection pooling for efficient database access.
    """

    dsn: str = Field(
        ...,
        description="PostgreSQL connection string (e.g., postgresql://user:pass@host/db)",
    )
    min_pool_size: int = 2
    max_pool_size: int = 10
    table_name: str = "raw_state"

    class Config:
        frozen = True


class PostgresBackend:
    """PostgreSQL implementation of StateBackend protocol.

    Stores state in a key-value table with TTL support. Table schema:
    - key: VARCHAR PRIMARY KEY
    - value: TEXT
    - expires_at: TIMESTAMP (NULL for no expiration)
    - created_at: TIMESTAMP
    - updated_at: TIMESTAMP

    The table is created automatically on first connection if it doesn't exist.
    """

    def __init__(self, config: PostgresConfig):
        """Initialize PostgreSQL backend with configuration.

        Args:
            config: PostgreSQL connection configuration

        Note:
            Connection pool is created lazily on first use via _ensure_pool.
        """
        self.config = config
        self._pool: asyncpg.Pool | None = None

    async def _ensure_pool(self) -> asyncpg.Pool:
        """Ensure connection pool is initialized and table exists.

        Lazy initialization allows configuration without immediate connection.
        Creates the state table if it doesn't exist.
        """
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.config.dsn,
                min_size=self.config.min_pool_size,
                max_size=self.config.max_pool_size,
            )
            await self._create_table_if_needed()
        return self._pool

    async def _create_table_if_needed(self) -> None:
        """Create state table if it doesn't exist.

        Uses CREATE TABLE IF NOT EXISTS for idempotency. Includes an index
        on expires_at for efficient cleanup of expired keys.
        """
        if self._pool is None:
            return

        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.config.table_name} (
                    key VARCHAR PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
            # Index for efficient TTL cleanup queries
            await conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{self.config.table_name}_expires
                ON {self.config.table_name}(expires_at)
                WHERE expires_at IS NOT NULL
                """
            )

    async def _cleanup_expired(self, conn: asyncpg.Connection) -> None:
        """Remove expired keys from database.

        Called during get operations to maintain data consistency.
        This ensures expired keys are eventually removed even without
        explicit delete operations.
        """
        await conn.execute(
            f"""
            DELETE FROM {self.config.table_name}
            WHERE expires_at IS NOT NULL AND expires_at <= NOW()
            """
        )

    async def get(self, key: str) -> str | None:
        """Retrieve value by key.

        Args:
            key: The state key to retrieve

        Returns:
            The value as a string, or None if not found or expired
        """
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            # Clean up expired keys first
            await self._cleanup_expired(conn)

            result = await conn.fetchrow(
                f"""
                SELECT value FROM {self.config.table_name}
                WHERE key = $1
                AND (expires_at IS NULL OR expires_at > NOW())
                """,
                key,
            )
            return result["value"] if result else None

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Store value with optional TTL.

        Args:
            key: The state key to store
            value: The value to store as a string
            ttl: Optional time-to-live in seconds
        """
        pool = await self._ensure_pool()
        expires_at = None
        if ttl is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.config.table_name} (key, value, expires_at, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (key)
                DO UPDATE SET value = $2, expires_at = $3, updated_at = NOW()
                """,
                key,
                value,
                expires_at,
            )

    async def delete(self, key: str) -> bool:
        """Delete key from state.

        Args:
            key: The state key to delete

        Returns:
            True if key was deleted, False if not found
        """
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                f"""
                DELETE FROM {self.config.table_name}
                WHERE key = $1
                """,
                key,
            )
            # result is in format "DELETE N" where N is number of rows
            return int(result.split()[-1]) > 0

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: The state key to check

        Returns:
            True if key exists and not expired, False otherwise
        """
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                f"""
                SELECT EXISTS(
                    SELECT 1 FROM {self.config.table_name}
                    WHERE key = $1
                    AND (expires_at IS NULL OR expires_at > NOW())
                )
                """,
                key,
            )
            return bool(result)

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key.

        Args:
            key: The state key to expire
            ttl: Time-to-live in seconds

        Returns:
            True if TTL was set, False if key not found
        """
        pool = await self._ensure_pool()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        async with pool.acquire() as conn:
            result = await conn.execute(
                f"""
                UPDATE {self.config.table_name}
                SET expires_at = $2, updated_at = NOW()
                WHERE key = $1
                AND (expires_at IS NULL OR expires_at > NOW())
                """,
                key,
                expires_at,
            )
            return int(result.split()[-1]) > 0

    async def keys(self, pattern: str = "*") -> list[str]:
        """List keys matching pattern.

        Args:
            pattern: Pattern to match (default: "*" for all keys)
                    Uses SQL LIKE syntax (% for wildcard, _ for single char)
                    Automatically converts Redis-style * to SQL %

        Returns:
            List of matching key names
        """
        pool = await self._ensure_pool()

        # Convert Redis-style pattern to SQL LIKE pattern
        sql_pattern = pattern.replace("*", "%").replace("?", "_")

        async with pool.acquire() as conn:
            # Clean up expired keys first
            await self._cleanup_expired(conn)

            rows = await conn.fetch(
                f"""
                SELECT key FROM {self.config.table_name}
                WHERE key LIKE $1
                AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY key
                """,
                sql_pattern,
            )
            return [row["key"] for row in rows]

    async def close(self) -> None:
        """Close PostgreSQL connection pool.

        Should be called during application shutdown to properly
        release database connections.
        """
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

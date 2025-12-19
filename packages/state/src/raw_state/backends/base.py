"""Base protocol and configuration for state backends."""

from typing import Protocol

from pydantic import BaseModel


class StateConfig(BaseModel):
    """Base configuration for state backends.

    Subclasses should add their specific connection parameters.
    """

    class Config:
        frozen = True  # Immutability for configuration objects


class StateBackend(Protocol):
    """Protocol for key-value state persistence.

    Defines async methods for storing and retrieving state across
    conversations and workflows. Implementations can use Redis,
    PostgreSQL, or other storage systems.
    """

    async def get(self, key: str) -> str | None:
        """Retrieve value by key.

        Args:
            key: The state key to retrieve

        Returns:
            The value as a string, or None if not found
        """
        ...

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Store value with optional TTL.

        Args:
            key: The state key to store
            value: The value to store as a string
            ttl: Optional time-to-live in seconds
        """
        ...

    async def delete(self, key: str) -> bool:
        """Delete key from state.

        Args:
            key: The state key to delete

        Returns:
            True if key was deleted, False if not found
        """
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: The state key to check

        Returns:
            True if key exists, False otherwise
        """
        ...

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key.

        Args:
            key: The state key to expire
            ttl: Time-to-live in seconds

        Returns:
            True if TTL was set, False if key not found
        """
        ...

    async def keys(self, pattern: str = "*") -> list[str]:
        """List keys matching pattern.

        Args:
            pattern: Pattern to match (default: "*" for all keys)

        Returns:
            List of matching key names
        """
        ...

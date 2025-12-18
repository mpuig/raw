"""Storage backend protocol for persistence."""

from typing import Protocol


class StorageBackend(Protocol):
    """Protocol for artifact and state persistence.

    Implementations can use local filesystem, S3, databases, etc.
    """

    async def read(self, key: str) -> bytes | None:
        """Read data from storage by key."""
        ...

    async def write(self, key: str, data: bytes) -> None:
        """Write data to storage with given key."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete data from storage. Returns True if deleted."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists in storage."""
        ...

    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys matching prefix."""
        ...

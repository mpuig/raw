"""Storage abstraction for workflow artifacts and state.

Provides a protocol for storing and retrieving workflow data, enabling:
- Local filesystem storage (default)
- Cloud storage (S3, GCS)
- Database storage

Note: Protocol is in raw_runtime.protocols.storage,
      Implementations are in raw_runtime.drivers.storage.
      This module re-exports for backwards compatibility.
"""

from raw_runtime.container import RuntimeContainer
from raw_runtime.drivers.storage import (
    FileSystemStorage,
    MemoryStorage,
    _serialize_for_storage,
)
from raw_runtime.protocols.storage import StorageBackend

# Public alias for backwards compatibility
serialize_for_storage = _serialize_for_storage


# Backward-compatible accessors that delegate to RuntimeContainer


def get_storage() -> StorageBackend:
    """Get the current storage backend.

    Returns FileSystemStorage by default if no storage is set.
    """
    return RuntimeContainer.storage()


def set_storage(storage: StorageBackend | None) -> None:
    """Set the global storage backend."""
    RuntimeContainer.set_storage(storage)


__all__ = [
    "StorageBackend",
    "FileSystemStorage",
    "MemoryStorage",
    "get_storage",
    "set_storage",
    "serialize_for_storage",
]

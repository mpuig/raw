"""RAW State - State management backends for Redis and PostgreSQL.

This package provides state persistence for conversations and workflows:
- StateBackend protocol for loose coupling
- Redis and PostgreSQL implementations with connection pooling
- SessionManager for high-level session management with TTL support
"""

__version__ = "0.1.0"

# Re-export commonly used items at package level
from raw_state.backends import (
    PostgresBackend,
    PostgresConfig,
    RedisBackend,
    RedisConfig,
    StateBackend,
    StateConfig,
)
from raw_state.session import Session, SessionManager

__all__ = [
    # Backends
    "StateBackend",
    "StateConfig",
    "RedisBackend",
    "RedisConfig",
    "PostgresBackend",
    "PostgresConfig",
    # Session management
    "Session",
    "SessionManager",
]

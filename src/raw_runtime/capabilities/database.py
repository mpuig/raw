"""Database capability - Execute database queries.

Supports PostgreSQL, MySQL, SQLite, and other databases via SQLAlchemy.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.capability import Capability, CapabilityEvent


class DatabaseCapability(Capability):
    """Database operations capability.

    Usage:
        result = await self.capability("database").call(
            query="SELECT * FROM users WHERE id = :id",
            params={"id": 123},
            connection="default",
        )
        users = result.data["rows"]
    """

    name: ClassVar[str] = "database"
    description: ClassVar[str] = "Execute database queries"
    triggers: ClassVar[list[str]] = []

    async def run(self, **config: Any) -> AsyncIterator[CapabilityEvent]:
        """Execute a database query.

        Args:
            query: SQL query string
            params: Query parameters (for parameterized queries)
            connection: Connection name from config (default: "default")
            fetch: Fetch mode ("all", "one", "none") - default "all"

        Yields:
            CapabilityEvent with types: started, completed (with rows), failed
        """
        raise NotImplementedError(
            "Database capability not implemented. "
            "Configure database connections to use this capability."
        )
        yield

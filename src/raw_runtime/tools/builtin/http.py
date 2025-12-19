"""HTTP capability - Make HTTP requests.

General-purpose HTTP client for API calls.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.tools.base import Tool, ToolEvent


class HttpTool(Tool):
    """HTTP request capability.

    Usage:
        # GET request
        result = await self.capability("http").call(
            method="GET",
            url="https://api.example.com/users",
            headers={"Authorization": "Bearer xxx"},
        )

        # POST request
        result = await self.capability("http").call(
            method="POST",
            url="https://api.example.com/users",
            json={"name": "John", "email": "john@example.com"},
        )
    """

    name: ClassVar[str] = "http"
    description: ClassVar[str] = "Make HTTP requests"
    triggers: ClassVar[list[str]] = ["webhook.received"]

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        """Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            url: Request URL
            headers: Request headers
            params: URL query parameters
            json: JSON body (for POST/PUT/PATCH)
            data: Form data (for POST/PUT/PATCH)
            timeout: Request timeout in seconds (default: 30)

        Yields:
            ToolEvent with types: started, completed (with response), failed
        """
        raise NotImplementedError(
            "HTTP capability not implemented. This capability requires an HTTP client library."
        )
        yield

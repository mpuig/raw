"""Search capability - Web and custom search.

Supports Google Search, Bing, and custom search indexes.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.capability import Capability, CapabilityEvent


class SearchCapability(Capability):
    """Web search capability.

    Usage:
        result = await self.capability("search").call(
            query="best practices for RAW workflows",
            num_results=10,
        )
        for item in result.data["results"]:
            print(item["title"], item["url"])
    """

    name: ClassVar[str] = "search"
    description: ClassVar[str] = "Web search (Google, Bing, custom)"
    triggers: ClassVar[list[str]] = []

    async def run(self, **config: Any) -> AsyncIterator[CapabilityEvent]:
        """Perform a web search.

        Args:
            query: Search query
            num_results: Number of results to return (default: 10)
            site: Limit search to a specific site
            date_range: Date range filter ("day", "week", "month", "year")
            provider: Provider ("google", "bing", "duckduckgo")

        Yields:
            CapabilityEvent with types: started, completed (with results), failed
        """
        raise NotImplementedError(
            "Search capability not implemented. "
            "Configure search API credentials to use this capability."
        )
        yield

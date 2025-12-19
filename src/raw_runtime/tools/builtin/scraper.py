"""Scraper capability - Web scraping.

Extracts data from web pages using CSS selectors or XPath.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.tools.base import Tool, ToolEvent


class ScraperTool(Tool):
    """Web scraping capability.

    Usage:
        result = await self.capability("scraper").call(
            url="https://example.com/products",
            selectors={
                "title": "h1.product-title",
                "price": ".price-value",
                "description": ".product-desc",
            },
        )
        products = result.data["items"]
    """

    name: ClassVar[str] = "scraper"
    description: ClassVar[str] = "Web scraping and data extraction"
    triggers: ClassVar[list[str]] = []

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        """Scrape data from a web page.

        Args:
            url: URL to scrape
            selectors: Dict of field names to CSS selectors
            xpath: Dict of field names to XPath expressions (alternative to selectors)
            wait_for: CSS selector to wait for before scraping
            javascript: Whether to render JavaScript (requires browser)
            headers: Custom HTTP headers

        Yields:
            ToolEvent with types: started, completed, failed
        """
        raise NotImplementedError(
            "Scraper capability not implemented. "
            "Install scraping dependencies to use this capability."
        )
        yield

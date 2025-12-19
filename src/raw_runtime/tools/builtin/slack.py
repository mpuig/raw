"""Slack capability - Send messages to Slack.

Supports channels, DMs, threads, and rich message formatting.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.tools.base import Tool, ToolEvent


class SlackTool(Tool):
    """Slack messaging capability.

    Usage:
        result = await self.capability("slack").call(
            channel="#general",
            text="Hello from RAW!",
            blocks=[...],  # optional Block Kit blocks
        )
    """

    name: ClassVar[str] = "slack"
    description: ClassVar[str] = "Send messages to Slack channels and users"
    triggers: ClassVar[list[str]] = ["slack.message.received", "slack.event"]

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        """Send a Slack message.

        Args:
            channel: Channel name or ID (e.g., "#general" or "C1234567890")
            text: Message text
            blocks: Optional Block Kit blocks for rich formatting
            thread_ts: Optional thread timestamp for replies
            unfurl_links: Whether to unfurl URLs (default: True)

        Yields:
            ToolEvent with types: started, completed, failed
        """
        raise NotImplementedError(
            "Slack capability not implemented. Configure Slack API token to use this capability."
        )
        yield

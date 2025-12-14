"""Converse capability - AI conversation handling.

Integrates with Converse for handling AI-powered conversations.
Supports text and voice modes with tool execution.

Triggers:
    - converse.conversation.ended: When a conversation completes
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.capability import Capability, CapabilityEvent


class ConverseCapability(Capability):
    """AI conversation handling capability.

    Connects to Converse to handle multi-turn conversations with
    tool execution and context management.

    Usage:
        async for event in self.capability("converse").run(
            bot="support",
            context={"customer_id": "123"},
            transport="http",  # or "twilio", "websocket"
        ):
            if event.type == "message":
                print(event.data["text"])
            elif event.type == "completed":
                outcome = event.data.get("outcome")
    """

    name: ClassVar[str] = "converse"
    description: ClassVar[str] = "AI conversation handling via Converse"
    triggers: ClassVar[list[str]] = ["converse.conversation.ended"]

    async def run(self, **config: Any) -> AsyncIterator[CapabilityEvent]:
        """Start or continue a conversation.

        Args:
            bot: Bot name to use
            context: Optional context dict to pass to the bot
            transport: Transport mode ("http", "twilio", "websocket")
            conversation_id: Optional existing conversation ID to continue
            message: Optional message to send (for continuing conversations)

        Yields:
            CapabilityEvent with types: started, message, tool_call, completed, failed
        """
        raise NotImplementedError(
            "Converse capability not implemented. "
            "Install and configure Converse to use this capability."
        )
        yield  # Make this a generator

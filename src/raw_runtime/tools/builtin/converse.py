"""Converse tool - AI conversation handling.

Integrates with Converse for handling AI-powered conversations.
Supports text and voice modes with tool execution.

Requires: pip install converse

Triggers:
    - converse.conversation.ended: When a conversation completes
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.tools.base import Tool, ToolEvent, ToolEventType


class ConverseTool(Tool):
    """AI conversation handling tool.

    Connects to Converse to handle multi-turn conversations with
    tool execution and context management.

    Requires the `converse` package to be installed.

    Usage:
        # Single turn
        async for event in self.tool("converse").run(
            bot="support",
            message="What's my account balance?",
        ):
            if event.type == ToolEventType.MESSAGE:
                print(event.data["text"])

        # Full conversation loop
        async for event in self.tool("converse").run(
            bot="support",
            context={"customer_id": "123"},
            greeting=True,
        ):
            ...
    """

    name: ClassVar[str] = "converse"
    description: ClassVar[str] = "AI conversation handling via Converse"
    triggers: ClassVar[list[str]] = ["converse.conversation.ended"]

    async def run(self, bot: str, **config: Any) -> AsyncIterator[ToolEvent]:
        """Start or continue a conversation.

        Args:
            bot: Bot name to use (must exist in bots/ directory)
            message: Optional message to process (for single turn)
            context: Optional context dict to pass to the bot
            greeting: Whether to generate initial greeting (default: False)
            state: Optional EngineState to restore from

        Yields:
            ToolEvent with types:
            - started: Conversation initialized
            - message: Text from assistant (streaming chunks)
            - custom: Tool calls and results
            - completed: Conversation turn or session ended
            - failed: Error occurred
        """
        try:
            from converse import (
                LiteLLMDriver,
                ToolExecutor,
                TurnComplete,
                create_engine,
                load_bot,
            )
        except ImportError as e:
            raise NotImplementedError(
                "Converse not installed. Install with: pip install converse"
            ) from e

        # Load bot and create engine
        loaded_bot = load_bot(bot)
        executor = ToolExecutor(loaded_bot.skill_registry)
        driver = LiteLLMDriver()

        engine = create_engine(
            bot=loaded_bot,
            executor=executor,
            driver=driver,
            state=config.get("state"),
        )

        yield self._emit_started(bot=bot, config=config)

        try:
            # Generate greeting if requested
            if config.get("greeting", False):
                async for event in engine.generate_greeting():
                    yield self._map_engine_event(event)

            # Process message if provided
            message = config.get("message")
            if message:
                async for event in engine.process_turn(message):
                    yield self._map_engine_event(event)

                    # Check for conversation end
                    if isinstance(event, TurnComplete) and event.end_conversation:
                        yield self._emit_completed(
                            outcome="ended",
                            conversation_ended=True,
                        )
                        return

            # If no message, just return after greeting
            yield self._emit_completed(
                outcome="turn_complete",
                conversation_ended=engine.conversation_ended,
            )

        except Exception as e:
            yield self._emit_failed(str(e))

    def _map_engine_event(self, event: Any) -> ToolEvent:
        """Map Converse EngineEvent to RAW ToolEvent."""
        from converse import (
            TextChunk,
            ToolCallEvent,
            ToolResultEvent,
            TurnComplete,
        )

        if isinstance(event, TextChunk):
            return self._emit_message(
                role="assistant",
                text=event.text,
                chunk=True,
            )
        elif isinstance(event, ToolCallEvent):
            return ToolEvent(
                type=ToolEventType.CUSTOM,
                tool=self.name,
                data={
                    "event": "tool_call",
                    "tool_name": event.name,
                    "arguments": event.arguments,
                    "call_id": event.call_id,
                },
            )
        elif isinstance(event, ToolResultEvent):
            return ToolEvent(
                type=ToolEventType.CUSTOM,
                tool=self.name,
                data={
                    "event": "tool_result",
                    "tool_name": event.name,
                    "result": event.result,
                    "call_id": event.call_id,
                },
            )
        elif isinstance(event, TurnComplete):
            return ToolEvent(
                type=ToolEventType.CUSTOM,
                tool=self.name,
                data={
                    "event": "turn_complete",
                    "end_conversation": event.end_conversation,
                },
            )
        else:
            # Unknown event type
            return ToolEvent(
                type=ToolEventType.CUSTOM,
                tool=self.name,
                data={"event": "unknown", "raw": str(event)},
            )

"""Conversation events for streaming output."""

from typing import Any

from raw_core.events.base import Event


class TextChunk(Event):
    """Streaming text fragment for real-time display."""

    text: str


class ToolCallEvent(Event):
    """Emitted when LLM requests a tool execution."""

    name: str
    arguments: dict[str, Any]
    call_id: str


class ToolResultEvent(Event):
    """Emitted after tool execution completes."""

    name: str
    result: dict[str, Any]
    call_id: str


class TurnComplete(Event):
    """Signals turn end. Callers check end_conversation for termination."""

    end_conversation: bool = False

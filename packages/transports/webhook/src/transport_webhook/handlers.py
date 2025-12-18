"""Webhook event handlers for processing conversation events.

This module provides the WebhookHandler class that manages the lifecycle of
webhook-based conversations, including message processing and event streaming.
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from raw_bot import ConversationEngine
from raw_core import TextChunk, ToolCallEvent, ToolResultEvent, TurnComplete


class ConversationStatus(str, Enum):
    """Status of a conversation session."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"


class ConversationState(BaseModel):
    """Immutable snapshot of conversation state."""

    id: str
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    message_count: int
    outcome: str | None = None
    error: str | None = None


class WebhookHandler:
    """Manages a single webhook-based conversation.

    Wraps a ConversationEngine and provides methods for processing messages
    and collecting responses. This decouples the HTTP transport layer from
    the core conversation logic.

    Why: Separates concerns between HTTP handling (router) and conversation
    management (handler), following single responsibility principle.
    """

    def __init__(self, conversation_id: str, engine: ConversationEngine):
        """Initialize webhook handler.

        Args:
            conversation_id: Unique identifier for this conversation.
            engine: Conversation engine instance for this session.
        """
        self.id = conversation_id
        self.engine = engine
        self._state = ConversationState(
            id=conversation_id,
            status=ConversationStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            message_count=0,
        )
        self._event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    @property
    def state(self) -> ConversationState:
        """Get current conversation state snapshot."""
        return self._state

    async def process_message(self, text: str) -> str:
        """Process a user message and return the complete response.

        Streams the conversation turn and accumulates text chunks into a
        single response string. Handles tool calls transparently.

        Args:
            text: User message text to process.

        Returns:
            Complete bot response as a single string.

        Raises:
            Exception: If conversation processing fails.
        """
        response_parts: list[str] = []

        try:
            async for event in self.engine.process_turn(text):
                # Queue event for streaming (if anyone is listening)
                await self._event_queue.put(self._serialize_event(event))

                if isinstance(event, TextChunk):
                    response_parts.append(event.text)
                elif isinstance(event, TurnComplete):
                    if event.end_conversation:
                        self._update_status(ConversationStatus.COMPLETED)
                        # Check for outcome in last tool result
                        messages = self.engine.messages
                        for msg in reversed(messages):
                            if msg.get("role") == "tool":
                                content = msg.get("content", "")
                                if isinstance(content, str) and "outcome" in content:
                                    try:
                                        import json

                                        result = json.loads(content)
                                        if isinstance(result, dict):
                                            self._state = ConversationState(
                                                **{
                                                    **self._state.model_dump(),
                                                    "outcome": result.get("outcome"),
                                                }
                                            )
                                    except (json.JSONDecodeError, ValueError):
                                        pass
                                    break

            self._state = ConversationState(
                **{
                    **self._state.model_dump(),
                    "message_count": self._state.message_count + 1,
                    "updated_at": datetime.now(),
                }
            )
            return "".join(response_parts)

        except Exception as e:
            self._update_status(ConversationStatus.ERROR, error=str(e))
            raise

    async def generate_greeting(self) -> str | None:
        """Generate initial greeting from bot if configured.

        Returns:
            Greeting text if bot is configured to greet first, None otherwise.
        """
        if not self.engine.config.greeting_first:
            return None

        response_parts: list[str] = []
        async for event in self.engine.generate_greeting():
            await self._event_queue.put(self._serialize_event(event))
            if isinstance(event, TextChunk):
                response_parts.append(event.text)

        return "".join(response_parts) if response_parts else None

    async def get_events(self, timeout: float = 30.0) -> dict[str, Any] | None:
        """Get next event from the queue with timeout.

        Used for WebSocket streaming of real-time events.

        Args:
            timeout: Maximum time to wait for an event in seconds.

        Returns:
            Event dictionary if available, None if timeout.
        """
        try:
            return await asyncio.wait_for(self._event_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def end(self, reason: str = "user_ended") -> None:
        """End the conversation.

        Args:
            reason: Reason for ending the conversation.
        """
        self._update_status(ConversationStatus.COMPLETED, outcome=reason)

    def _update_status(
        self, status: ConversationStatus, outcome: str | None = None, error: str | None = None
    ) -> None:
        """Update conversation status and metadata.

        Why: Centralizes state updates to ensure consistency and proper
        timestamp tracking.
        """
        self._state = ConversationState(
            **{
                **self._state.model_dump(),
                "status": status,
                "updated_at": datetime.now(),
                "outcome": outcome or self._state.outcome,
                "error": error or self._state.error,
            }
        )

    def _serialize_event(self, event: Any) -> dict[str, Any]:
        """Serialize conversation event for API transport.

        Why: Converts typed event objects to JSON-serializable dictionaries
        suitable for HTTP/WebSocket transmission.
        """
        if isinstance(event, TextChunk):
            return {"type": "text_chunk", "text": event.text}
        elif isinstance(event, ToolCallEvent):
            return {
                "type": "tool_call",
                "name": event.name,
                "arguments": event.arguments,
                "call_id": event.call_id,
            }
        elif isinstance(event, ToolResultEvent):
            return {
                "type": "tool_result",
                "name": event.name,
                "result": event.result,
                "call_id": event.call_id,
            }
        elif isinstance(event, TurnComplete):
            return {
                "type": "turn_complete",
                "end_conversation": event.end_conversation,
            }
        else:
            return {"type": "unknown", "data": str(event)}


class ConversationManager:
    """Manages multiple webhook conversation sessions.

    Provides a registry for active conversations, enabling lookup by ID
    and lifecycle management across multiple concurrent webhook requests.

    Why: Centralizes session management, preventing duplicate conversations
    and enabling proper cleanup of completed sessions.
    """

    def __init__(self) -> None:
        """Initialize conversation manager."""
        self._conversations: dict[str, WebhookHandler] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        engine: ConversationEngine,
        conversation_id: str | None = None,
    ) -> WebhookHandler:
        """Create a new conversation session.

        Args:
            engine: Conversation engine instance for this session.
            conversation_id: Optional custom conversation ID. If not provided,
                a UUID will be generated.

        Returns:
            New WebhookHandler instance.
        """
        async with self._lock:
            conv_id = conversation_id or str(uuid.uuid4())
            if conv_id in self._conversations:
                raise ValueError(f"Conversation {conv_id} already exists")

            handler = WebhookHandler(conv_id, engine)
            self._conversations[conv_id] = handler
            return handler

    async def get(self, conversation_id: str) -> WebhookHandler | None:
        """Get conversation by ID.

        Args:
            conversation_id: Conversation identifier.

        Returns:
            WebhookHandler if found, None otherwise.
        """
        return self._conversations.get(conversation_id)

    async def list_all(self) -> list[ConversationState]:
        """List all conversation states.

        Returns:
            List of conversation state snapshots.
        """
        return [conv.state for conv in self._conversations.values()]

    async def remove(self, conversation_id: str) -> None:
        """Remove conversation from registry.

        Args:
            conversation_id: Conversation identifier.
        """
        async with self._lock:
            self._conversations.pop(conversation_id, None)

    async def cleanup_completed(self, max_age_seconds: int = 3600) -> int:
        """Remove completed conversations older than max_age.

        Why: Prevents memory leaks from accumulating completed sessions.

        Args:
            max_age_seconds: Maximum age in seconds for completed conversations.

        Returns:
            Number of conversations removed.
        """
        async with self._lock:
            now = datetime.now()
            to_remove = [
                conv_id
                for conv_id, conv in self._conversations.items()
                if conv.state.status == ConversationStatus.COMPLETED
                and (now - conv.state.updated_at).total_seconds() > max_age_seconds
            ]

            for conv_id in to_remove:
                del self._conversations[conv_id]

            return len(to_remove)

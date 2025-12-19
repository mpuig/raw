"""Tool base class and events for RAW workflows.

Tools are reusable actions that workflows can call. They provide a uniform
async iterator interface for both simple functions and complex services.

Tools can be:
- Pre-defined: Ship with RAW (email, slack, converse, etc.)
- Programmatic: Created by Claude Code during workflow definition
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from enum import Enum
from typing import Any, ClassVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ToolEventType(str, Enum):
    """Standard tool event types."""

    # Lifecycle
    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    FAILED = "failed"

    # Communication (for streaming tools like converse)
    MESSAGE = "message"
    CHUNK = "chunk"

    # Long-running
    WAITING = "waiting"
    RESUMED = "resumed"

    # Custom
    CUSTOM = "custom"


class ToolEvent(BaseModel):
    """Event emitted by tools during execution.

    Events provide real-time feedback from tool execution,
    enabling progress tracking, streaming responses, and error handling.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    type: ToolEventType
    tool: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ToolResult(BaseModel):
    """Final result from a tool execution."""

    model_config = ConfigDict(frozen=True)

    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_seconds: float = 0.0


class Tool(ABC):
    """Base class for all tools.

    Tools wrap actions (simple functions or complex services) with a
    uniform interface. They can be:
    - Request/response (HTTP, database queries)
    - Long-running (conversations, file processing)
    - Event-triggered (webhooks, incoming calls)

    Subclass this and implement `run()` to create a tool.
    """

    name: ClassVar[str]
    description: ClassVar[str]
    triggers: ClassVar[list[str]] = []

    @abstractmethod
    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        """Execute the tool with given configuration.

        Yields events during execution, ending with a COMPLETED or FAILED event.

        Args:
            **config: Tool-specific configuration parameters.

        Yields:
            ToolEvent instances representing execution progress.
        """
        ...

    async def call(self, **config: Any) -> ToolResult:
        """Execute tool and return final result.

        Convenience method for simple request/response patterns.
        Consumes all events and returns the final result.
        """
        started_at = datetime.now(timezone.utc)
        last_event: ToolEvent | None = None
        result_data: dict[str, Any] = {}

        async for event in self.run(**config):
            last_event = event
            if event.type == ToolEventType.COMPLETED:
                result_data = event.data
            elif event.type == ToolEventType.FAILED:
                ended_at = datetime.now(timezone.utc)
                return ToolResult(
                    success=False,
                    error=event.error,
                    duration_seconds=(ended_at - started_at).total_seconds(),
                )

        ended_at = datetime.now(timezone.utc)
        duration = (ended_at - started_at).total_seconds()

        if last_event and last_event.type == ToolEventType.COMPLETED:
            return ToolResult(
                success=True,
                data=result_data,
                duration_seconds=duration,
            )

        return ToolResult(
            success=False,
            error="Tool did not emit completion event",
            duration_seconds=duration,
        )

    def _emit_started(self, **data: Any) -> ToolEvent:
        """Helper to create a STARTED event."""
        return ToolEvent(
            type=ToolEventType.STARTED,
            tool=self.name,
            data=data,
        )

    def _emit_progress(self, **data: Any) -> ToolEvent:
        """Helper to create a PROGRESS event."""
        return ToolEvent(
            type=ToolEventType.PROGRESS,
            tool=self.name,
            data=data,
        )

    def _emit_completed(self, **data: Any) -> ToolEvent:
        """Helper to create a COMPLETED event."""
        return ToolEvent(
            type=ToolEventType.COMPLETED,
            tool=self.name,
            data=data,
        )

    def _emit_failed(self, error: str, **data: Any) -> ToolEvent:
        """Helper to create a FAILED event."""
        return ToolEvent(
            type=ToolEventType.FAILED,
            tool=self.name,
            error=error,
            data=data,
        )

    def _emit_message(self, **data: Any) -> ToolEvent:
        """Helper to create a MESSAGE event (for streaming tools)."""
        return ToolEvent(
            type=ToolEventType.MESSAGE,
            tool=self.name,
            data=data,
        )

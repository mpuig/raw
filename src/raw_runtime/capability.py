"""Capability system for RAW workflows.

Capabilities are external services that workflows can interact with.
Each capability provides a uniform async iterator interface for event-driven
communication, enabling both request/response and long-running interactions.

Usage:
    # In a workflow
    async for event in self.capability("email").run(
        to="user@example.com",
        subject="Hello",
        body="World",
    ):
        if event.type == "sent":
            self.log(f"Email sent: {event.data['message_id']}")

    # Or for simple request/response:
    result = await self.capability("http").call(url="https://api.example.com")
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from enum import Enum
from typing import Any, ClassVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class CapabilityEventType(str, Enum):
    """Standard capability event types."""

    # Lifecycle
    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    FAILED = "failed"

    # Communication
    MESSAGE = "message"
    CHUNK = "chunk"

    # Long-running
    WAITING = "waiting"
    RESUMED = "resumed"

    # Custom
    CUSTOM = "custom"


class CapabilityEvent(BaseModel):
    """Event emitted by capabilities during execution.

    Events provide real-time feedback from capability execution,
    enabling progress tracking, streaming responses, and error handling.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    type: CapabilityEventType
    capability: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class CapabilityResult(BaseModel):
    """Final result from a capability execution."""

    model_config = ConfigDict(frozen=True)

    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_seconds: float = 0.0


class Capability(ABC):
    """Base class for all capabilities.

    Capabilities wrap external services (email, SMS, HTTP, etc.) with a
    uniform interface. They can be:
    - Request/response (HTTP, database queries)
    - Long-running (conversations, file processing)
    - Event-triggered (webhooks, incoming calls)

    Subclass this and implement `run()` to create a capability.
    """

    name: ClassVar[str]
    description: ClassVar[str]
    triggers: ClassVar[list[str]] = []

    @abstractmethod
    async def run(self, **config: Any) -> AsyncIterator[CapabilityEvent]:
        """Execute the capability with given configuration.

        Yields events during execution, ending with a COMPLETED or FAILED event.

        Args:
            **config: Capability-specific configuration parameters.

        Yields:
            CapabilityEvent instances representing execution progress.
        """
        ...

    async def call(self, **config: Any) -> CapabilityResult:
        """Execute capability and return final result.

        Convenience method for simple request/response patterns.
        Consumes all events and returns the final result.
        """
        started_at = datetime.now(timezone.utc)
        last_event: CapabilityEvent | None = None
        result_data: dict[str, Any] = {}

        async for event in self.run(**config):
            last_event = event
            if event.type == CapabilityEventType.COMPLETED:
                result_data = event.data
            elif event.type == CapabilityEventType.FAILED:
                ended_at = datetime.now(timezone.utc)
                return CapabilityResult(
                    success=False,
                    error=event.error,
                    duration_seconds=(ended_at - started_at).total_seconds(),
                )

        ended_at = datetime.now(timezone.utc)
        duration = (ended_at - started_at).total_seconds()

        if last_event and last_event.type == CapabilityEventType.COMPLETED:
            return CapabilityResult(
                success=True,
                data=result_data,
                duration_seconds=duration,
            )

        return CapabilityResult(
            success=False,
            error="Capability did not emit completion event",
            duration_seconds=duration,
        )

    def _emit_started(self, **data: Any) -> CapabilityEvent:
        """Helper to create a STARTED event."""
        return CapabilityEvent(
            type=CapabilityEventType.STARTED,
            capability=self.name,
            data=data,
        )

    def _emit_progress(self, **data: Any) -> CapabilityEvent:
        """Helper to create a PROGRESS event."""
        return CapabilityEvent(
            type=CapabilityEventType.PROGRESS,
            capability=self.name,
            data=data,
        )

    def _emit_completed(self, **data: Any) -> CapabilityEvent:
        """Helper to create a COMPLETED event."""
        return CapabilityEvent(
            type=CapabilityEventType.COMPLETED,
            capability=self.name,
            data=data,
        )

    def _emit_failed(self, error: str, **data: Any) -> CapabilityEvent:
        """Helper to create a FAILED event."""
        return CapabilityEvent(
            type=CapabilityEventType.FAILED,
            capability=self.name,
            error=error,
            data=data,
        )


class CapabilityRegistry:
    """Registry for capability instances.

    Manages capability lifecycle and provides lookup by name.
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        """Register a capability instance."""
        self._capabilities[capability.name] = capability

    def get(self, name: str) -> Capability | None:
        """Get a capability by name."""
        return self._capabilities.get(name)

    def require(self, name: str) -> Capability:
        """Get a capability by name, raising if not found."""
        cap = self.get(name)
        if cap is None:
            available = ", ".join(self._capabilities.keys()) or "(none)"
            raise KeyError(f"Capability '{name}' not found. Available: {available}")
        return cap

    def list_all(self) -> list[str]:
        """List all registered capability names."""
        return list(self._capabilities.keys())

    def list_by_trigger(self, trigger: str) -> list[Capability]:
        """List capabilities that can handle a given trigger."""
        return [cap for cap in self._capabilities.values() if trigger in cap.triggers]


# Global registry instance
_registry: CapabilityRegistry | None = None


def get_capability_registry() -> CapabilityRegistry:
    """Get the global capability registry."""
    global _registry
    if _registry is None:
        _registry = CapabilityRegistry()
    return _registry


def set_capability_registry(registry: CapabilityRegistry) -> None:
    """Set the global capability registry."""
    global _registry
    _registry = registry


def register_capability(capability: Capability) -> None:
    """Register a capability in the global registry."""
    get_capability_registry().register(capability)


def get_capability(name: str) -> Capability:
    """Get a capability from the global registry."""
    return get_capability_registry().require(name)

"""Event triggers for RAW workflows.

Triggers allow workflows to be started by external events (webhooks,
incoming calls, scheduled jobs, etc.) rather than manual invocation.

Usage:
    from raw_runtime import BaseWorkflow, on_event, step

    @on_event("twilio.call.incoming")
    class InboundCallWorkflow(BaseWorkflow[CallParams]):

        @step("handle")
        async def handle_call(self):
            # Access trigger event data via self.trigger_event
            phone = self.trigger_event.data["from"]
            ...

        def run(self) -> int:
            self.handle_call()
            return 0
"""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class TriggerEvent(BaseModel):
    """External event that triggers a workflow.

    Contains metadata about the event source and the event data payload.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    event_type: str
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)


# Registry mapping event types to workflow classes
_trigger_registry: dict[str, list[type]] = {}


def on_event(event_type: str) -> Callable[[type[T]], type[T]]:
    """Decorator to register a workflow as triggered by an event type.

    Args:
        event_type: The event type pattern (e.g., "twilio.call.incoming",
                    "webhook.payment.received", "cron.daily").

    Usage:
        @on_event("twilio.call.incoming")
        class HandleInboundCall(BaseWorkflow[CallParams]):
            def run(self) -> int:
                # self.trigger_event contains the event data
                return 0
    """

    def decorator(cls: type[T]) -> type[T]:
        # Store metadata on the class
        cls._trigger_event_type = event_type  # type: ignore[attr-defined]

        # Register in global registry
        if event_type not in _trigger_registry:
            _trigger_registry[event_type] = []
        _trigger_registry[event_type].append(cls)

        return cls

    return decorator


def get_workflows_for_event(event_type: str) -> list[type]:
    """Get all workflow classes registered for an event type."""
    return _trigger_registry.get(event_type, [])


def list_trigger_types() -> list[str]:
    """List all registered trigger event types."""
    return list(_trigger_registry.keys())


def clear_trigger_registry() -> None:
    """Clear the trigger registry (for testing)."""
    _trigger_registry.clear()

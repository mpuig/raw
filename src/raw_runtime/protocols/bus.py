"""EventBus protocol definition."""

from collections.abc import Callable
from typing import Protocol

from raw_runtime.events import Event, EventType

SyncHandler = Callable[[Event], None]


class EventBus(Protocol):
    """Protocol for event bus implementations."""

    def emit(self, event: Event) -> None:
        """Emit an event to all registered handlers."""
        ...

    def subscribe(
        self,
        handler: SyncHandler,
        event_types: list[EventType] | None = None,
    ) -> None:
        """Subscribe a handler to events."""
        ...

    def unsubscribe(self, handler: SyncHandler) -> None:
        """Unsubscribe a handler from events."""
        ...

"""Event bus protocol for pub/sub messaging."""

from typing import Any, Callable, Protocol


class EventBus(Protocol):
    """Protocol for event publication and subscription.

    Enables decoupled communication between components through
    a publish/subscribe pattern.
    """

    def subscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        """Subscribe to events of a specific type."""
        ...

    def unsubscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        """Unsubscribe from events of a specific type."""
        ...

    async def publish(self, event_type: str, data: Any) -> None:
        """Publish an event to all subscribers."""
        ...

"""TelemetrySink protocol definition."""

from enum import Enum
from typing import Any, Protocol, runtime_checkable


class EventSeverity(str, Enum):
    """Severity level for events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@runtime_checkable
class TelemetrySink(Protocol):
    """Protocol for telemetry sinks.

    Implementations handle the mechanics of recording metrics
    and events to various backends.
    """

    def log_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
        unit: str | None = None,
    ) -> None:
        """Log a metric value.

        Args:
            name: Metric name (e.g., "step.duration_seconds")
            value: Numeric value
            tags: Optional key-value tags
            unit: Optional unit (e.g., "seconds", "bytes")
        """
        ...

    def log_event(
        self,
        name: str,
        severity: EventSeverity = EventSeverity.INFO,
        message: str | None = None,
        data: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Log a structured event.

        Args:
            name: Event name (e.g., "workflow.started")
            severity: Event severity level
            message: Human-readable message
            data: Structured event data
            tags: Optional key-value tags
        """
        ...

    def flush(self) -> None:
        """Flush any buffered data.

        Should be called before process exit to ensure all
        telemetry is persisted.
        """
        ...

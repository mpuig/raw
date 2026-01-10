"""Telemetry abstraction for workflow observability.

Provides a protocol for logging metrics and events, enabling:
- Console output (default for development)
- JSON file logging (for log aggregation)
- Future: OpenTelemetry, Datadog, etc.

Note: Protocol is in raw_runtime.protocols.telemetry,
      Implementations are in raw_runtime.drivers.telemetry.
      This module re-exports for backwards compatibility.
"""

from raw_runtime.container import RuntimeContainer
from raw_runtime.drivers.telemetry import (
    CompositeSink,
    ConsoleSink,
    JsonFileSink,
    MemorySink,
    MetricPoint,
    NullSink,
    TelemetryEvent,
)
from raw_runtime.protocols.telemetry import EventSeverity, TelemetrySink

# Backward-compatible accessors that delegate to RuntimeContainer


def get_telemetry_sink() -> TelemetrySink:
    """Get the current telemetry sink.

    Returns NullSink by default (telemetry opt-in).
    """
    return RuntimeContainer.telemetry()


def set_telemetry_sink(sink: TelemetrySink | None) -> None:
    """Set the global telemetry sink."""
    RuntimeContainer.set_telemetry(sink)


def log_metric(
    name: str,
    value: float,
    tags: dict[str, str] | None = None,
    unit: str | None = None,
) -> None:
    """Convenience function to log a metric."""
    get_telemetry_sink().log_metric(name, value, tags, unit)


def log_event(
    name: str,
    severity: EventSeverity = EventSeverity.INFO,
    message: str | None = None,
    data: dict[str, any] | None = None,
    tags: dict[str, str] | None = None,
) -> None:
    """Convenience function to log an event."""
    get_telemetry_sink().log_event(name, severity, message, data, tags)


__all__ = [
    "EventSeverity",
    "MetricPoint",
    "TelemetryEvent",
    "TelemetrySink",
    "NullSink",
    "ConsoleSink",
    "JsonFileSink",
    "MemorySink",
    "CompositeSink",
    "get_telemetry_sink",
    "set_telemetry_sink",
    "log_metric",
    "log_event",
]

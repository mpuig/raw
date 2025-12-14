"""Telemetry sink implementations."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, TextIO

from pydantic import BaseModel, ConfigDict, Field

from raw_runtime.protocols.telemetry import EventSeverity


class MetricPoint(BaseModel):
    """A single metric data point.

    Using Pydantic enables automatic JSON serialization in JsonFileSink
    via model_dump_json(), eliminating manual dict construction.

    Frozen because metrics are immutable facts about measurements.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["metric"] = "metric"
    name: str
    value: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: dict[str, str] = Field(default_factory=dict)
    unit: str | None = None


class TelemetryEvent(BaseModel):
    """A structured telemetry event.

    Using Pydantic enables automatic JSON serialization in JsonFileSink
    via model_dump_json(), eliminating manual dict construction.

    Frozen because events are immutable facts about what happened.
    """

    model_config = ConfigDict(frozen=True)

    type: Literal["event"] = "event"
    name: str
    severity: EventSeverity = EventSeverity.INFO
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    tags: dict[str, str] = Field(default_factory=dict)


class NullSink:
    """Telemetry sink that discards all data.

    Useful for testing or when telemetry is disabled.
    """

    def log_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
        unit: str | None = None,
    ) -> None:
        pass

    def log_event(
        self,
        name: str,
        severity: EventSeverity = EventSeverity.INFO,
        message: str | None = None,
        data: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        pass

    def flush(self) -> None:
        pass


class ConsoleSink:
    """Telemetry sink that prints to console.

    Uses simple formatting for human readability.
    """

    def __init__(
        self,
        output: TextIO | None = None,
        min_severity: EventSeverity = EventSeverity.INFO,
    ) -> None:
        """Initialize console sink.

        Args:
            output: Output stream (defaults to stderr)
            min_severity: Minimum severity to log
        """
        self._output = output or sys.stderr
        self._min_severity = min_severity
        self._severity_order = list(EventSeverity)

    def log_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
        unit: str | None = None,
    ) -> None:
        unit_str = f" {unit}" if unit else ""
        tags_str = ""
        if tags:
            tags_str = " " + " ".join(f"{k}={v}" for k, v in tags.items())
        print(f"[METRIC] {name}: {value}{unit_str}{tags_str}", file=self._output)

    def log_event(
        self,
        name: str,
        severity: EventSeverity = EventSeverity.INFO,
        message: str | None = None,
        data: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        if self._severity_order.index(severity) < self._severity_order.index(self._min_severity):
            return

        severity_str = severity.value.upper()
        msg_str = f": {message}" if message else ""
        print(f"[{severity_str}] {name}{msg_str}", file=self._output)

    def flush(self) -> None:
        self._output.flush()


class JsonFileSink:
    """Telemetry sink that writes JSON lines to a file.

    Each metric/event is written as a single JSON line for
    easy parsing by log aggregation tools.
    """

    def __init__(self, path: Path | str) -> None:
        """Initialize JSON file sink.

        Args:
            path: Path to output file
        """
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self._path.open("a")

    def log_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
        unit: str | None = None,
    ) -> None:
        # Pydantic handles JSON serialization with proper datetime formatting
        metric = MetricPoint(
            name=name,
            value=value,
            tags=tags or {},
            unit=unit,
        )
        self._file.write(metric.model_dump_json(exclude_none=True) + "\n")

    def log_event(
        self,
        name: str,
        severity: EventSeverity = EventSeverity.INFO,
        message: str | None = None,
        data: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        # Pydantic handles JSON serialization with proper datetime/enum formatting
        event = TelemetryEvent(
            name=name,
            severity=severity,
            message=message,
            data=data or {},
            tags=tags or {},
        )
        self._file.write(event.model_dump_json(exclude_none=True) + "\n")

    def flush(self) -> None:
        self._file.flush()

    def close(self) -> None:
        """Close the file handle."""
        self._file.close()


class MemorySink:
    """Telemetry sink that stores data in memory.

    Useful for testing - allows inspection of logged metrics/events.
    """

    def __init__(self) -> None:
        self.metrics: list[MetricPoint] = []
        self.events: list[TelemetryEvent] = []

    def log_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
        unit: str | None = None,
    ) -> None:
        self.metrics.append(
            MetricPoint(
                name=name,
                value=value,
                tags=tags or {},
                unit=unit,
            )
        )

    def log_event(
        self,
        name: str,
        severity: EventSeverity = EventSeverity.INFO,
        message: str | None = None,
        data: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        self.events.append(
            TelemetryEvent(
                name=name,
                severity=severity,
                message=message,
                data=data or {},
                tags=tags or {},
            )
        )

    def flush(self) -> None:
        pass

    def clear(self) -> None:
        """Clear all stored data."""
        self.metrics.clear()
        self.events.clear()


class CompositeSink:
    """Telemetry sink that forwards to multiple sinks.

    Useful for sending telemetry to multiple destinations
    (e.g., console + file).
    """

    def __init__(self, sinks: list[Any]) -> None:
        """Initialize with list of sinks.

        Args:
            sinks: Sinks to forward to
        """
        self._sinks = sinks

    def log_metric(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
        unit: str | None = None,
    ) -> None:
        for sink in self._sinks:
            sink.log_metric(name, value, tags, unit)

    def log_event(
        self,
        name: str,
        severity: EventSeverity = EventSeverity.INFO,
        message: str | None = None,
        data: dict[str, Any] | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        for sink in self._sinks:
            sink.log_event(name, severity, message, data, tags)

    def flush(self) -> None:
        for sink in self._sinks:
            sink.flush()

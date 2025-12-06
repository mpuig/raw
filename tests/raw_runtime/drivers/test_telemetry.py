"""Tests for telemetry sink abstraction."""

import json
from io import StringIO

from raw_runtime.telemetry import (
    CompositeSink,
    ConsoleSink,
    EventSeverity,
    JsonFileSink,
    MemorySink,
    NullSink,
    TelemetrySink,
    get_telemetry_sink,
    log_event,
    log_metric,
    set_telemetry_sink,
)


class TestTelemetrySinkProtocol:
    """Test that implementations satisfy the TelemetrySink protocol."""

    def test_null_sink_is_telemetry_sink(self):
        assert isinstance(NullSink(), TelemetrySink)

    def test_console_sink_is_telemetry_sink(self):
        assert isinstance(ConsoleSink(), TelemetrySink)

    def test_memory_sink_is_telemetry_sink(self):
        assert isinstance(MemorySink(), TelemetrySink)

    def test_composite_sink_is_telemetry_sink(self):
        assert isinstance(CompositeSink([]), TelemetrySink)


class TestNullSink:
    """Tests for NullSink."""

    def test_accepts_metrics(self):
        sink = NullSink()
        sink.log_metric("test.metric", 42.0, tags={"env": "test"})

    def test_accepts_events(self):
        sink = NullSink()
        sink.log_event("test.event", EventSeverity.INFO, "message")

    def test_flush_noop(self):
        sink = NullSink()
        sink.flush()


class TestConsoleSink:
    """Tests for ConsoleSink."""

    def test_logs_metric(self):
        output = StringIO()
        sink = ConsoleSink(output=output)

        sink.log_metric("request.duration", 0.5, unit="seconds")
        sink.flush()

        result = output.getvalue()
        assert "[METRIC]" in result
        assert "request.duration" in result
        assert "0.5" in result
        assert "seconds" in result

    def test_logs_metric_with_tags(self):
        output = StringIO()
        sink = ConsoleSink(output=output)

        sink.log_metric("requests", 100, tags={"method": "GET"})
        sink.flush()

        result = output.getvalue()
        assert "method=GET" in result

    def test_logs_event(self):
        output = StringIO()
        sink = ConsoleSink(output=output)

        sink.log_event("workflow.started", EventSeverity.INFO, "Starting workflow")
        sink.flush()

        result = output.getvalue()
        assert "[INFO]" in result
        assert "workflow.started" in result
        assert "Starting workflow" in result

    def test_filters_by_severity(self):
        output = StringIO()
        sink = ConsoleSink(output=output, min_severity=EventSeverity.WARNING)

        sink.log_event("debug.msg", EventSeverity.DEBUG, "ignored")
        sink.log_event("info.msg", EventSeverity.INFO, "also ignored")
        sink.log_event("warn.msg", EventSeverity.WARNING, "shown")
        sink.flush()

        result = output.getvalue()
        assert "debug.msg" not in result
        assert "info.msg" not in result
        assert "warn.msg" in result


class TestJsonFileSink:
    """Tests for JsonFileSink."""

    def test_logs_metric_as_json(self, tmp_path):
        path = tmp_path / "telemetry.jsonl"
        sink = JsonFileSink(path)

        sink.log_metric("cpu.usage", 75.5, tags={"host": "server1"}, unit="percent")
        sink.flush()
        sink.close()

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 1

        data = json.loads(lines[0])
        assert data["type"] == "metric"
        assert data["name"] == "cpu.usage"
        assert data["value"] == 75.5
        assert data["tags"] == {"host": "server1"}
        assert data["unit"] == "percent"
        assert "timestamp" in data

    def test_logs_event_as_json(self, tmp_path):
        path = tmp_path / "telemetry.jsonl"
        sink = JsonFileSink(path)

        sink.log_event(
            "step.completed",
            EventSeverity.INFO,
            "Step finished",
            data={"step": "fetch", "duration": 1.5},
            tags={"workflow": "test"},
        )
        sink.flush()
        sink.close()

        lines = path.read_text().strip().split("\n")
        data = json.loads(lines[0])

        assert data["type"] == "event"
        assert data["name"] == "step.completed"
        assert data["severity"] == "info"
        assert data["message"] == "Step finished"
        assert data["data"] == {"step": "fetch", "duration": 1.5}
        assert data["tags"] == {"workflow": "test"}

    def test_appends_to_file(self, tmp_path):
        path = tmp_path / "telemetry.jsonl"
        sink = JsonFileSink(path)

        sink.log_metric("m1", 1.0)
        sink.log_metric("m2", 2.0)
        sink.log_metric("m3", 3.0)
        sink.flush()
        sink.close()

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 3


class TestMemorySink:
    """Tests for MemorySink."""

    def test_stores_metrics(self):
        sink = MemorySink()

        sink.log_metric("test.metric", 42.0, tags={"env": "test"})
        sink.log_metric("other.metric", 100.0)

        assert len(sink.metrics) == 2
        assert sink.metrics[0].name == "test.metric"
        assert sink.metrics[0].value == 42.0
        assert sink.metrics[0].tags == {"env": "test"}

    def test_stores_events(self):
        sink = MemorySink()

        sink.log_event("event.one", EventSeverity.INFO, "first")
        sink.log_event("event.two", EventSeverity.ERROR, "second", data={"key": "val"})

        assert len(sink.events) == 2
        assert sink.events[0].name == "event.one"
        assert sink.events[0].severity == EventSeverity.INFO
        assert sink.events[1].data == {"key": "val"}

    def test_clear(self):
        sink = MemorySink()

        sink.log_metric("m", 1.0)
        sink.log_event("e", EventSeverity.INFO)
        assert len(sink.metrics) == 1
        assert len(sink.events) == 1

        sink.clear()
        assert len(sink.metrics) == 0
        assert len(sink.events) == 0


class TestCompositeSink:
    """Tests for CompositeSink."""

    def test_forwards_to_all_sinks(self):
        sink1 = MemorySink()
        sink2 = MemorySink()
        composite = CompositeSink([sink1, sink2])

        composite.log_metric("shared.metric", 50.0)
        composite.log_event("shared.event", EventSeverity.INFO)

        assert len(sink1.metrics) == 1
        assert len(sink2.metrics) == 1
        assert len(sink1.events) == 1
        assert len(sink2.events) == 1

    def test_empty_composite(self):
        composite = CompositeSink([])
        composite.log_metric("ignored", 0.0)
        composite.log_event("ignored", EventSeverity.INFO)
        composite.flush()


class TestGlobalTelemetrySink:
    """Tests for global telemetry functions."""

    def test_default_is_null_sink(self):
        set_telemetry_sink(None)
        sink = get_telemetry_sink()
        assert isinstance(sink, NullSink)

    def test_set_and_get_sink(self):
        memory = MemorySink()
        set_telemetry_sink(memory)
        assert get_telemetry_sink() is memory
        set_telemetry_sink(None)

    def test_log_metric_convenience(self):
        memory = MemorySink()
        set_telemetry_sink(memory)

        log_metric("conv.metric", 99.0, tags={"source": "test"})

        assert len(memory.metrics) == 1
        assert memory.metrics[0].name == "conv.metric"
        set_telemetry_sink(None)

    def test_log_event_convenience(self):
        memory = MemorySink()
        set_telemetry_sink(memory)

        log_event("conv.event", EventSeverity.WARNING, "warning message")

        assert len(memory.events) == 1
        assert memory.events[0].name == "conv.event"
        assert memory.events[0].severity == EventSeverity.WARNING
        set_telemetry_sink(None)


class TestEventSeverity:
    """Tests for EventSeverity enum."""

    def test_severity_values(self):
        assert EventSeverity.DEBUG == "debug"
        assert EventSeverity.INFO == "info"
        assert EventSeverity.WARNING == "warning"
        assert EventSeverity.ERROR == "error"
        assert EventSeverity.CRITICAL == "critical"

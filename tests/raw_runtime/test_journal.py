"""Tests for journal writing and reading."""

import json
from pathlib import Path

import pytest

from raw_runtime.events import (
    EventType,
    StepCompletedEvent,
    StepStartedEvent,
    WorkflowCompletedEvent,
    WorkflowStartedEvent,
)
from raw_runtime.journal import JournalReader, LocalJournalWriter


class TestLocalJournalWriter:
    """Tests for LocalJournalWriter."""

    def test_write_single_event(self, tmp_path: Path) -> None:
        """Test writing a single event to journal."""
        journal_path = tmp_path / "events.jsonl"
        writer = LocalJournalWriter(journal_path)

        event = WorkflowStartedEvent(
            workflow_id="test-workflow",
            run_id="test-run",
            workflow_name="TestWorkflow",
            parameters={"arg": "value"},
        )

        writer.write_event(event)
        writer.close()

        # Verify file exists and contains valid JSONL
        assert journal_path.exists()
        lines = journal_path.read_text().strip().split("\n")
        assert len(lines) == 1

        # Parse and verify structure
        entry = json.loads(lines[0])
        assert entry["version"] == 1
        assert entry["event"]["event_type"] == "workflow.started"
        assert entry["event"]["workflow_id"] == "test-workflow"
        assert entry["event"]["run_id"] == "test-run"

    def test_write_multiple_events(self, tmp_path: Path) -> None:
        """Test writing multiple events creates JSONL with one event per line."""
        journal_path = tmp_path / "events.jsonl"
        writer = LocalJournalWriter(journal_path)

        events = [
            WorkflowStartedEvent(
                workflow_id="test-workflow",
                run_id="test-run",
                workflow_name="TestWorkflow",
            ),
            StepStartedEvent(
                workflow_id="test-workflow",
                run_id="test-run",
                step_name="step1",
            ),
            StepCompletedEvent(
                workflow_id="test-workflow",
                run_id="test-run",
                step_name="step1",
                duration_seconds=1.5,
                result_type="str",
            ),
            WorkflowCompletedEvent(
                workflow_id="test-workflow",
                run_id="test-run",
                duration_seconds=2.0,
                step_count=1,
            ),
        ]

        for event in events:
            writer.write_event(event)

        writer.close()

        # Verify all events written
        lines = journal_path.read_text().strip().split("\n")
        assert len(lines) == 4

        # Verify event types
        event_types = [json.loads(line)["event"]["event_type"] for line in lines]
        assert event_types == [
            "workflow.started",
            "step.started",
            "step.completed",
            "workflow.completed",
        ]

    def test_context_manager(self, tmp_path: Path) -> None:
        """Test using journal writer as context manager."""
        journal_path = tmp_path / "events.jsonl"

        with LocalJournalWriter(journal_path) as writer:
            event = WorkflowStartedEvent(
                workflow_id="test-workflow",
                run_id="test-run",
                workflow_name="TestWorkflow",
            )
            writer.write_event(event)

        # Verify file was flushed and closed
        assert journal_path.exists()
        lines = journal_path.read_text().strip().split("\n")
        assert len(lines) == 1

    def test_flush_ensures_durability(self, tmp_path: Path) -> None:
        """Test that flush() ensures data is written to disk."""
        journal_path = tmp_path / "events.jsonl"
        writer = LocalJournalWriter(journal_path)

        event = WorkflowStartedEvent(
            workflow_id="test-workflow",
            run_id="test-run",
            workflow_name="TestWorkflow",
        )

        writer.write_event(event)
        writer.flush()

        # Verify data is readable immediately after flush
        content = journal_path.read_text()
        assert "workflow.started" in content

        writer.close()

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that journal writer creates parent directory if needed."""
        journal_path = tmp_path / "runs" / "run_123" / "events.jsonl"
        writer = LocalJournalWriter(journal_path)

        event = WorkflowStartedEvent(
            workflow_id="test-workflow",
            run_id="test-run",
            workflow_name="TestWorkflow",
        )

        writer.write_event(event)
        writer.close()

        assert journal_path.exists()
        assert journal_path.parent.exists()


class TestJournalReader:
    """Tests for JournalReader."""

    def test_read_empty_journal(self, tmp_path: Path) -> None:
        """Test reading from non-existent journal returns empty list."""
        journal_path = tmp_path / "events.jsonl"
        reader = JournalReader(journal_path)

        events = reader.read_events()
        assert events == []

    def test_read_single_event(self, tmp_path: Path) -> None:
        """Test reading a single event from journal."""
        journal_path = tmp_path / "events.jsonl"

        # Write event
        writer = LocalJournalWriter(journal_path)
        event = WorkflowStartedEvent(
            workflow_id="test-workflow",
            run_id="test-run",
            workflow_name="TestWorkflow",
            parameters={"key": "value"},
        )
        writer.write_event(event)
        writer.close()

        # Read event
        reader = JournalReader(journal_path)
        events = reader.read_events()

        assert len(events) == 1
        assert events[0]["event_type"] == "workflow.started"
        assert events[0]["workflow_id"] == "test-workflow"
        assert events[0]["parameters"] == {"key": "value"}

    def test_read_multiple_events(self, tmp_path: Path) -> None:
        """Test reading multiple events preserves order."""
        journal_path = tmp_path / "events.jsonl"

        # Write events
        writer = LocalJournalWriter(journal_path)
        events_written = [
            WorkflowStartedEvent(
                workflow_id="test-workflow",
                run_id="test-run",
                workflow_name="TestWorkflow",
            ),
            StepStartedEvent(
                workflow_id="test-workflow",
                run_id="test-run",
                step_name="step1",
            ),
            StepCompletedEvent(
                workflow_id="test-workflow",
                run_id="test-run",
                step_name="step1",
                duration_seconds=1.0,
                result_type="str",
            ),
        ]
        for event in events_written:
            writer.write_event(event)
        writer.close()

        # Read events
        reader = JournalReader(journal_path)
        events = reader.read_events()

        assert len(events) == 3
        assert events[0]["event_type"] == "workflow.started"
        assert events[1]["event_type"] == "step.started"
        assert events[2]["event_type"] == "step.completed"

    def test_handles_corrupt_line(self, tmp_path: Path) -> None:
        """Test that corrupt/incomplete lines are skipped gracefully."""
        journal_path = tmp_path / "events.jsonl"

        # Write good event, corrupt line, then another good event
        writer = LocalJournalWriter(journal_path)
        event1 = WorkflowStartedEvent(
            workflow_id="test-workflow",
            run_id="test-run",
            workflow_name="TestWorkflow",
        )
        writer.write_event(event1)
        writer.close()

        # Append corrupt line manually
        with open(journal_path, "a") as f:
            f.write("{this is not valid json\n")

        # Write another good event
        with open(journal_path, "a") as f:
            event2 = StepStartedEvent(
                workflow_id="test-workflow",
                run_id="test-run",
                step_name="step1",
            )
            entry = {"version": 1, "event": json.loads(event2.model_dump_json())}
            f.write(json.dumps(entry) + "\n")

        # Read events - should skip corrupt line
        reader = JournalReader(journal_path)
        events = reader.read_events()

        assert len(events) == 2  # Should have 2 good events, corrupt line skipped
        assert events[0]["event_type"] == "workflow.started"
        assert events[1]["event_type"] == "step.started"

    def test_iter_events_memory_efficient(self, tmp_path: Path) -> None:
        """Test iter_events() for memory-efficient reading."""
        journal_path = tmp_path / "events.jsonl"

        # Write multiple events
        writer = LocalJournalWriter(journal_path)
        for i in range(100):
            event = StepStartedEvent(
                workflow_id="test-workflow",
                run_id="test-run",
                step_name=f"step{i}",
            )
            writer.write_event(event)
        writer.close()

        # Read using iterator
        reader = JournalReader(journal_path)
        count = 0
        for event in reader.iter_events():
            assert event["event_type"] == "step.started"
            count += 1

        assert count == 100

    def test_skip_empty_lines(self, tmp_path: Path) -> None:
        """Test that empty lines in journal are skipped."""
        journal_path = tmp_path / "events.jsonl"

        # Write events with empty lines
        writer = LocalJournalWriter(journal_path)
        event = WorkflowStartedEvent(
            workflow_id="test-workflow",
            run_id="test-run",
            workflow_name="TestWorkflow",
        )
        writer.write_event(event)
        writer.close()

        # Add empty lines manually
        with open(journal_path, "a") as f:
            f.write("\n\n")

        # Read events - should ignore empty lines
        reader = JournalReader(journal_path)
        events = reader.read_events()

        assert len(events) == 1
        assert events[0]["event_type"] == "workflow.started"

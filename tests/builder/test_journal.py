"""Tests for builder journal writer and reader."""

import tempfile
from pathlib import Path

import pytest

from raw.builder.events import (
    BuildCompletedEvent,
    BuildStartedEvent,
    GateCompletedEvent,
    GateStartedEvent,
)
from raw.builder.journal import (
    BuilderJournal,
    BuilderJournalReader,
    get_last_build,
    list_builds,
)


def test_builder_journal_write():
    """Test writing events to journal."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builds_dir = Path(tmpdir)

        # Create journal
        journal = BuilderJournal("build-123", builds_dir)

        # Write events
        journal.write(
            BuildStartedEvent(
                build_id="build-123", iteration=0, workflow_id="wf-456", intent="Test workflow"
            )
        )

        journal.write(
            GateStartedEvent(build_id="build-123", iteration=1, gate="validate")
        )

        journal.close()

        # Check file exists
        journal_path = builds_dir / "build-123" / "events.jsonl"
        assert journal_path.exists()

        # Check content
        lines = journal_path.read_text().strip().split("\n")
        assert len(lines) == 2


def test_builder_journal_context_manager():
    """Test journal with context manager."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builds_dir = Path(tmpdir)

        with BuilderJournal("build-456", builds_dir) as journal:
            journal.write(
                BuildStartedEvent(
                    build_id="build-456",
                    iteration=0,
                    workflow_id="wf-789",
                    intent="Context test",
                )
            )

        # File should be closed and exist
        journal_path = builds_dir / "build-456" / "events.jsonl"
        assert journal_path.exists()


def test_builder_journal_reader():
    """Test reading events from journal."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builds_dir = Path(tmpdir)

        # Write events
        with BuilderJournal("build-789", builds_dir) as journal:
            journal.write(
                BuildStartedEvent(
                    build_id="build-789",
                    iteration=0,
                    workflow_id="wf-abc",
                    intent="Read test",
                )
            )
            journal.write(GateStartedEvent(build_id="build-789", iteration=1, gate="validate"))
            journal.write(
                GateCompletedEvent(
                    build_id="build-789",
                    iteration=1,
                    gate="validate",
                    passed=True,
                    duration_seconds=1.5,
                )
            )

        # Read events
        journal_path = builds_dir / "build-789" / "events.jsonl"
        reader = BuilderJournalReader(journal_path)
        events = reader.read_events()

        assert len(events) == 3
        assert events[0]["event_type"] == "build.started"
        assert events[0]["workflow_id"] == "wf-abc"
        assert events[1]["event_type"] == "gate.started"
        assert events[1]["gate"] == "validate"
        assert events[2]["event_type"] == "gate.completed"
        assert events[2]["passed"] is True


def test_builder_journal_reader_typed():
    """Test reading typed events from journal."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builds_dir = Path(tmpdir)

        # Write events
        with BuilderJournal("build-typed", builds_dir) as journal:
            journal.write(
                BuildStartedEvent(
                    build_id="build-typed",
                    iteration=0,
                    workflow_id="wf-typed",
                    intent="Typed test",
                )
            )
            journal.write(
                BuildCompletedEvent(
                    build_id="build-typed",
                    iteration=3,
                    total_iterations=3,
                    duration_seconds=45.2,
                )
            )

        # Read typed events
        journal_path = builds_dir / "build-typed" / "events.jsonl"
        reader = BuilderJournalReader(journal_path)
        typed_events = reader.read_typed_events()

        assert len(typed_events) == 2
        assert isinstance(typed_events[0], BuildStartedEvent)
        assert typed_events[0].workflow_id == "wf-typed"
        assert isinstance(typed_events[1], BuildCompletedEvent)
        assert typed_events[1].total_iterations == 3


def test_builder_journal_reader_not_found():
    """Test reader with non-existent file."""
    reader = BuilderJournalReader(Path("/nonexistent/events.jsonl"))

    with pytest.raises(FileNotFoundError):
        reader.read_events()


def test_builder_journal_reader_corrupt_line():
    """Test reader handles corrupt lines gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "corrupt.jsonl"

        # Write mixed valid/corrupt lines
        with open(journal_path, "w") as f:
            f.write('{"event_type": "build.started", "build_id": "b1", "iteration": 0}\n')
            f.write('not valid json\n')
            f.write('{"event_type": "build.completed", "build_id": "b1", "iteration": 1}\n')

        reader = BuilderJournalReader(journal_path)
        events = reader.read_events()

        # Should skip corrupt line
        assert len(events) == 2
        assert events[0]["event_type"] == "build.started"
        assert events[1]["event_type"] == "build.completed"


def test_list_builds():
    """Test listing all builds."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builds_dir = Path(tmpdir)

        # Create multiple builds
        for build_id in ["build-1", "build-2", "build-3"]:
            with BuilderJournal(build_id, builds_dir) as journal:
                journal.write(
                    BuildStartedEvent(
                        build_id=build_id,
                        iteration=0,
                        workflow_id=f"wf-{build_id}",
                        intent="List test",
                    )
                )

        # List builds
        builds = list_builds(builds_dir)

        assert len(builds) == 3
        build_ids = [b["build_id"] for b in builds]
        assert "build-1" in build_ids
        assert "build-2" in build_ids
        assert "build-3" in build_ids

        # Check event count
        assert all(b["event_count"] == 1 for b in builds)


def test_list_builds_empty():
    """Test listing builds with no builds."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builds_dir = Path(tmpdir) / "empty"
        builds = list_builds(builds_dir)
        assert builds == []


def test_get_last_build():
    """Test getting most recent build."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builds_dir = Path(tmpdir)

        # Create builds with different times
        import time

        for build_id in ["build-old", "build-new"]:
            with BuilderJournal(build_id, builds_dir) as journal:
                journal.write(
                    BuildStartedEvent(
                        build_id=build_id,
                        iteration=0,
                        workflow_id=f"wf-{build_id}",
                        intent="Last test",
                    )
                )
            time.sleep(0.01)  # Ensure different timestamps

        # Get last build
        last = get_last_build(builds_dir)

        assert last is not None
        assert last["build_id"] == "build-new"


def test_get_last_build_empty():
    """Test getting last build when none exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builds_dir = Path(tmpdir) / "empty"
        last = get_last_build(builds_dir)
        assert last is None


def test_journal_creates_directory():
    """Test journal creates directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        builds_dir = Path(tmpdir) / "nonexistent"

        # Should create directory
        journal = BuilderJournal("build-create", builds_dir)
        journal.write(
            BuildStartedEvent(
                build_id="build-create",
                iteration=0,
                workflow_id="wf-create",
                intent="Create dir test",
            )
        )
        journal.close()

        assert builds_dir.exists()
        assert (builds_dir / "build-create").exists()
        assert (builds_dir / "build-create" / "events.jsonl").exists()

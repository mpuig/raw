"""Tests for builder resume functionality."""

import json
import tempfile
from pathlib import Path

import pytest

from raw.builder.events import (
    BuildCompletedEvent,
    BuildEventType,
    BuildStartedEvent,
    BuildStuckEvent,
    GateCompletedEvent,
    IterationStartedEvent,
    ModeSwitchedEvent,
)
from raw.builder.mode import BuildMode
from raw.builder.resume import (
    ResumeError,
    find_build_to_resume,
    replay_journal_for_resume,
)


def create_test_journal(builds_dir: Path, build_id: str, events: list[dict]) -> Path:
    """Create a test journal with given events."""
    build_dir = builds_dir / build_id
    build_dir.mkdir(parents=True, exist_ok=True)

    journal_path = build_dir / "events.jsonl"
    with open(journal_path, "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    return journal_path


def test_find_build_to_resume_by_id():
    """Test finding build by specific ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create .raw/builds structure
        raw_dir = tmpdir_path / ".raw"
        builds_dir = raw_dir / "builds"
        builds_dir.mkdir(parents=True)

        # Create test builds
        build_id = "build-123"
        create_test_journal(builds_dir, build_id, [{"event_type": "build.started"}])

        # Change to tmpdir
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir_path)

            result = find_build_to_resume(build_id=build_id)
            assert result == build_id

        finally:
            os.chdir(original_cwd)


def test_find_build_to_resume_last():
    """Test finding last build."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create .raw/builds structure
        raw_dir = tmpdir_path / ".raw"
        builds_dir = raw_dir / "builds"
        builds_dir.mkdir(parents=True)

        # Create test builds
        create_test_journal(builds_dir, "build-old", [{"event_type": "build.started"}])
        import time

        time.sleep(0.01)  # Ensure different mtime
        create_test_journal(builds_dir, "build-new", [{"event_type": "build.started"}])

        # Change to tmpdir
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir_path)

            result = find_build_to_resume(last=True)
            assert result == "build-new"

        finally:
            os.chdir(original_cwd)


def test_find_build_to_resume_not_found():
    """Test error when build not found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create .raw/builds structure
        raw_dir = tmpdir_path / ".raw"
        builds_dir = raw_dir / "builds"
        builds_dir.mkdir(parents=True)

        # Change to tmpdir
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir_path)

            with pytest.raises(ResumeError, match="Build not found"):
                find_build_to_resume(build_id="nonexistent")

        finally:
            os.chdir(original_cwd)


def test_find_build_to_resume_both_flags():
    """Test error when both --resume and --last specified."""
    with pytest.raises(ResumeError, match="Cannot specify both"):
        find_build_to_resume(build_id="build-123", last=True)


def test_replay_journal_for_resume_basic():
    """Test basic journal replay."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        builds_dir = tmpdir_path / ".raw" / "builds"
        builds_dir.mkdir(parents=True)

        build_id = "build-test"

        # Create journal with basic events
        events = [
            {
                "event_type": BuildEventType.BUILD_STARTED.value,
                "timestamp": 1234567890.0,
                "build_id": build_id,
                "iteration": 0,
                "workflow_id": "test-workflow",
                "intent": None,
                "config": {
                    "budgets": {
                        "max_iterations": 10,
                        "max_minutes": 30,
                        "doom_loop_threshold": 3,
                    },
                    "gates": {"default": ["validate", "dry"], "optional": {}},
                    "skills": {"discovery_paths": ["builder/skills"]},
                    "mode": {"plan_first": True},
                },
            },
            {
                "event_type": BuildEventType.ITERATION_STARTED.value,
                "timestamp": 1234567891.0,
                "build_id": build_id,
                "iteration": 1,
                "mode": "plan",
            },
            {
                "event_type": BuildEventType.MODE_SWITCHED.value,
                "timestamp": 1234567892.0,
                "build_id": build_id,
                "iteration": 1,
                "mode": "execute",
            },
        ]

        create_test_journal(builds_dir, build_id, events)

        # Replay journal
        state = replay_journal_for_resume(build_id, builds_dir)

        assert state.build_id == build_id
        assert state.workflow_id == "test-workflow"
        assert state.intent is None
        assert state.last_iteration == 1
        assert state.current_mode == BuildMode.EXECUTE
        assert state.start_timestamp == 1234567890.0


def test_replay_journal_for_resume_already_completed():
    """Test error when trying to resume completed build."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        builds_dir = tmpdir_path / ".raw" / "builds"
        builds_dir.mkdir(parents=True)

        build_id = "build-completed"

        # Create journal with completion event
        events = [
            {
                "event_type": BuildEventType.BUILD_STARTED.value,
                "timestamp": 1234567890.0,
                "build_id": build_id,
                "iteration": 0,
                "workflow_id": "test-workflow",
                "intent": None,
                "config": {"budgets": {}, "gates": {}, "skills": {}, "mode": {}},
            },
            {
                "event_type": BuildEventType.BUILD_COMPLETED.value,
                "timestamp": 1234567900.0,
                "build_id": build_id,
                "iteration": 1,
                "total_iterations": 1,
                "duration_seconds": 10.0,
            },
        ]

        create_test_journal(builds_dir, build_id, events)

        # Should raise error
        with pytest.raises(ResumeError, match="Cannot resume build that already completed"):
            replay_journal_for_resume(build_id, builds_dir)


def test_replay_journal_for_resume_already_stuck():
    """Test error when trying to resume stuck build."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        builds_dir = tmpdir_path / ".raw" / "builds"
        builds_dir.mkdir(parents=True)

        build_id = "build-stuck"

        # Create journal with stuck event
        events = [
            {
                "event_type": BuildEventType.BUILD_STARTED.value,
                "timestamp": 1234567890.0,
                "build_id": build_id,
                "iteration": 0,
                "workflow_id": "test-workflow",
                "intent": None,
                "config": {"budgets": {}, "gates": {}, "skills": {}, "mode": {}},
            },
            {
                "event_type": BuildEventType.BUILD_STUCK.value,
                "timestamp": 1234567900.0,
                "build_id": build_id,
                "iteration": 10,
                "reason": "max_iterations",
                "last_failures": ["Gate failed"],
            },
        ]

        create_test_journal(builds_dir, build_id, events)

        # Should raise error
        with pytest.raises(ResumeError, match="Cannot resume build that already stuck"):
            replay_journal_for_resume(build_id, builds_dir)


def test_replay_journal_for_resume_doom_loop_detection():
    """Test doom loop counter reconstruction."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        builds_dir = tmpdir_path / ".raw" / "builds"
        builds_dir.mkdir(parents=True)

        build_id = "build-doom"

        # Create journal with repeated gate failures
        events = [
            {
                "event_type": BuildEventType.BUILD_STARTED.value,
                "timestamp": 1234567890.0,
                "build_id": build_id,
                "iteration": 0,
                "workflow_id": "test-workflow",
                "intent": None,
                "config": {"budgets": {}, "gates": {}, "skills": {}, "mode": {}},
            },
            # Iteration 1 - validate fails
            {
                "event_type": BuildEventType.ITERATION_STARTED.value,
                "timestamp": 1234567891.0,
                "build_id": build_id,
                "iteration": 1,
                "mode": "execute",
            },
            {
                "event_type": BuildEventType.GATE_COMPLETED.value,
                "timestamp": 1234567892.0,
                "build_id": build_id,
                "iteration": 1,
                "gate": "validate",
                "passed": False,
                "duration_seconds": 1.0,
                "output_path": "/logs/validate.log",
            },
            {
                "event_type": BuildEventType.MODE_SWITCHED.value,
                "timestamp": 1234567893.0,
                "build_id": build_id,
                "iteration": 1,
                "mode": "plan",
                "context": "Gates failed: validate",
            },
            # Iteration 2 - validate fails again (same signature)
            {
                "event_type": BuildEventType.ITERATION_STARTED.value,
                "timestamp": 1234567894.0,
                "build_id": build_id,
                "iteration": 2,
                "mode": "execute",
            },
            {
                "event_type": BuildEventType.GATE_COMPLETED.value,
                "timestamp": 1234567895.0,
                "build_id": build_id,
                "iteration": 2,
                "gate": "validate",
                "passed": False,
                "duration_seconds": 1.0,
                "output_path": "/logs/validate.log",
            },
        ]

        create_test_journal(builds_dir, build_id, events)

        # Replay journal
        state = replay_journal_for_resume(build_id, builds_dir)

        # Should detect doom loop counter = 2 (same failure twice)
        assert state.doom_loop_counter == 2
        assert state.last_gate_results_signature == "validate:False"


def test_replay_journal_for_resume_empty_journal():
    """Test error with empty journal."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        builds_dir = tmpdir_path / ".raw" / "builds"
        builds_dir.mkdir(parents=True)

        build_id = "build-empty"
        create_test_journal(builds_dir, build_id, [])

        with pytest.raises(ResumeError, match="Empty journal"):
            replay_journal_for_resume(build_id, builds_dir)


def test_replay_journal_for_resume_missing_workflow_id():
    """Test error when workflow_id cannot be determined."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        builds_dir = tmpdir_path / ".raw" / "builds"
        builds_dir.mkdir(parents=True)

        build_id = "build-invalid"

        # Create journal without BUILD_STARTED event
        events = [
            {
                "event_type": BuildEventType.ITERATION_STARTED.value,
                "timestamp": 1234567891.0,
                "build_id": build_id,
                "iteration": 1,
                "mode": "plan",
            }
        ]

        create_test_journal(builds_dir, build_id, events)

        with pytest.raises(ResumeError, match="Cannot determine workflow_id"):
            replay_journal_for_resume(build_id, builds_dir)

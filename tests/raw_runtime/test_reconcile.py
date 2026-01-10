"""Tests for run reconciliation - detecting and marking crashed runs."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from raw_runtime.journal import LocalJournalWriter
from raw_runtime.models import RunStatus
from raw_runtime.reconcile import reconcile_run, scan_and_reconcile
from raw_runtime.reducer import ManifestReducer


class TestReconcileRun:
    """Tests for reconcile_run()."""

    def test_reconcile_stale_run(self, tmp_path: Path) -> None:
        """Test reconciling a stale run marks it as crashed."""
        run_dir = tmp_path / "run_123"
        run_dir.mkdir()
        journal_path = run_dir / "events.jsonl"

        # Write events for a workflow that started but never completed
        from raw_runtime.events import (
            StepStartedEvent,
            WorkflowStartedEvent,
        )

        # Create events from 2 hours ago (stale)
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)

        with LocalJournalWriter(journal_path) as writer:
            writer.write_event(
                WorkflowStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    workflow_name="TestWorkflow",
                    timestamp=old_time,
                )
            )
            writer.write_event(
                StepStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    step_name="step1",
                    timestamp=old_time,
                )
            )

        # Backdate the file modification time to simulate stale file
        import os

        old_timestamp = old_time.timestamp()
        os.utime(journal_path, (old_timestamp, old_timestamp))

        # Reconcile with 1-hour timeout (run is 2 hours old)
        result = reconcile_run(run_dir, stale_timeout_seconds=3600, mark_as_crashed=True)

        # Should mark as crashed
        assert result is not None
        assert result.previous_status == RunStatus.RUNNING
        assert result.new_status == RunStatus.CRASHED
        assert result.action == "marked_crashed"
        assert "inactive" in result.message.lower()

        # Verify workflow.failed event was written to journal
        from raw_runtime.reducer import ManifestReducer

        reducer = ManifestReducer()
        manifest = reducer.reduce_from_file(journal_path)
        assert manifest.run.status == RunStatus.CRASHED
        assert "terminated unexpectedly" in manifest.error.lower()

    def test_reconcile_active_run_no_action(self, tmp_path: Path) -> None:
        """Test reconciling an active run takes no action."""
        run_dir = tmp_path / "run_123"
        run_dir.mkdir()
        journal_path = run_dir / "events.jsonl"

        # Write events from 30 seconds ago (active)
        from raw_runtime.events import WorkflowStartedEvent

        recent_time = datetime.now(timezone.utc) - timedelta(seconds=30)

        with LocalJournalWriter(journal_path) as writer:
            writer.write_event(
                WorkflowStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    workflow_name="TestWorkflow",
                    timestamp=recent_time,
                )
            )

        # Reconcile with 1-hour timeout (run is only 30s old)
        result = reconcile_run(run_dir, stale_timeout_seconds=3600, mark_as_crashed=True)

        # Should take no action
        assert result is None

    def test_reconcile_completed_run_no_action(self, tmp_path: Path) -> None:
        """Test reconciling a completed run takes no action."""
        run_dir = tmp_path / "run_123"
        run_dir.mkdir()
        journal_path = run_dir / "events.jsonl"

        # Write complete workflow events
        from raw_runtime.events import (
            StepCompletedEvent,
            StepStartedEvent,
            WorkflowCompletedEvent,
            WorkflowStartedEvent,
        )

        with LocalJournalWriter(journal_path) as writer:
            writer.write_event(
                WorkflowStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    workflow_name="TestWorkflow",
                )
            )
            writer.write_event(
                StepStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    step_name="step1",
                )
            )
            writer.write_event(
                StepCompletedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    step_name="step1",
                    duration_seconds=1.0,
                    result_type="str",
                )
            )
            writer.write_event(
                WorkflowCompletedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    duration_seconds=1.0,
                    step_count=1,
                )
            )

        # Reconcile
        result = reconcile_run(run_dir, stale_timeout_seconds=0, mark_as_crashed=True)

        # Should take no action (already terminal)
        assert result is None

    def test_reconcile_failed_run_no_action(self, tmp_path: Path) -> None:
        """Test reconciling a failed run takes no action."""
        run_dir = tmp_path / "run_123"
        run_dir.mkdir()
        journal_path = run_dir / "events.jsonl"

        # Write failed workflow events
        from raw_runtime.events import (
            StepFailedEvent,
            StepStartedEvent,
            WorkflowFailedEvent,
            WorkflowStartedEvent,
        )

        with LocalJournalWriter(journal_path) as writer:
            writer.write_event(
                WorkflowStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    workflow_name="TestWorkflow",
                )
            )
            writer.write_event(
                StepStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    step_name="step1",
                )
            )
            writer.write_event(
                StepFailedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    step_name="step1",
                    error="Something went wrong",
                    duration_seconds=0.5,
                )
            )
            writer.write_event(
                WorkflowFailedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    error="Step failed",
                    failed_step="step1",
                    duration_seconds=0.5,
                )
            )

        # Reconcile
        result = reconcile_run(run_dir, stale_timeout_seconds=0, mark_as_crashed=True)

        # Should take no action (already terminal)
        assert result is None

    def test_reconcile_dry_run_mode(self, tmp_path: Path) -> None:
        """Test dry-run mode reports but doesn't modify journal."""
        run_dir = tmp_path / "run_123"
        run_dir.mkdir()
        journal_path = run_dir / "events.jsonl"

        # Write stale events
        from raw_runtime.events import WorkflowStartedEvent

        old_time = datetime.now(timezone.utc) - timedelta(hours=2)

        with LocalJournalWriter(journal_path) as writer:
            writer.write_event(
                WorkflowStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    workflow_name="TestWorkflow",
                    timestamp=old_time,
                )
            )

        # Backdate the file modification time
        import os

        old_timestamp = old_time.timestamp()
        os.utime(journal_path, (old_timestamp, old_timestamp))

        # Count journal lines before
        lines_before = len(journal_path.read_text().strip().split("\n"))

        # Reconcile in dry-run mode
        result = reconcile_run(run_dir, stale_timeout_seconds=3600, mark_as_crashed=False)

        # Should report action but not modify journal
        assert result is not None
        assert result.action == "would_mark_crashed"
        assert "would mark" in result.message.lower()

        # Verify journal unchanged
        lines_after = len(journal_path.read_text().strip().split("\n"))
        assert lines_after == lines_before

        # Verify status still RUNNING
        reducer = ManifestReducer()
        manifest = reducer.reduce_from_file(journal_path)
        assert manifest.run.status == RunStatus.RUNNING

    def test_reconcile_missing_journal(self, tmp_path: Path) -> None:
        """Test reconciling run without journal returns None."""
        run_dir = tmp_path / "run_123"
        run_dir.mkdir()

        # No events.jsonl file
        result = reconcile_run(run_dir, stale_timeout_seconds=3600, mark_as_crashed=True)

        # Should return None (can't reconcile without journal)
        assert result is None

    def test_reconcile_corrupt_journal(self, tmp_path: Path) -> None:
        """Test reconciling run with corrupt journal returns error result."""
        run_dir = tmp_path / "run_123"
        run_dir.mkdir()
        journal_path = run_dir / "events.jsonl"

        # Write corrupt journal
        journal_path.write_text("this is not valid json\n")

        # Reconcile
        result = reconcile_run(run_dir, stale_timeout_seconds=3600, mark_as_crashed=True)

        # Should return error result
        assert result is not None
        assert result.action == "error"
        assert "failed to read journal" in result.message.lower()


class TestScanAndReconcile:
    """Tests for scan_and_reconcile()."""

    def test_scan_empty_directory(self, tmp_path: Path) -> None:
        """Test scanning empty directory returns no results."""
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        results = scan_and_reconcile(workflows_dir)
        assert results == []

    def test_scan_multiple_runs(self, tmp_path: Path) -> None:
        """Test scanning multiple runs reconciles stale ones."""
        workflows_dir = tmp_path / "workflows"
        workflow1_dir = workflows_dir / "workflow1"
        workflow1_dir.mkdir(parents=True)
        runs_dir = workflow1_dir / "runs"
        runs_dir.mkdir()

        # Create 3 runs: 1 stale, 1 active, 1 completed
        from raw_runtime.events import (
            StepCompletedEvent,
            StepStartedEvent,
            WorkflowCompletedEvent,
            WorkflowStartedEvent,
        )

        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        recent_time = datetime.now(timezone.utc) - timedelta(seconds=30)

        # Stale run
        stale_run_dir = runs_dir / "run_stale"
        stale_run_dir.mkdir()
        stale_journal = stale_run_dir / "events.jsonl"
        with LocalJournalWriter(stale_journal) as writer:
            writer.write_event(
                WorkflowStartedEvent(
                    workflow_id="workflow1",
                    run_id="run_stale",
                    workflow_name="Workflow1",
                    timestamp=old_time,
                )
            )

        # Backdate file
        import os

        old_timestamp = old_time.timestamp()
        os.utime(stale_journal, (old_timestamp, old_timestamp))

        # Active run
        active_run_dir = runs_dir / "run_active"
        active_run_dir.mkdir()
        with LocalJournalWriter(active_run_dir / "events.jsonl") as writer:
            writer.write_event(
                WorkflowStartedEvent(
                    workflow_id="workflow1",
                    run_id="run_active",
                    workflow_name="Workflow1",
                    timestamp=recent_time,
                )
            )

        # Completed run
        completed_run_dir = runs_dir / "run_completed"
        completed_run_dir.mkdir()
        with LocalJournalWriter(completed_run_dir / "events.jsonl") as writer:
            writer.write_event(
                WorkflowStartedEvent(
                    workflow_id="workflow1",
                    run_id="run_completed",
                    workflow_name="Workflow1",
                )
            )
            writer.write_event(
                StepStartedEvent(
                    workflow_id="workflow1",
                    run_id="run_completed",
                    step_name="step1",
                )
            )
            writer.write_event(
                StepCompletedEvent(
                    workflow_id="workflow1",
                    run_id="run_completed",
                    step_name="step1",
                    duration_seconds=1.0,
                    result_type="str",
                )
            )
            writer.write_event(
                WorkflowCompletedEvent(
                    workflow_id="workflow1",
                    run_id="run_completed",
                    duration_seconds=1.0,
                    step_count=1,
                )
            )

        # Scan and reconcile
        results = scan_and_reconcile(workflows_dir, stale_timeout_seconds=3600)

        # Should only reconcile the stale run
        assert len(results) == 1
        assert results[0].run_id == "run_stale"
        assert results[0].action == "marked_crashed"

    def test_scan_dry_run_mode(self, tmp_path: Path) -> None:
        """Test scanning in dry-run mode doesn't modify journals."""
        workflows_dir = tmp_path / "workflows"
        workflow_dir = workflows_dir / "workflow1" / "runs" / "run_stale"
        workflow_dir.mkdir(parents=True)
        journal_path = workflow_dir / "events.jsonl"

        # Create stale run
        from raw_runtime.events import WorkflowStartedEvent

        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        with LocalJournalWriter(journal_path) as writer:
            writer.write_event(
                WorkflowStartedEvent(
                    workflow_id="workflow1",
                    run_id="run_stale",
                    workflow_name="Workflow1",
                    timestamp=old_time,
                )
            )

        # Backdate file
        import os

        old_timestamp = old_time.timestamp()
        os.utime(journal_path, (old_timestamp, old_timestamp))

        lines_before = len(journal_path.read_text().strip().split("\n"))

        # Scan in dry-run mode
        results = scan_and_reconcile(workflows_dir, stale_timeout_seconds=3600, dry_run=True)

        # Should report but not modify
        assert len(results) == 1
        assert results[0].action == "would_mark_crashed"

        lines_after = len(journal_path.read_text().strip().split("\n"))
        assert lines_after == lines_before

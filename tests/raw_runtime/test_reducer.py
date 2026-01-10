"""Tests for ManifestReducer - rebuilding manifests from event journals."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from raw_runtime.journal import LocalJournalWriter
from raw_runtime.models import RunStatus, StepStatus
from raw_runtime.reducer import ManifestReducer


class TestManifestReducer:
    """Tests for ManifestReducer."""

    def test_basic_workflow_success(self) -> None:
        """Test reducing a basic successful workflow."""
        events = [
            {
                "event_type": "workflow.started",
                "workflow_id": "test-workflow",
                "run_id": "run_123",
                "workflow_name": "TestWorkflow",
                "workflow_version": "1.0.0",
                "parameters": {"arg": "value"},
                "timestamp": "2025-01-10T12:00:00Z",
            },
            {
                "event_type": "step.started",
                "workflow_id": "test-workflow",
                "run_id": "run_123",
                "step_name": "step1",
                "timestamp": "2025-01-10T12:00:01Z",
            },
            {
                "event_type": "step.completed",
                "workflow_id": "test-workflow",
                "run_id": "run_123",
                "step_name": "step1",
                "duration_seconds": 1.5,
                "result_type": "str",
                "timestamp": "2025-01-10T12:00:02.5Z",
            },
            {
                "event_type": "workflow.completed",
                "workflow_id": "test-workflow",
                "run_id": "run_123",
                "duration_seconds": 2.5,
                "step_count": 1,
                "timestamp": "2025-01-10T12:00:02.5Z",
            },
        ]

        reducer = ManifestReducer()
        manifest = reducer.reduce_from_events(events)

        # Verify workflow info
        assert manifest.workflow.id == "test-workflow"
        assert manifest.workflow.short_name == "TestWorkflow"
        assert manifest.workflow.version == "1.0.0"

        # Verify run info
        assert manifest.run.run_id == "run_123"
        assert manifest.run.status == RunStatus.SUCCESS
        assert manifest.run.parameters == {"arg": "value"}
        assert manifest.error is None  # Error is on Manifest, not RunInfo

        # Verify steps
        assert len(manifest.steps) == 1
        assert manifest.steps[0].name == "step1"
        assert manifest.steps[0].status == StepStatus.SUCCESS
        assert manifest.steps[0].duration_seconds == 1.5

    def test_multiple_steps(self) -> None:
        """Test reducing workflow with multiple steps."""
        events = [
            {
                "event_type": "workflow.started",
                "workflow_id": "test-workflow",
                "run_id": "run_123",
                "workflow_name": "TestWorkflow",
                "timestamp": "2025-01-10T12:00:00Z",
            },
            {
                "event_type": "step.started",
                "step_name": "step1",
                "timestamp": "2025-01-10T12:00:01Z",
            },
            {
                "event_type": "step.completed",
                "step_name": "step1",
                "duration_seconds": 1.0,
                "result_type": "str",
                "timestamp": "2025-01-10T12:00:02Z",
            },
            {
                "event_type": "step.started",
                "step_name": "step2",
                "timestamp": "2025-01-10T12:00:02Z",
            },
            {
                "event_type": "step.completed",
                "step_name": "step2",
                "duration_seconds": 2.0,
                "result_type": "int",
                "timestamp": "2025-01-10T12:00:04Z",
            },
            {
                "event_type": "workflow.completed",
                "duration_seconds": 4.0,
                "step_count": 2,
                "timestamp": "2025-01-10T12:00:04Z",
            },
        ]

        reducer = ManifestReducer()
        manifest = reducer.reduce_from_events(events)

        # Verify steps
        assert len(manifest.steps) == 2
        assert manifest.steps[0].name == "step1"
        assert manifest.steps[0].status == StepStatus.SUCCESS
        assert manifest.steps[1].name == "step2"
        assert manifest.steps[1].status == StepStatus.SUCCESS

    def test_step_failure(self) -> None:
        """Test reducing workflow with failed step."""
        events = [
            {
                "event_type": "workflow.started",
                "workflow_id": "test-workflow",
                "run_id": "run_123",
                "workflow_name": "TestWorkflow",
                "timestamp": "2025-01-10T12:00:00Z",
            },
            {
                "event_type": "step.started",
                "step_name": "step1",
                "timestamp": "2025-01-10T12:00:01Z",
            },
            {
                "event_type": "step.failed",
                "step_name": "step1",
                "error": "Division by zero",
                "duration_seconds": 0.5,
                "timestamp": "2025-01-10T12:00:01.5Z",
            },
            {
                "event_type": "workflow.failed",
                "error": "Step step1 failed",
                "failed_step": "step1",
                "duration_seconds": 1.5,
                "timestamp": "2025-01-10T12:00:01.5Z",
            },
        ]

        reducer = ManifestReducer()
        manifest = reducer.reduce_from_events(events)

        # Verify run failed
        assert manifest.run.status == RunStatus.FAILED
        assert manifest.error == "Step step1 failed"  # Error is on Manifest, not RunInfo

        # Verify step failed
        assert len(manifest.steps) == 1
        assert manifest.steps[0].status == StepStatus.FAILED
        assert manifest.steps[0].error == "Division by zero"

    def test_step_retry(self) -> None:
        """Test reducer tracks step retries."""
        events = [
            {
                "event_type": "workflow.started",
                "workflow_id": "test-workflow",
                "run_id": "run_123",
                "workflow_name": "TestWorkflow",
                "timestamp": "2025-01-10T12:00:00Z",
            },
            {
                "event_type": "step.started",
                "step_name": "step1",
                "timestamp": "2025-01-10T12:00:01Z",
            },
            {
                "event_type": "step.retry",
                "step_name": "step1",
                "attempt": 1,
                "max_attempts": 3,
                "error": "Network timeout",
                "delay_seconds": 1.0,
                "timestamp": "2025-01-10T12:00:02Z",
            },
            {
                "event_type": "step.retry",
                "step_name": "step1",
                "attempt": 2,
                "max_attempts": 3,
                "error": "Network timeout",
                "delay_seconds": 2.0,
                "timestamp": "2025-01-10T12:00:04Z",
            },
            {
                "event_type": "step.completed",
                "step_name": "step1",
                "duration_seconds": 6.0,
                "result_type": "str",
                "timestamp": "2025-01-10T12:00:07Z",
            },
            {
                "event_type": "workflow.completed",
                "duration_seconds": 7.0,
                "step_count": 1,
                "timestamp": "2025-01-10T12:00:07Z",
            },
        ]

        reducer = ManifestReducer()
        manifest = reducer.reduce_from_events(events)

        # Verify step succeeded after retries
        assert len(manifest.steps) == 1
        assert manifest.steps[0].status == StepStatus.SUCCESS
        assert manifest.steps[0].retries == 2  # Two retries

    def test_cache_hit(self) -> None:
        """Test reducer marks cached steps."""
        events = [
            {
                "event_type": "workflow.started",
                "workflow_id": "test-workflow",
                "run_id": "run_123",
                "workflow_name": "TestWorkflow",
                "timestamp": "2025-01-10T12:00:00Z",
            },
            {
                "event_type": "step.started",
                "step_name": "step1",
                "timestamp": "2025-01-10T12:00:01Z",
            },
            {
                "event_type": "cache.hit",
                "step_name": "step1",
                "cache_key": "abc123",
                "timestamp": "2025-01-10T12:00:01Z",
            },
            {
                "event_type": "step.completed",
                "step_name": "step1",
                "duration_seconds": 0.01,
                "result_type": "str",
                "timestamp": "2025-01-10T12:00:01.01Z",
            },
            {
                "event_type": "workflow.completed",
                "duration_seconds": 1.01,
                "step_count": 1,
                "timestamp": "2025-01-10T12:00:01.01Z",
            },
        ]

        reducer = ManifestReducer()
        manifest = reducer.reduce_from_events(events)

        # Verify step marked as cached
        assert len(manifest.steps) == 1
        assert manifest.steps[0].cached is True

    def test_skipped_step(self) -> None:
        """Test reducer handles skipped steps."""
        events = [
            {
                "event_type": "workflow.started",
                "workflow_id": "test-workflow",
                "run_id": "run_123",
                "workflow_name": "TestWorkflow",
                "timestamp": "2025-01-10T12:00:00Z",
            },
            {
                "event_type": "step.skipped",
                "step_name": "step1",
                "reason": "Condition not met",
                "timestamp": "2025-01-10T12:00:01Z",
            },
            {
                "event_type": "workflow.completed",
                "duration_seconds": 1.0,
                "step_count": 0,
                "timestamp": "2025-01-10T12:00:01Z",
            },
        ]

        reducer = ManifestReducer()
        manifest = reducer.reduce_from_events(events)

        # Verify skipped step
        assert len(manifest.steps) == 1
        assert manifest.steps[0].status == StepStatus.SKIPPED
        assert manifest.steps[0].error == "Condition not met"

    def test_artifacts(self) -> None:
        """Test reducer collects artifacts."""
        events = [
            {
                "event_type": "workflow.started",
                "workflow_id": "test-workflow",
                "run_id": "run_123",
                "workflow_name": "TestWorkflow",
                "timestamp": "2025-01-10T12:00:00Z",
            },
            {
                "event_type": "artifact.created",
                "artifact_type": "report",
                "path": "output/report.pdf",
                "size_bytes": 12345,
                "timestamp": "2025-01-10T12:00:01Z",
            },
            {
                "event_type": "artifact.created",
                "artifact_type": "data",
                "path": "output/data.json",
                "size_bytes": 6789,
                "timestamp": "2025-01-10T12:00:02Z",
            },
            {
                "event_type": "workflow.completed",
                "duration_seconds": 2.0,
                "step_count": 0,
                "timestamp": "2025-01-10T12:00:02Z",
            },
        ]

        reducer = ManifestReducer()
        manifest = reducer.reduce_from_events(events)

        # Verify artifacts
        assert len(manifest.artifacts) == 2
        assert manifest.artifacts[0].type == "report"
        assert manifest.artifacts[0].path == "output/report.pdf"
        assert manifest.artifacts[0].size_bytes == 12345
        assert manifest.artifacts[1].type == "data"
        assert manifest.artifacts[1].path == "output/data.json"

    def test_missing_workflow_started_raises(self) -> None:
        """Test reducer raises if workflow.started is missing."""
        events = [
            {
                "event_type": "step.started",
                "step_name": "step1",
                "timestamp": "2025-01-10T12:00:01Z",
            },
        ]

        reducer = ManifestReducer()
        with pytest.raises(ValueError, match="Missing required workflow metadata"):
            reducer.reduce_from_events(events)

    def test_empty_journal_raises(self) -> None:
        """Test reducer raises on empty journal."""
        reducer = ManifestReducer()
        with pytest.raises(ValueError, match="No events to reduce"):
            reducer.reduce_from_events([])

    def test_reduce_from_file(self, tmp_path: Path) -> None:
        """Test reducing from journal file."""
        journal_path = tmp_path / "events.jsonl"

        # Write events to journal
        from raw_runtime.events import (
            StepCompletedEvent,
            StepStartedEvent,
            WorkflowCompletedEvent,
            WorkflowStartedEvent,
        )

        writer = LocalJournalWriter(journal_path)

        events = [
            WorkflowStartedEvent(
                workflow_id="test-workflow",
                run_id="run_123",
                workflow_name="TestWorkflow",
            ),
            StepStartedEvent(
                workflow_id="test-workflow",
                run_id="run_123",
                step_name="step1",
            ),
            StepCompletedEvent(
                workflow_id="test-workflow",
                run_id="run_123",
                step_name="step1",
                duration_seconds=1.0,
                result_type="str",
            ),
            WorkflowCompletedEvent(
                workflow_id="test-workflow",
                run_id="run_123",
                duration_seconds=1.0,
                step_count=1,
            ),
        ]

        for event in events:
            writer.write_event(event)
        writer.close()

        # Reduce from file
        reducer = ManifestReducer()
        manifest = reducer.reduce_from_file(journal_path)

        # Verify manifest
        assert manifest.workflow.id == "test-workflow"
        assert manifest.run.status == RunStatus.SUCCESS
        assert len(manifest.steps) == 1
        assert manifest.steps[0].status == StepStatus.SUCCESS

    def test_handles_missing_step_started(self) -> None:
        """Test reducer handles step.completed without step.started."""
        events = [
            {
                "event_type": "workflow.started",
                "workflow_id": "test-workflow",
                "run_id": "run_123",
                "workflow_name": "TestWorkflow",
                "timestamp": "2025-01-10T12:00:00Z",
            },
            # Missing step.started
            {
                "event_type": "step.completed",
                "step_name": "step1",
                "duration_seconds": 1.0,
                "result_type": "str",
                "timestamp": "2025-01-10T12:00:01Z",
            },
            {
                "event_type": "workflow.completed",
                "duration_seconds": 1.0,
                "step_count": 1,
                "timestamp": "2025-01-10T12:00:01Z",
            },
        ]

        reducer = ManifestReducer()
        manifest = reducer.reduce_from_events(events)

        # Should create step even without step.started
        assert len(manifest.steps) == 1
        assert manifest.steps[0].status == StepStatus.SUCCESS

    def test_workflow_without_completion_event(self) -> None:
        """Test reducer handles crashed workflow (no workflow.completed/failed)."""
        events = [
            {
                "event_type": "workflow.started",
                "workflow_id": "test-workflow",
                "run_id": "run_123",
                "workflow_name": "TestWorkflow",
                "timestamp": "2025-01-10T12:00:00Z",
            },
            {
                "event_type": "step.started",
                "step_name": "step1",
                "timestamp": "2025-01-10T12:00:01Z",
            },
            # Crash - no step.completed, no workflow.completed
        ]

        reducer = ManifestReducer()
        manifest = reducer.reduce_from_events(events)

        # Should create manifest with RUNNING status (crashed)
        assert manifest.run.status == RunStatus.RUNNING
        assert len(manifest.steps) == 1
        assert manifest.steps[0].status == StepStatus.RUNNING

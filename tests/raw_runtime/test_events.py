"""Tests for RAW event models and ApprovalRegistry."""

import asyncio
from datetime import datetime, timezone

import pytest

from raw_runtime.bus import ApprovalRegistry
from raw_runtime.events import (
    ApprovalReceivedEvent,
    ApprovalRequestedEvent,
    EventType,
    StepCompletedEvent,
    StepFailedEvent,
    StepStartedEvent,
    WorkflowCompletedEvent,
    WorkflowStartedEvent,
)


class TestEventModels:
    """Tests for event model creation and serialization."""

    def test_workflow_started_event(self) -> None:
        event = WorkflowStartedEvent(
            workflow_id="test-workflow-123",
            run_id="run_20250107_120000",
            workflow_name="test-workflow",
            workflow_version="1.0.0",
            parameters={"ticker": "TSLA"},
        )
        assert event.event_type == EventType.WORKFLOW_STARTED
        assert event.workflow_id == "test-workflow-123"
        assert event.workflow_name == "test-workflow"
        assert len(event.event_id) == 12

    def test_workflow_completed_event(self) -> None:
        event = WorkflowCompletedEvent(
            workflow_id="test-workflow-123",
            run_id="run_20250107_120000",
            duration_seconds=5.5,
            step_count=3,
            artifacts=["output.pdf"],
        )
        assert event.event_type == EventType.WORKFLOW_COMPLETED
        assert event.duration_seconds == 5.5
        assert event.step_count == 3

    def test_step_started_event(self) -> None:
        event = StepStartedEvent(
            workflow_id="test-workflow-123",
            run_id="run_20250107_120000",
            step_name="fetch_data",
            input_types=["str", "int"],
            output_type="dict",
        )
        assert event.event_type == EventType.STEP_STARTED
        assert event.step_name == "fetch_data"
        assert event.input_types == ["str", "int"]

    def test_step_completed_event(self) -> None:
        event = StepCompletedEvent(
            workflow_id="test-workflow-123",
            run_id="run_20250107_120000",
            step_name="fetch_data",
            duration_seconds=1.2,
            result_type="dict",
        )
        assert event.event_type == EventType.STEP_COMPLETED
        assert event.duration_seconds == 1.2

    def test_step_failed_event(self) -> None:
        event = StepFailedEvent(
            workflow_id="test-workflow-123",
            run_id="run_20250107_120000",
            step_name="fetch_data",
            error="Connection timeout",
            duration_seconds=30.0,
        )
        assert event.event_type == EventType.STEP_FAILED
        assert event.error == "Connection timeout"

    def test_approval_requested_event(self) -> None:
        event = ApprovalRequestedEvent(
            workflow_id="test-workflow-123",
            run_id="run_20250107_120000",
            step_name="deploy",
            prompt="Deploy to production?",
            options=["approve", "reject"],
            timeout_seconds=3600,
        )
        assert event.event_type == EventType.APPROVAL_REQUESTED
        assert event.prompt == "Deploy to production?"
        assert "approve" in event.options

    def test_approval_received_event(self) -> None:
        event = ApprovalReceivedEvent(
            workflow_id="test-workflow-123",
            run_id="run_20250107_120000",
            step_name="deploy",
            decision="approve",
            approved_by="user@example.com",
        )
        assert event.event_type == EventType.APPROVAL_RECEIVED
        assert event.decision == "approve"

    def test_event_timestamp_auto_generated(self) -> None:
        before = datetime.now(timezone.utc)
        event = WorkflowStartedEvent(
            workflow_id="test",
            workflow_name="test",
        )
        after = datetime.now(timezone.utc)
        assert before <= event.timestamp <= after


class TestApprovalRegistry:
    """Tests for ApprovalRegistry."""

    async def test_request_creates_future(self) -> None:
        registry = ApprovalRegistry()
        future = registry.request("wf-123", "deploy")
        assert not future.done()
        assert registry.is_pending("wf-123", "deploy")

    async def test_resolve_completes_future(self) -> None:
        registry = ApprovalRegistry()
        future = registry.request("wf-123", "deploy")

        result = registry.resolve("wf-123", "deploy", "approve")
        assert result is True
        assert future.done()
        assert future.result() == "approve"
        assert not registry.is_pending("wf-123", "deploy")

    async def test_resolve_nonexistent_returns_false(self) -> None:
        registry = ApprovalRegistry()
        result = registry.resolve("wf-123", "nonexistent", "approve")
        assert result is False

    async def test_cancel_sets_exception(self) -> None:
        registry = ApprovalRegistry()
        future = registry.request("wf-123", "deploy")

        result = registry.cancel("wf-123", "deploy", "Timeout")
        assert result is True
        assert future.done()
        with pytest.raises(asyncio.CancelledError):
            future.result()

    async def test_cancel_nonexistent_returns_false(self) -> None:
        registry = ApprovalRegistry()
        result = registry.cancel("wf-123", "nonexistent", "Reason")
        assert result is False

    async def test_is_pending(self) -> None:
        registry = ApprovalRegistry()
        assert not registry.is_pending("wf-123", "deploy")

        registry.request("wf-123", "deploy")
        assert registry.is_pending("wf-123", "deploy")

    async def test_list_pending(self) -> None:
        registry = ApprovalRegistry()
        registry.request("wf-123", "step1")
        registry.request("wf-456", "step2")

        pending = registry.list_pending()
        assert len(pending) == 2
        assert ("wf-123", None, "step1") in pending
        assert ("wf-456", None, "step2") in pending

    async def test_duplicate_request_raises(self) -> None:
        registry = ApprovalRegistry()
        registry.request("wf-123", "deploy")

        with pytest.raises(ValueError, match="Approval already pending"):
            registry.request("wf-123", "deploy")

    async def test_concurrent_runs_with_run_id(self) -> None:
        """Test that concurrent runs of the same workflow don't collide."""
        registry = ApprovalRegistry()

        # Two runs of the same workflow, same step
        future1 = registry.request("wf-123", "deploy", run_id="run-001")
        future2 = registry.request("wf-123", "deploy", run_id="run-002")

        # Both should be pending
        assert registry.is_pending("wf-123", "deploy", "run-001")
        assert registry.is_pending("wf-123", "deploy", "run-002")

        # Resolve first run
        registry.resolve("wf-123", "deploy", "approve", run_id="run-001")
        assert future1.done()
        assert not future2.done()
        assert future1.result() == "approve"

        # Resolve second run differently
        registry.resolve("wf-123", "deploy", "reject", run_id="run-002")
        assert future2.done()
        assert future2.result() == "reject"

    async def test_list_pending_with_run_id(self) -> None:
        """Test list_pending returns run_id when provided."""
        registry = ApprovalRegistry()
        registry.request("wf-123", "step1", run_id="run-001")
        registry.request("wf-123", "step1", run_id="run-002")

        pending = registry.list_pending()
        assert len(pending) == 2
        assert ("wf-123", "run-001", "step1") in pending
        assert ("wf-123", "run-002", "step1") in pending

"""Tests for WorkflowContext."""

from pathlib import Path

from raw_runtime.bus import LocalEventBus
from raw_runtime.context import (
    WorkflowContext,
    get_workflow_context,
    set_workflow_context,
)
from raw_runtime.events import (
    ArtifactCreatedEvent,
    Event,
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
    WorkflowStartedEvent,
)
from raw_runtime.models import RunStatus, StepResult, StepStatus


def test_context_creation() -> None:
    """Test creating a workflow context."""
    ctx = WorkflowContext(
        workflow_id="20250106-test-abc123",
        short_name="test",
        parameters={"ticker": "TSLA"},
    )

    assert ctx.workflow_id == "20250106-test-abc123"
    assert ctx.short_name == "test"
    assert ctx.parameters == {"ticker": "TSLA"}
    assert ctx.run_id.startswith("run_")


def test_context_global_access() -> None:
    """Test global context access."""
    # Initially no context
    assert get_workflow_context() is None

    ctx = WorkflowContext(
        workflow_id="20250106-test-abc123",
        short_name="test",
    )
    set_workflow_context(ctx)

    assert get_workflow_context() is ctx

    # Clean up
    set_workflow_context(None)
    assert get_workflow_context() is None


def test_context_manager() -> None:
    """Test context as context manager."""
    assert get_workflow_context() is None

    with WorkflowContext(
        workflow_id="20250106-test-abc123",
        short_name="test",
    ) as ctx:
        assert get_workflow_context() is ctx

    assert get_workflow_context() is None


def test_add_step_result() -> None:
    """Test adding step results."""
    ctx = WorkflowContext(
        workflow_id="20250106-test-abc123",
        short_name="test",
    )

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    step = StepResult(
        name="fetch_data",
        status=StepStatus.SUCCESS,
        started_at=now,
        duration_seconds=1.0,
    )
    ctx.add_step_result(step)

    steps = ctx.get_steps()
    assert len(steps) == 1
    assert steps[0].name == "fetch_data"


def test_add_artifact(tmp_path: Path) -> None:
    """Test adding artifacts."""
    ctx = WorkflowContext(
        workflow_id="20250106-test-abc123",
        short_name="test",
    )

    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    ctx.add_artifact("data", test_file)

    artifacts = ctx.get_artifacts()
    assert len(artifacts) == 1
    assert artifacts[0].type == "data"
    assert artifacts[0].size_bytes == len("test content")


def test_build_manifest() -> None:
    """Test building manifest."""
    ctx = WorkflowContext(
        workflow_id="20250106-test-abc123",
        short_name="test",
        parameters={"ticker": "TSLA"},
    )

    manifest = ctx.build_manifest(status=RunStatus.SUCCESS)

    assert manifest.schema_version == "1.0.0"
    assert manifest.workflow.id == "20250106-test-abc123"
    assert manifest.run.status == RunStatus.SUCCESS
    assert manifest.run.parameters["ticker"] == "TSLA"
    assert manifest.run.environment is not None


def test_finalize_saves_manifest(tmp_path: Path) -> None:
    """Test that finalize saves the manifest."""
    workflow_dir = tmp_path / "workflow"
    workflow_dir.mkdir()

    ctx = WorkflowContext(
        workflow_id="20250106-test-abc123",
        short_name="test",
        workflow_dir=workflow_dir,
    )

    ctx.finalize(status="success")

    # Manifest is saved directly in workflow_dir (for run directories)
    manifest_path = workflow_dir / "manifest.json"
    assert manifest_path.exists()


class TestContextEvents:
    """Tests verifying WorkflowContext via emitted events."""

    def test_context_manager_emits_workflow_started(self) -> None:
        """Verify WorkflowStartedEvent is emitted when entering context."""
        bus = LocalEventBus()
        events: list[Event] = []
        bus.subscribe(lambda e: events.append(e))

        with WorkflowContext(
            workflow_id="test-workflow-123",
            short_name="test",
            parameters={"key": "value"},
            event_bus=bus,
        ):
            pass

        assert len(events) == 1
        assert isinstance(events[0], WorkflowStartedEvent)
        assert events[0].workflow_id == "test-workflow-123"
        assert events[0].workflow_name == "test"
        assert events[0].parameters == {"key": "value"}

    def test_add_artifact_emits_event(self, tmp_path: Path) -> None:
        """Verify ArtifactCreatedEvent is emitted when adding artifact."""
        bus = LocalEventBus()
        events: list[Event] = []
        bus.subscribe(lambda e: events.append(e))

        ctx = WorkflowContext(
            workflow_id="test-workflow-123",
            short_name="test",
            event_bus=bus,
        )

        test_file = tmp_path / "output.txt"
        test_file.write_text("test content")

        ctx.add_artifact("report", test_file)

        assert len(events) == 1
        assert isinstance(events[0], ArtifactCreatedEvent)
        assert events[0].artifact_type == "report"
        assert events[0].path == str(test_file)
        assert events[0].size_bytes == len("test content")

    def test_finalize_success_emits_completed_event(self) -> None:
        """Verify WorkflowCompletedEvent is emitted on successful finalize."""
        bus = LocalEventBus()
        events: list[Event] = []
        bus.subscribe(lambda e: events.append(e))

        ctx = WorkflowContext(
            workflow_id="test-workflow-123",
            short_name="test",
            event_bus=bus,
        )

        ctx.finalize(status="success")

        assert len(events) == 1
        assert isinstance(events[0], WorkflowCompletedEvent)
        assert events[0].workflow_id == "test-workflow-123"
        assert events[0].step_count == 0
        assert events[0].duration_seconds >= 0

    def test_finalize_failure_emits_failed_event(self) -> None:
        """Verify WorkflowFailedEvent is emitted on failed finalize."""
        bus = LocalEventBus()
        events: list[Event] = []
        bus.subscribe(lambda e: events.append(e))

        ctx = WorkflowContext(
            workflow_id="test-workflow-123",
            short_name="test",
            event_bus=bus,
        )

        ctx.finalize(status="failed", error="Something went wrong")

        assert len(events) == 1
        assert isinstance(events[0], WorkflowFailedEvent)
        assert events[0].workflow_id == "test-workflow-123"
        assert events[0].error == "Something went wrong"

    def test_full_workflow_lifecycle_events(self, tmp_path: Path) -> None:
        """Verify complete event sequence through workflow lifecycle."""
        bus = LocalEventBus()
        events: list[Event] = []
        bus.subscribe(lambda e: events.append(e))

        test_file = tmp_path / "result.txt"
        test_file.write_text("workflow output")

        with WorkflowContext(
            workflow_id="test-workflow-123",
            short_name="test",
            parameters={"input": "data"},
            event_bus=bus,
        ) as ctx:
            ctx.add_artifact("output", test_file)
            ctx.finalize(status="success")

        assert len(events) == 3
        assert isinstance(events[0], WorkflowStartedEvent)
        assert isinstance(events[1], ArtifactCreatedEvent)
        assert isinstance(events[2], WorkflowCompletedEvent)

        # Verify event sequence metadata consistency
        assert events[0].workflow_id == events[1].workflow_id == events[2].workflow_id
        assert events[2].artifacts == [str(test_file)]

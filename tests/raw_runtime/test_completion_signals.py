"""Tests for BaseWorkflow completion signals."""

from pydantic import BaseModel, Field

from raw.validation.signals import CompletionSignal
from raw_runtime import BaseWorkflow


class DemoParams(BaseModel):
    """Demo parameters."""

    value: int = Field(default=0, description="Test value")


class DemoWorkflow(BaseWorkflow[DemoParams]):
    """Demo workflow for completion signals."""

    def run(self) -> int:
        return 0


def test_workflow_success() -> None:
    """Test workflow.success() method."""
    params = DemoParams(value=42)
    workflow = DemoWorkflow(params=params)

    result = workflow.success("Task completed successfully", data={"count": 42})

    assert result.signal == CompletionSignal.SUCCESS
    assert result.message == "Task completed successfully"
    assert result.data == {"count": 42}
    assert result.exit_code == 0
    assert result.is_success()


def test_workflow_error() -> None:
    """Test workflow.error() method."""
    params = DemoParams(value=42)
    workflow = DemoWorkflow(params=params)

    result = workflow.error("Task failed with error")

    assert result.signal == CompletionSignal.ERROR
    assert result.message == "Task failed with error"
    assert result.exit_code == 1
    assert result.is_error()


def test_workflow_error_custom_exit_code() -> None:
    """Test workflow.error() with custom exit code."""
    params = DemoParams(value=42)
    workflow = DemoWorkflow(params=params)

    result = workflow.error("Connection timeout", exit_code=124)

    assert result.signal == CompletionSignal.ERROR
    assert result.exit_code == 124


def test_workflow_complete() -> None:
    """Test workflow.complete() method."""
    params = DemoParams(value=42)
    workflow = DemoWorkflow(params=params)

    result = workflow.complete("All tasks completed", data={"total": 100})

    assert result.signal == CompletionSignal.COMPLETE
    assert result.message == "All tasks completed"
    assert result.data == {"total": 100}
    assert result.exit_code == 0
    assert result.is_complete()
    assert result.is_success()


def test_workflow_success_no_data() -> None:
    """Test workflow.success() without data."""
    params = DemoParams(value=42)
    workflow = DemoWorkflow(params=params)

    result = workflow.success("Done")

    assert result.signal == CompletionSignal.SUCCESS
    assert result.data is None


def test_workflow_complete_no_data() -> None:
    """Test workflow.complete() without data."""
    params = DemoParams(value=42)
    workflow = DemoWorkflow(params=params)

    result = workflow.complete("Finished")

    assert result.signal == CompletionSignal.COMPLETE
    assert result.data is None

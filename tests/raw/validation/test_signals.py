"""Tests for completion signals."""

from raw.validation.signals import CompletionSignal, WorkflowResult


def test_completion_signal_enum() -> None:
    """Test CompletionSignal enum values."""
    assert CompletionSignal.SUCCESS == "success"
    assert CompletionSignal.ERROR == "error"
    assert CompletionSignal.COMPLETE == "complete"


def test_workflow_result_success() -> None:
    """Test WorkflowResult.success() creation."""
    result = WorkflowResult.success("Task completed", data={"count": 42})

    assert result.signal == CompletionSignal.SUCCESS
    assert result.message == "Task completed"
    assert result.data == {"count": 42}
    assert result.exit_code == 0
    assert result.is_success()
    assert not result.is_error()
    assert not result.is_complete()


def test_workflow_result_success_no_data() -> None:
    """Test WorkflowResult.success() without data."""
    result = WorkflowResult.success("Task completed")

    assert result.signal == CompletionSignal.SUCCESS
    assert result.message == "Task completed"
    assert result.data is None
    assert result.exit_code == 0


def test_workflow_result_error() -> None:
    """Test WorkflowResult.error() creation."""
    result = WorkflowResult.error("API rate limit exceeded")

    assert result.signal == CompletionSignal.ERROR
    assert result.message == "API rate limit exceeded"
    assert result.data is None
    assert result.exit_code == 1
    assert not result.is_success()
    assert result.is_error()
    assert not result.is_complete()


def test_workflow_result_error_custom_exit_code() -> None:
    """Test WorkflowResult.error() with custom exit code."""
    result = WorkflowResult.error("Connection timeout", exit_code=124)

    assert result.signal == CompletionSignal.ERROR
    assert result.exit_code == 124


def test_workflow_result_complete() -> None:
    """Test WorkflowResult.complete() creation."""
    result = WorkflowResult.complete("All tasks processed", data={"total": 100})

    assert result.signal == CompletionSignal.COMPLETE
    assert result.message == "All tasks processed"
    assert result.data == {"total": 100}
    assert result.exit_code == 0
    assert result.is_success()
    assert not result.is_error()
    assert result.is_complete()


def test_workflow_result_complete_no_data() -> None:
    """Test WorkflowResult.complete() without data."""
    result = WorkflowResult.complete("Workflow finished")

    assert result.signal == CompletionSignal.COMPLETE
    assert result.message == "Workflow finished"
    assert result.data is None


def test_workflow_result_is_success_for_complete() -> None:
    """Test is_success() returns True for COMPLETE signal."""
    result = WorkflowResult.complete("Done")
    assert result.is_success()
    assert result.is_complete()


def test_workflow_result_serialization() -> None:
    """Test WorkflowResult can be serialized with Pydantic."""
    result = WorkflowResult.success("Test", data={"key": "value"})
    json_data = result.model_dump()

    assert json_data["signal"] == "success"
    assert json_data["message"] == "Test"
    assert json_data["data"] == {"key": "value"}
    assert json_data["exit_code"] == 0


def test_workflow_result_deserialization() -> None:
    """Test WorkflowResult can be deserialized from dict."""
    data = {
        "signal": "error",
        "message": "Failed",
        "data": None,
        "exit_code": 1,
    }
    result = WorkflowResult.model_validate(data)

    assert result.signal == CompletionSignal.ERROR
    assert result.message == "Failed"
    assert result.is_error()


def test_workflow_result_with_complex_data() -> None:
    """Test WorkflowResult with complex nested data."""
    complex_data = {
        "results": [
            {"id": 1, "status": "success"},
            {"id": 2, "status": "failed"},
        ],
        "summary": {"total": 2, "success": 1, "failed": 1},
    }
    result = WorkflowResult.success("Processed items", data=complex_data)

    assert result.data == complex_data
    assert result.data["summary"]["total"] == 2

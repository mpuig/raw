"""Tests for RAW runtime models."""

from datetime import datetime, timezone

from raw_runtime.models import (
    Artifact,
    EnvironmentInfo,
    Manifest,
    RunInfo,
    RunStatus,
    StepResult,
    StepStatus,
    WorkflowInfo,
)


def test_step_result_success() -> None:
    """Test creating a successful step result."""
    now = datetime.now(timezone.utc)
    step = StepResult(
        name="fetch_data",
        status=StepStatus.SUCCESS,
        started_at=now,
        ended_at=now,
        duration_seconds=1.5,
        result={"data_points": 100},
    )
    assert step.name == "fetch_data"
    assert step.status == StepStatus.SUCCESS
    assert step.retries == 0
    assert step.cached is False
    assert step.error is None


def test_step_result_failed() -> None:
    """Test creating a failed step result."""
    now = datetime.now(timezone.utc)
    step = StepResult(
        name="fetch_data",
        status=StepStatus.FAILED,
        started_at=now,
        error="Connection timeout",
    )
    assert step.status == StepStatus.FAILED
    assert step.error == "Connection timeout"


def test_artifact() -> None:
    """Test artifact model."""
    artifact = Artifact(
        type="chart",
        path="results/chart.png",
        size_bytes=12345,
    )
    assert artifact.type == "chart"
    assert artifact.path == "results/chart.png"
    assert artifact.size_bytes == 12345


def test_workflow_info() -> None:
    """Test workflow info model."""
    now = datetime.now(timezone.utc)
    info = WorkflowInfo(
        id="20250106-stock-analysis-abc123",
        short_name="stock-analysis",
        version="1.0.0",
        created_at=now,
    )
    assert info.id == "20250106-stock-analysis-abc123"
    assert info.short_name == "stock-analysis"


def test_run_info() -> None:
    """Test run info model."""
    now = datetime.now(timezone.utc)
    env = EnvironmentInfo(
        hostname="test-host",
        python_version="3.10.0",
        raw_version="0.1.0",
        working_directory="/tmp/test",
    )
    run = RunInfo(
        run_id="run_20250106_120000",
        workflow_id="20250106-stock-analysis-abc123",
        started_at=now,
        status=RunStatus.SUCCESS,
        parameters={"ticker": "TSLA"},
        environment=env,
    )
    assert run.run_id == "run_20250106_120000"
    assert run.status == RunStatus.SUCCESS
    assert run.parameters["ticker"] == "TSLA"


def test_manifest_serialization() -> None:
    """Test manifest can be serialized to JSON."""
    now = datetime.now(timezone.utc)

    workflow = WorkflowInfo(
        id="20250106-test-abc123",
        short_name="test",
        created_at=now,
    )

    run = RunInfo(
        run_id="run_001",
        workflow_id="20250106-test-abc123",
        started_at=now,
        status=RunStatus.SUCCESS,
    )

    manifest = Manifest(
        workflow=workflow,
        run=run,
        steps=[
            StepResult(
                name="step1",
                status=StepStatus.SUCCESS,
                started_at=now,
                duration_seconds=1.0,
            )
        ],
    )

    # Should serialize without error
    json_str = manifest.model_dump_json()
    assert "20250106-test-abc123" in json_str
    assert "step1" in json_str

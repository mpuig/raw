"""Tests for builder gate runner."""

import tempfile
from pathlib import Path

import pytest

from raw.builder.config import BuilderConfig, GateCommand
from raw.builder.gates import (
    CommandGate,
    DryRunGate,
    ValidateGate,
    format_gate_failures,
    save_gate_output,
)
from raw.builder.gates import GateResult


@pytest.mark.asyncio
async def test_validate_gate_success():
    """Test validate gate with valid workflow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workflow_dir = Path(tmpdir)

        # Create valid run.py
        run_py = workflow_dir / "run.py"
        run_py.write_text(
            """#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0"]
# ///
from pydantic import BaseModel
from raw_runtime import BaseWorkflow

class MyWorkflow(BaseWorkflow):
    def run(self) -> int:
        return 0

if __name__ == "__main__":
    MyWorkflow.main()
"""
        )

        gate = ValidateGate()
        result = await gate.run("test-workflow", workflow_dir)

        assert result.gate == "validate"
        assert result.passed is True
        assert result.duration_seconds > 0
        assert "passed" in result.output.lower()


@pytest.mark.asyncio
async def test_validate_gate_failure():
    """Test validate gate with invalid workflow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workflow_dir = Path(tmpdir)

        # Create invalid run.py (missing run() method)
        run_py = workflow_dir / "run.py"
        run_py.write_text(
            """#!/usr/bin/env python3
from pydantic import BaseModel

class MyWorkflow(BaseModel):
    pass
"""
        )

        gate = ValidateGate()
        result = await gate.run("test-workflow", workflow_dir)

        assert result.gate == "validate"
        assert result.passed is False
        assert result.duration_seconds > 0
        assert "failed" in result.output.lower() or "error" in result.output.lower()


@pytest.mark.asyncio
async def test_validate_gate_missing_run_py():
    """Test validate gate with missing run.py."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workflow_dir = Path(tmpdir)

        gate = ValidateGate()
        result = await gate.run("test-workflow", workflow_dir)

        assert result.gate == "validate"
        assert result.passed is False
        assert "run.py not found" in result.output or "error" in result.output.lower()


@pytest.mark.asyncio
async def test_dry_run_gate_missing_dry_run_py():
    """Test dry run gate with missing dry_run.py."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workflow_dir = Path(tmpdir)

        gate = DryRunGate()
        result = await gate.run("test-workflow", workflow_dir)

        assert result.gate == "dry"
        assert result.passed is False
        assert "dry_run.py not found" in result.output


@pytest.mark.asyncio
async def test_command_gate_success():
    """Test command gate with successful command."""
    gate_config = GateCommand(command="echo 'test'", timeout_seconds=5)
    gate = CommandGate("echo-test", gate_config)

    result = await gate.run("test-workflow", Path("/tmp"))

    assert result.gate == "echo-test"
    assert result.passed is True
    assert "test" in result.output
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_command_gate_failure():
    """Test command gate with failing command."""
    gate_config = GateCommand(command="exit 1", timeout_seconds=5)
    gate = CommandGate("fail-test", gate_config)

    result = await gate.run("test-workflow", Path("/tmp"))

    assert result.gate == "fail-test"
    assert result.passed is False
    assert result.exit_code == 1


@pytest.mark.asyncio
async def test_command_gate_timeout():
    """Test command gate timeout."""
    gate_config = GateCommand(command="sleep 10", timeout_seconds=1)
    gate = CommandGate("timeout-test", gate_config)

    result = await gate.run("test-workflow", Path("/tmp"))

    assert result.gate == "timeout-test"
    assert result.passed is False
    assert "timed out" in result.output.lower()
    assert result.exit_code == 124


def test_save_gate_output():
    """Test saving gate output to log file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        build_dir = Path(tmpdir)

        result = GateResult(
            gate="validate",
            passed=True,
            duration_seconds=1.5,
            output="Test output\nLine 2",
            exit_code=0,
        )

        log_path = save_gate_output(result, build_dir)

        assert log_path.exists()
        assert log_path.name == "validate.log"
        assert log_path.read_text() == "Test output\nLine 2"


def test_format_gate_failures_all_pass():
    """Test formatting when all gates pass."""
    results = [
        GateResult(
            gate="validate", passed=True, duration_seconds=1.0, output="OK", exit_code=0
        ),
        GateResult(gate="dry", passed=True, duration_seconds=2.0, output="OK", exit_code=0),
    ]

    formatted = format_gate_failures(results)

    assert "All gates passed" in formatted


def test_format_gate_failures_some_fail():
    """Test formatting gate failures."""
    results = [
        GateResult(
            gate="validate", passed=True, duration_seconds=1.0, output="OK", exit_code=0
        ),
        GateResult(
            gate="dry",
            passed=False,
            duration_seconds=2.0,
            output="Error: something broke",
            exit_code=1,
        ),
        GateResult(
            gate="pytest",
            passed=False,
            duration_seconds=3.0,
            output="3 errors found",
            exit_code=1,
        ),
    ]

    formatted = format_gate_failures(results)

    assert "Gates failed" in formatted
    assert "dry" in formatted
    assert "pytest" in formatted
    assert "validate" not in formatted  # Passed gate should not be included


def test_gate_result_model():
    """Test GateResult model."""
    result = GateResult(
        gate="validate",
        passed=True,
        duration_seconds=1.234,
        output="Test output",
        exit_code=0,
    )

    assert result.gate == "validate"
    assert result.passed is True
    assert result.duration_seconds == 1.234
    assert result.output == "Test output"
    assert result.exit_code == 0

    # Test JSON serialization
    json_data = result.model_dump_json()
    assert "validate" in json_data
    assert "true" in json_data.lower()

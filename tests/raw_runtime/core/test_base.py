"""Tests for BaseWorkflow."""

import json
from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from raw_runtime import BaseWorkflow, step


class GreetParams(BaseModel):
    """Parameters for greeting workflow."""

    name: str = Field(..., description="Name to greet")
    greeting: str = Field(default="Hello", description="Greeting to use")


class GreetWorkflow(BaseWorkflow[GreetParams]):
    """Simple greeting workflow for testing."""

    @step("generate_greeting")
    def generate_greeting(self) -> str:
        return f"{self.params.greeting}, {self.params.name}!"

    def run(self) -> int:
        message = self.generate_greeting()
        self.save("greeting.txt", message)
        return 0


class FailingWorkflow(BaseWorkflow[GreetParams]):
    """Workflow that fails for testing."""

    def run(self) -> int:
        raise ValueError("Intentional failure")


def test_get_params_class() -> None:
    """Test extracting params class from generic."""
    params_class = GreetWorkflow._get_params_class()
    assert params_class is GreetParams


def test_build_argparse() -> None:
    """Test building argparse from Pydantic model."""
    params_class = GreetWorkflow._get_params_class()
    parser = GreetWorkflow._build_argparse(params_class)

    # Parse with required arg
    args = parser.parse_args(["--name", "World"])
    assert args.name == "World"
    assert args.greeting == "Hello"

    # Parse with both args
    args = parser.parse_args(["--name", "Alice", "--greeting", "Hi"])
    assert args.name == "Alice"
    assert args.greeting == "Hi"


def test_workflow_execution(tmp_path: Path) -> None:
    """Test workflow execution saves to results/ directory."""
    import os

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        params = GreetParams(name="Test")
        workflow = GreetWorkflow(params)
        exit_code = workflow.run()

        assert exit_code == 0
        # Results are saved to results/ in CWD
        assert (workflow.results_dir / "greeting.txt").exists()
        content = (workflow.results_dir / "greeting.txt").read_text()
        assert content == "Hello, Test!"
        # Verify results_dir is results/
        assert workflow.results_dir.name == "results"
    finally:
        os.chdir(original_cwd)


def test_save_dict(tmp_path: Path) -> None:
    """Test saving dict as JSON in timestamped directory."""
    import os

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        params = GreetParams(name="Test")
        workflow = GreetWorkflow(params)
        workflow.save("data.json", {"key": "value"})

        # Results are now in timestamped subdirectory
        content = json.loads((workflow.results_dir / "data.json").read_text())
        assert content == {"key": "value"}
    finally:
        os.chdir(original_cwd)


def test_save_pydantic_model(tmp_path: Path) -> None:
    """Test saving Pydantic model as JSON in timestamped directory."""
    import os

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        params = GreetParams(name="Test")
        workflow = GreetWorkflow(params)
        workflow.save("params.json", params)

        # Results are now in timestamped subdirectory
        content = json.loads((workflow.results_dir / "params.json").read_text())
        assert content["name"] == "Test"
        assert content["greeting"] == "Hello"
    finally:
        os.chdir(original_cwd)


def test_main_with_args(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test main entry point with command line args saves to results/ directory."""
    monkeypatch.chdir(tmp_path)

    # Mock sys.exit to capture exit code
    exit_code = None

    def mock_exit(code: int) -> None:
        nonlocal exit_code
        exit_code = code
        raise SystemExit(code)

    monkeypatch.setattr("sys.exit", mock_exit)

    with pytest.raises(SystemExit):
        GreetWorkflow.main(["--name", "CLI Test"])

    assert exit_code == 0
    # Results are saved to results/ in CWD
    results_dir = tmp_path / "results"
    assert results_dir.exists()
    # The greeting file should be in results/
    assert (results_dir / "greeting.txt").exists()


def test_main_missing_required_arg(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test main fails gracefully with missing required arg."""
    exit_code = None

    def mock_exit(code: int) -> None:
        nonlocal exit_code
        exit_code = code
        raise SystemExit(code)

    monkeypatch.setattr("sys.exit", mock_exit)

    with pytest.raises(SystemExit):
        GreetWorkflow.main([])

    assert exit_code != 0


def test_log_file_creation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that log files are created in the current working directory."""
    monkeypatch.chdir(tmp_path)

    # Mock sys.exit to capture exit code
    exit_code = None

    def mock_exit(code: int) -> None:
        nonlocal exit_code
        exit_code = code
        raise SystemExit(code)

    monkeypatch.setattr("sys.exit", mock_exit)

    with pytest.raises(SystemExit):
        GreetWorkflow.main(["--name", "Log Test"])

    assert exit_code == 0

    # Log file should be in CWD as output.log
    log_file = tmp_path / "output.log"
    assert log_file.exists()

    # Log file should contain workflow start message
    log_content = log_file.read_text()
    assert "Starting workflow: GreetWorkflow" in log_content
    assert "Workflow completed successfully" in log_content

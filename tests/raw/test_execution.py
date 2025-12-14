"""Tests for workflow execution module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from raw.engine import Container, DRY_RUN_TIMEOUT_SECONDS, SubprocessBackend
from raw.engine.mocks import MockBackend, MockStorage
from raw.engine.protocols import RunResult


class TestRunResult:
    """Tests for RunResult dataclass."""

    def test_basic_result(self) -> None:
        """Test basic RunResult creation."""
        result = RunResult(
            exit_code=0,
            stdout="output",
            stderr="",
            duration_seconds=1.5,
        )
        assert result.exit_code == 0
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.duration_seconds == 1.5
        assert result.timed_out is False

    def test_timed_out_result(self) -> None:
        """Test RunResult with timeout."""
        result = RunResult(
            exit_code=124,
            stdout="",
            stderr="Timeout exceeded",
            duration_seconds=60.0,
            timed_out=True,
        )
        assert result.exit_code == 124
        assert result.timed_out is True


class TestSubprocessBackend:
    """Tests for SubprocessBackend."""

    def test_run_with_timeout_parameter(self) -> None:
        """Test that timeout parameter is passed to subprocess."""
        backend = SubprocessBackend()

        with patch("raw.engine.backends.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="success",
                stderr="",
            )

            script_path = Path("/tmp/test.py")
            backend.run(script_path, [], timeout=30.0)

            # Verify timeout was passed
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["timeout"] == 30.0

    def test_timeout_handles_text_mode_stdout(self) -> None:
        """Test timeout handling when text=True (stdout is str, not bytes)."""
        import subprocess

        backend = SubprocessBackend()

        # When text=True, TimeoutExpired.stdout is a str
        timeout_error = subprocess.TimeoutExpired(cmd=["test"], timeout=5)
        timeout_error.stdout = "partial output"  # str, not bytes

        with patch("raw.engine.backends.subprocess.run") as mock_run:
            mock_run.side_effect = timeout_error

            script_path = Path("/tmp/test.py")
            result = backend.run(script_path, [], timeout=5.0)

            assert result.timed_out is True
            assert result.exit_code == 124
            assert result.stdout == "partial output"  # Should handle str correctly

    def test_timeout_handles_bytes_stdout(self) -> None:
        """Test timeout handling when stdout is bytes (text=False scenario)."""
        import subprocess

        backend = SubprocessBackend()

        # Simulate bytes stdout (though our code uses text=True)
        timeout_error = subprocess.TimeoutExpired(cmd=["test"], timeout=5)
        timeout_error.stdout = b"partial bytes output"  # bytes

        with patch("raw.engine.backends.subprocess.run") as mock_run:
            mock_run.side_effect = timeout_error

            script_path = Path("/tmp/test.py")
            result = backend.run(script_path, [], timeout=5.0)

            assert result.timed_out is True
            assert result.exit_code == 124
            assert result.stdout == "partial bytes output"  # Should decode bytes

    def test_timeout_handles_none_stdout(self) -> None:
        """Test timeout handling when stdout is None."""
        import subprocess

        backend = SubprocessBackend()

        timeout_error = subprocess.TimeoutExpired(cmd=["test"], timeout=5)
        timeout_error.stdout = None

        with patch("raw.engine.backends.subprocess.run") as mock_run:
            mock_run.side_effect = timeout_error

            script_path = Path("/tmp/test.py")
            result = backend.run(script_path, [], timeout=5.0)

            assert result.timed_out is True
            assert result.exit_code == 124
            assert result.stdout == ""  # Should handle None


# mock_backend and mock_storage fixtures are provided by tests/conftest.py


class TestRunWorkflow:
    """Tests for workflow runner run method."""

    def test_script_not_found(self, tmp_path: Path) -> None:
        """Test run with non-existent script."""
        runner = Container.workflow_runner()
        result = runner.run(tmp_path, "nonexistent.py")
        assert result.exit_code == 1
        assert "Script not found" in result.stderr

    def test_timeout_parameter_passed(self, tmp_path: Path, mock_backend: MockBackend) -> None:
        """Test that timeout is passed to backend."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        runner = Container.workflow_runner()
        runner.run(tmp_path, "test.py", timeout=45.0)

        assert len(mock_backend.calls) == 1
        assert mock_backend.calls[0]["timeout"] == 45.0


class TestRunDry:
    """Tests for workflow runner run_dry method."""

    def test_uses_default_timeout(self, tmp_path: Path, mock_backend: MockBackend) -> None:
        """Test that run_dry uses DRY_RUN_TIMEOUT_SECONDS by default."""
        script = tmp_path / "dry_run.py"
        script.write_text("print('dry run')")
        mocks_dir = tmp_path / "mocks"
        mocks_dir.mkdir()

        runner = Container.workflow_runner()
        runner.run_dry(tmp_path)

        assert len(mock_backend.calls) == 1
        assert mock_backend.calls[0]["timeout"] == DRY_RUN_TIMEOUT_SECONDS

    def test_custom_timeout_overrides_default(self, tmp_path: Path, mock_backend: MockBackend) -> None:
        """Test that custom timeout overrides default."""
        script = tmp_path / "dry_run.py"
        script.write_text("print('dry run')")
        mocks_dir = tmp_path / "mocks"
        mocks_dir.mkdir()

        runner = Container.workflow_runner()
        runner.run_dry(tmp_path, timeout=120.0)

        assert len(mock_backend.calls) == 1
        assert mock_backend.calls[0]["timeout"] == 120.0

    def test_warns_when_mocks_missing(self, tmp_path: Path, mock_backend: MockBackend) -> None:
        """Test that run_dry warns when mocks/ directory is missing."""
        script = tmp_path / "dry_run.py"
        script.write_text("print('dry run')")
        # Note: NOT creating mocks/ directory

        runner = Container.workflow_runner()
        result = runner.run_dry(tmp_path)

        assert "Warning: mocks/ directory not found" in result.stderr

    def test_no_warning_when_mocks_exists(self, tmp_path: Path, mock_backend: MockBackend) -> None:
        """Test no warning when mocks/ directory exists."""
        script = tmp_path / "dry_run.py"
        script.write_text("print('dry run')")
        mocks_dir = tmp_path / "mocks"
        mocks_dir.mkdir()

        runner = Container.workflow_runner()
        result = runner.run_dry(tmp_path)

        assert "Warning: mocks/ directory not found" not in result.stderr

    def test_no_warning_on_failure(self, tmp_path: Path) -> None:
        """Test that warning is not prepended on failure."""
        script = tmp_path / "dry_run.py"
        script.write_text("raise Exception('fail')")
        # Note: NOT creating mocks/ directory

        # Use a failing mock backend
        fail_result = RunResult(
            exit_code=1,
            stdout="",
            stderr="Exception: fail",
            duration_seconds=0.1,
        )
        fail_backend = MockBackend(fail_result)
        Container.set_backend(fail_backend)

        try:
            runner = Container.workflow_runner()
            result = runner.run_dry(tmp_path)

            # Warning should not be prepended to error output
            assert "Warning: mocks/ directory not found" not in result.stderr
            assert result.stderr == "Exception: fail"
        finally:
            Container.reset()


class TestContainer:
    """Tests for Container (composition root)."""

    def test_container_returns_default_backend(self) -> None:
        """Test that Container returns SubprocessBackend by default."""
        Container.reset()
        backend = Container.backend()
        assert isinstance(backend, SubprocessBackend)

    def test_container_returns_same_instance(self) -> None:
        """Test that Container returns the same instance on repeated calls."""
        Container.reset()
        backend1 = Container.backend()
        backend2 = Container.backend()
        assert backend1 is backend2

    def test_container_override_backend(self) -> None:
        """Test that Container allows backend override."""
        result = RunResult(exit_code=0, stdout="", stderr="", duration_seconds=0.0)
        mock = MockBackend(result)

        Container.set_backend(mock)
        assert Container.backend() is mock

        Container.reset()
        assert isinstance(Container.backend(), SubprocessBackend)

    def test_container_override_storage(self) -> None:
        """Test that Container allows storage override."""
        mock = MockStorage()

        Container.set_storage(mock)
        assert Container.storage() is mock

        Container.reset()

    def test_container_workflow_runner_uses_overrides(self, tmp_path: Path) -> None:
        """Test that workflow_runner() uses overridden dependencies."""
        result = RunResult(exit_code=0, stdout="test", stderr="", duration_seconds=0.1)
        mock_be = MockBackend(result)
        mock_st = MockStorage()

        Container.set_backend(mock_be)
        Container.set_storage(mock_st)

        script = tmp_path / "run.py"
        script.write_text("print('test')")

        runner = Container.workflow_runner()
        runner.run(tmp_path, isolate_run=True)

        # Verify mock backend was called
        assert len(mock_be.calls) == 1

        # Verify mock storage was used
        assert len(mock_st.created_directories) == 1
        assert len(mock_st.saved_manifests) == 1

        Container.reset()


class TestWorkflowRunner:
    """Tests for WorkflowRunner class with dependency injection."""

    def test_runner_with_injected_backend(self, tmp_path: Path) -> None:
        """Test that WorkflowRunner works with injected backend."""
        from raw.engine.backends import LocalRunStorage
        from raw.engine.runner import WorkflowRunner

        script = tmp_path / "run.py"
        script.write_text("print('hello')")

        result = RunResult(exit_code=0, stdout="hello", stderr="", duration_seconds=0.1)
        mock_backend = MockBackend(result)
        storage = LocalRunStorage()

        runner = WorkflowRunner(backend=mock_backend, storage=storage)
        runner.run(tmp_path, isolate_run=False)

        assert len(mock_backend.calls) == 1
        assert mock_backend.calls[0]["script_path"] == script

    def test_runner_creates_run_directory(self, tmp_path: Path) -> None:
        """Test that runner creates run directory when isolate_run=True."""
        from raw.engine.backends import LocalRunStorage
        from raw.engine.runner import WorkflowRunner

        script = tmp_path / "run.py"
        script.write_text("print('hello')")

        result = RunResult(exit_code=0, stdout="hello", stderr="", duration_seconds=0.1)
        mock_backend = MockBackend(result)
        storage = LocalRunStorage()

        runner = WorkflowRunner(backend=mock_backend, storage=storage)
        runner.run(tmp_path, isolate_run=True)

        # Verify run directory was created
        runs_dir = tmp_path / "runs"
        assert runs_dir.exists()
        run_dirs = list(runs_dir.iterdir())
        assert len(run_dirs) == 1
        assert (run_dirs[0] / "manifest.json").exists()
        assert (run_dirs[0] / "output.log").exists()

    def test_runner_with_fully_mocked_dependencies(self, tmp_path: Path) -> None:
        """Test runner with both backend and storage mocked.

        Demonstrates that WorkflowRunner can be tested without any
        real filesystem or subprocess side effects.
        """
        from raw.engine.runner import WorkflowRunner

        script = tmp_path / "run.py"
        script.write_text("print('isolated')")

        result = RunResult(exit_code=0, stdout="isolated", stderr="", duration_seconds=0.05)
        mock_be = MockBackend(result)
        mock_st = MockStorage()

        runner = WorkflowRunner(backend=mock_be, storage=mock_st)
        run_result = runner.run(tmp_path, isolate_run=True)

        # Backend was called
        assert len(mock_be.calls) == 1
        assert mock_be.calls[0]["script_path"] == script

        # Storage methods were called (no actual filesystem)
        assert len(mock_st.created_directories) == 1
        assert len(mock_st.saved_manifests) == 1
        assert mock_st.saved_manifests[0]["exit_code"] == 0
        assert len(mock_st.saved_logs) == 1

        # Result is correct
        assert run_result.exit_code == 0
        assert run_result.stdout == "isolated"

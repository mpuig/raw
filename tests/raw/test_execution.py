"""Tests for workflow execution module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from raw.engine.execution import (
    DRY_RUN_TIMEOUT_SECONDS,
    RunResult,
    SubprocessBackend,
    run_dry,
    run_workflow,
)


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

        with patch("raw.engine.execution.subprocess.run") as mock_run:
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

        with patch("raw.engine.execution.subprocess.run") as mock_run:
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

        with patch("raw.engine.execution.subprocess.run") as mock_run:
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

        with patch("raw.engine.execution.subprocess.run") as mock_run:
            mock_run.side_effect = timeout_error

            script_path = Path("/tmp/test.py")
            result = backend.run(script_path, [], timeout=5.0)

            assert result.timed_out is True
            assert result.exit_code == 124
            assert result.stdout == ""  # Should handle None


class TestRunWorkflow:
    """Tests for run_workflow function."""

    def test_script_not_found(self, tmp_path: Path) -> None:
        """Test run_workflow with non-existent script."""
        result = run_workflow(tmp_path, "nonexistent.py")
        assert result.exit_code == 1
        assert "Script not found" in result.stderr

    def test_timeout_parameter_passed(self, tmp_path: Path) -> None:
        """Test that timeout is passed to backend."""
        script = tmp_path / "test.py"
        script.write_text("print('hello')")

        with patch("raw.engine.execution.default_backend") as mock_backend:
            mock_backend.run.return_value = RunResult(
                exit_code=0,
                stdout="hello",
                stderr="",
                duration_seconds=0.1,
            )

            run_workflow(tmp_path, "test.py", timeout=45.0)

            mock_backend.run.assert_called_once()
            call_kwargs = mock_backend.run.call_args[1]
            assert call_kwargs["timeout"] == 45.0


class TestRunDry:
    """Tests for run_dry function."""

    def test_uses_default_timeout(self, tmp_path: Path) -> None:
        """Test that run_dry uses DRY_RUN_TIMEOUT_SECONDS by default."""
        script = tmp_path / "dry_run.py"
        script.write_text("print('dry run')")
        mocks_dir = tmp_path / "mocks"
        mocks_dir.mkdir()

        with patch("raw.engine.execution.default_backend") as mock_backend:
            mock_backend.run.return_value = RunResult(
                exit_code=0,
                stdout="dry run",
                stderr="",
                duration_seconds=0.1,
            )

            run_dry(tmp_path)

            mock_backend.run.assert_called_once()
            call_kwargs = mock_backend.run.call_args[1]
            assert call_kwargs["timeout"] == DRY_RUN_TIMEOUT_SECONDS

    def test_custom_timeout_overrides_default(self, tmp_path: Path) -> None:
        """Test that custom timeout overrides default."""
        script = tmp_path / "dry_run.py"
        script.write_text("print('dry run')")
        mocks_dir = tmp_path / "mocks"
        mocks_dir.mkdir()

        with patch("raw.engine.execution.default_backend") as mock_backend:
            mock_backend.run.return_value = RunResult(
                exit_code=0,
                stdout="dry run",
                stderr="",
                duration_seconds=0.1,
            )

            run_dry(tmp_path, timeout=120.0)

            mock_backend.run.assert_called_once()
            call_kwargs = mock_backend.run.call_args[1]
            assert call_kwargs["timeout"] == 120.0

    def test_warns_when_mocks_missing(self, tmp_path: Path) -> None:
        """Test that run_dry warns when mocks/ directory is missing."""
        script = tmp_path / "dry_run.py"
        script.write_text("print('dry run')")
        # Note: NOT creating mocks/ directory

        with patch("raw.engine.execution.default_backend") as mock_backend:
            mock_backend.run.return_value = RunResult(
                exit_code=0,
                stdout="dry run",
                stderr="",
                duration_seconds=0.1,
            )

            result = run_dry(tmp_path)

            assert "Warning: mocks/ directory not found" in result.stderr

    def test_no_warning_when_mocks_exists(self, tmp_path: Path) -> None:
        """Test no warning when mocks/ directory exists."""
        script = tmp_path / "dry_run.py"
        script.write_text("print('dry run')")
        mocks_dir = tmp_path / "mocks"
        mocks_dir.mkdir()

        with patch("raw.engine.execution.default_backend") as mock_backend:
            mock_backend.run.return_value = RunResult(
                exit_code=0,
                stdout="dry run",
                stderr="",
                duration_seconds=0.1,
            )

            result = run_dry(tmp_path)

            assert "Warning: mocks/ directory not found" not in result.stderr

    def test_no_warning_on_failure(self, tmp_path: Path) -> None:
        """Test that warning is not prepended on failure."""
        script = tmp_path / "dry_run.py"
        script.write_text("raise Exception('fail')")
        # Note: NOT creating mocks/ directory

        with patch("raw.engine.execution.default_backend") as mock_backend:
            mock_backend.run.return_value = RunResult(
                exit_code=1,
                stdout="",
                stderr="Exception: fail",
                duration_seconds=0.1,
            )

            result = run_dry(tmp_path)

            # Warning should not be prepended to error output
            assert "Warning: mocks/ directory not found" not in result.stderr
            assert result.stderr == "Exception: fail"

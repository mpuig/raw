"""Mock implementations for testing the engine layer.

Provides in-memory implementations of engine protocols that can be
used in tests without filesystem or subprocess side effects.
"""

from pathlib import Path
from typing import Any

from raw.engine.protocols import ExecutionBackend, RunResult, RunStorage


class MockBackend:
    """Mock execution backend for testing.

    Records all calls without actually executing anything.
    Returns a configurable result for each call.
    """

    def __init__(self, result: RunResult | None = None) -> None:
        """Initialize with a default result to return.

        Args:
            result: RunResult to return from run(). If None, uses a default success result.
        """
        self.result = result or RunResult(
            exit_code=0,
            stdout="",
            stderr="",
            duration_seconds=0.0,
        )
        self.calls: list[dict[str, Any]] = []

    def run(
        self,
        script_path: Path,
        args: list[str],
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> RunResult:
        """Record the call and return the configured result."""
        self.calls.append({
            "script_path": script_path,
            "args": args,
            "cwd": cwd,
            "timeout": timeout,
        })
        return self.result

    def set_result(self, result: RunResult) -> None:
        """Change the result for subsequent calls."""
        self.result = result


class MockStorage:
    """Mock storage backend for testing.

    Records all operations without filesystem side effects.
    """

    def __init__(self) -> None:
        self.created_directories: list[Path] = []
        self.saved_manifests: list[dict[str, Any]] = []
        self.saved_logs: list[dict[str, Any]] = []

    def create_run_directory(self, workflow_dir: Path) -> Path:
        """Record directory creation and return a mock path."""
        run_dir = workflow_dir / "runs" / "mock-run"
        self.created_directories.append(run_dir)
        return run_dir

    def save_manifest(
        self,
        run_dir: Path,
        workflow_id: str,
        exit_code: int,
        duration_seconds: float,
        args: list[str],
    ) -> None:
        """Record manifest save."""
        self.saved_manifests.append({
            "run_dir": run_dir,
            "workflow_id": workflow_id,
            "exit_code": exit_code,
            "duration_seconds": duration_seconds,
            "args": args,
        })

    def save_output_log(self, run_dir: Path, stdout: str, stderr: str) -> None:
        """Record log save."""
        self.saved_logs.append({
            "run_dir": run_dir,
            "stdout": stdout,
            "stderr": stderr,
        })

    def reset(self) -> None:
        """Clear all recorded operations."""
        self.created_directories.clear()
        self.saved_manifests.clear()
        self.saved_logs.clear()


# Verify protocol compliance at import time
assert isinstance(MockBackend(), ExecutionBackend)
assert isinstance(MockStorage(), RunStorage)

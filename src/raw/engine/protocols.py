"""Protocols for workflow execution engine.

Defines contracts for execution backends and run storage,
enabling dependency injection and testability.
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class RunResult(BaseModel):
    """Result of a workflow execution.

    Using Pydantic enables:
    - Automatic JSON serialization for manifest storage
    - Type validation at construction time
    - Consistent serialization format

    Frozen because results are immutable facts about past executions.
    """

    model_config = ConfigDict(frozen=True)

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False


@runtime_checkable
class ExecutionBackend(Protocol):
    """Protocol for script execution backends.

    Implementations handle the actual subprocess/container/remote execution.
    Examples: SubprocessBackend, DockerBackend, KubernetesBackend
    """

    def run(
        self,
        script_path: Path,
        args: list[str],
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> RunResult:
        """Execute a script and return the result."""
        ...


@runtime_checkable
class RunStorage(Protocol):
    """Protocol for run directory and manifest management.

    Separates storage concerns from execution logic,
    enabling different storage strategies (local, S3, etc.)
    """

    def create_run_directory(self, workflow_dir: Path) -> Path:
        """Create a timestamped run directory for workflow execution.

        Returns:
            Path to the created run directory (e.g., workflow_dir/runs/20251207-215930/)
        """
        ...

    def save_manifest(
        self,
        run_dir: Path,
        workflow_id: str,
        exit_code: int,
        duration_seconds: float,
        args: list[str],
    ) -> None:
        """Save execution manifest to run directory."""
        ...

    def save_output_log(self, run_dir: Path, stdout: str, stderr: str) -> None:
        """Save execution output to log file."""
        ...

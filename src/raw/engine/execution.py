"""Workflow execution via uv run.

This module provides the public API for workflow execution.
It uses WorkflowRunner internally with default backends.

For custom execution strategies, use WorkflowRunner directly
with injected ExecutionBackend and RunStorage implementations,
or use Container for DI configuration.
"""

from pathlib import Path

from raw.engine.backends import (
    LocalRunStorage,
    SubprocessBackend,
    parse_pep723_dependencies,
)
from raw.engine.container import Container
from raw.engine.protocols import ExecutionBackend, RunResult, RunStorage
from raw.engine.runner import DRY_RUN_TIMEOUT_SECONDS, WorkflowRunner


# Backward-compatible accessors that delegate to Container


def get_default_backend() -> ExecutionBackend:
    """Get the default execution backend."""
    return Container.backend()


def set_default_backend(backend: ExecutionBackend | None) -> None:
    """Set the default execution backend (useful for testing)."""
    Container.set_backend(backend)


def get_default_storage() -> RunStorage:
    """Get the default run storage."""
    return Container.storage()


def set_default_storage(storage: RunStorage | None) -> None:
    """Set the default run storage (useful for testing)."""
    Container.set_storage(storage)


def get_default_runner() -> WorkflowRunner:
    """Get a WorkflowRunner with default dependencies."""
    return Container.workflow_runner()


# Backward-compatible module-level functions


def create_run_directory(workflow_dir: Path) -> Path:
    """Create a timestamped run directory for workflow execution.

    Returns path like: workflow_dir/runs/20251207-215930/

    Note: Prefer using WorkflowRunner for new code.
    """
    return get_default_storage().create_run_directory(workflow_dir)


def save_run_manifest(
    run_dir: Path,
    workflow_id: str,
    exit_code: int,
    duration_seconds: float,
    args: list[str],
) -> None:
    """Save execution manifest to run directory.

    Note: Prefer using WorkflowRunner for new code.
    """
    get_default_storage().save_manifest(
        run_dir=run_dir,
        workflow_id=workflow_id,
        exit_code=exit_code,
        duration_seconds=duration_seconds,
        args=args,
    )


def verify_tool_hashes(workflow_dir: Path) -> list[str]:
    """Verify tool hashes for a published workflow.

    Returns list of warnings for tools with mismatched hashes.
    """
    # Delegate to runner's internal method via a temporary instance
    runner = get_default_runner()
    return runner._verify_tool_hashes(workflow_dir)


def run_workflow(
    workflow_dir: Path,
    script_name: str = "run.py",
    args: list[str] | None = None,
    backend: ExecutionBackend | None = None,
    timeout: float | None = None,
    isolate_run: bool = True,
) -> RunResult:
    """Run a workflow script.

    Args:
        workflow_dir: Path to workflow directory
        script_name: Name of script to run (run.py, dry_run.py)
        args: Arguments to pass to the script
        backend: Execution backend to use (deprecated, use WorkflowRunner)
        timeout: Maximum execution time in seconds (None for no limit)
        isolate_run: Create timestamped run directory for outputs

    Returns:
        RunResult with execution details

    Note: For new code, prefer using WorkflowRunner directly with
    dependency injection for better testability.
    """
    if backend is not None:
        # Custom backend provided - create a runner with it
        runner = WorkflowRunner(
            backend=backend,
            storage=get_default_storage(),
        )
    else:
        runner = get_default_runner()

    return runner.run(
        workflow_dir=workflow_dir,
        script_name=script_name,
        args=args,
        timeout=timeout,
        isolate_run=isolate_run,
    )


def run_dry(
    workflow_dir: Path,
    args: list[str] | None = None,
    backend: ExecutionBackend | None = None,
    timeout: float | None = None,
) -> RunResult:
    """Run a workflow in dry-run mode with mock data.

    Dry runs execute dry_run.py with a default timeout and validate
    that the mocks/ directory exists. Dry runs do not create isolated
    run directories since they are for testing purposes.

    Args:
        workflow_dir: Path to workflow directory
        args: Arguments to pass to the script
        backend: Execution backend to use (deprecated, use WorkflowRunner)
        timeout: Maximum execution time (defaults to DRY_RUN_TIMEOUT_SECONDS)

    Returns:
        RunResult with execution details

    Note: For new code, prefer using WorkflowRunner directly.
    """
    if backend is not None:
        runner = WorkflowRunner(
            backend=backend,
            storage=get_default_storage(),
        )
    else:
        runner = get_default_runner()

    return runner.run_dry(
        workflow_dir=workflow_dir,
        args=args,
        timeout=timeout,
    )


# Re-export for backward compatibility
__all__ = [
    # DI Container
    "Container",
    # Protocols and types
    "ExecutionBackend",
    "RunStorage",
    "RunResult",
    # Classes
    "WorkflowRunner",
    "SubprocessBackend",
    "LocalRunStorage",
    # Functions
    "run_workflow",
    "run_dry",
    "create_run_directory",
    "save_run_manifest",
    "verify_tool_hashes",
    "parse_pep723_dependencies",
    # Default management (delegates to Container)
    "get_default_backend",
    "set_default_backend",
    "get_default_storage",
    "set_default_storage",
    "get_default_runner",
    # Constants
    "DRY_RUN_TIMEOUT_SECONDS",
]

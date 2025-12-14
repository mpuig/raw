"""Execution engine for workflows.

This module provides workflow execution capabilities with clean architecture:

- WorkflowRunner: Main class for executing workflows with DI
- ExecutionBackend: Protocol for script execution (subprocess, docker, etc.)
- RunStorage: Protocol for run directory management (local, S3, etc.)

For simple use cases, use the module-level functions (run_workflow, run_dry).
For custom execution strategies, use WorkflowRunner with injected dependencies.
"""

from raw.engine.backends import LocalRunStorage, SubprocessBackend, parse_pep723_dependencies
from raw.engine.execution import (
    DRY_RUN_TIMEOUT_SECONDS,
    create_run_directory,
    get_default_backend,
    get_default_runner,
    get_default_storage,
    run_dry,
    run_workflow,
    save_run_manifest,
    set_default_backend,
    set_default_storage,
    verify_tool_hashes,
)
from raw.engine.protocols import ExecutionBackend, RunResult, RunStorage
from raw.engine.runner import WorkflowRunner

__all__ = [
    # Core classes
    "WorkflowRunner",
    # Protocols
    "ExecutionBackend",
    "RunStorage",
    "RunResult",
    # Implementations
    "SubprocessBackend",
    "LocalRunStorage",
    # Module-level functions (backward compatible)
    "run_workflow",
    "run_dry",
    "create_run_directory",
    "save_run_manifest",
    "verify_tool_hashes",
    "parse_pep723_dependencies",
    # Default management
    "get_default_backend",
    "set_default_backend",
    "get_default_storage",
    "set_default_storage",
    "get_default_runner",
    # Constants
    "DRY_RUN_TIMEOUT_SECONDS",
]

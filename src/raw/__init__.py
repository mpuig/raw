"""RAW - Run Agentic Workflows.

Agent-first workflow orchestration for Claude Code.
"""

from raw.exceptions import (
    ConfigurationError,
    ExecutionError,
    ExecutionFailedError,
    ExecutionTimeoutError,
    InvalidArgumentError,
    ProjectNotInitializedError,
    RawError,
    ScriptNotFoundError,
    ToolAlreadyExistsError,
    ToolError,
    ToolHashMismatchError,
    ToolNotFoundError,
    ValidationError,
    WorkflowAlreadyExistsError,
    WorkflowConfigError,
    WorkflowError,
    WorkflowNotFoundError,
)

__version__ = "0.1.0"

__all__ = [
    # Base exception
    "RawError",
    # Configuration
    "ConfigurationError",
    "ProjectNotInitializedError",
    # Workflow
    "WorkflowError",
    "WorkflowNotFoundError",
    "WorkflowConfigError",
    "WorkflowAlreadyExistsError",
    # Tool
    "ToolError",
    "ToolNotFoundError",
    "ToolAlreadyExistsError",
    "ToolHashMismatchError",
    # Execution
    "ExecutionError",
    "ExecutionFailedError",
    "ExecutionTimeoutError",
    "ScriptNotFoundError",
    # Validation
    "ValidationError",
    "InvalidArgumentError",
]

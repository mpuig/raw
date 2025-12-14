"""RAW exception hierarchy.

Provides a unified exception hierarchy for the RAW CLI and engine.
This enables:
- User-friendly error messages in the CLI
- Programmatic error handling in library usage
- Clear distinction between user errors and internal bugs

Usage:
    from raw.exceptions import WorkflowNotFoundError, ExecutionFailedError

    try:
        run_workflow(workflow_dir)
    except WorkflowNotFoundError as e:
        print(f"Workflow not found: {e.workflow_id}")
    except ExecutionFailedError as e:
        print(f"Execution failed: {e.message}")
    except RawError as e:
        print(f"RAW error: {e}")
"""


class RawError(Exception):
    """Base exception for all RAW errors.

    All RAW-specific exceptions inherit from this class, allowing
    callers to catch all RAW errors with a single except clause.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


# Configuration Errors


class ConfigurationError(RawError):
    """Error in RAW configuration.

    Raised when config.yaml is invalid, missing required fields,
    or contains incompatible settings.
    """

    pass


class ProjectNotInitializedError(ConfigurationError):
    """RAW project not initialized.

    Raised when a command requires an initialized .raw/ directory
    but none exists.
    """

    def __init__(self, path: str | None = None) -> None:
        self.path = path
        message = "RAW project not initialized"
        if path:
            message = f"RAW project not initialized at {path}"
        message += ". Run 'raw init' to initialize."
        super().__init__(message)


# Workflow Errors


class WorkflowError(RawError):
    """Base class for workflow-related errors."""

    pass


class WorkflowNotFoundError(WorkflowError):
    """Workflow not found.

    Raised when a workflow ID doesn't match any existing workflow.
    """

    def __init__(self, workflow_id: str) -> None:
        self.workflow_id = workflow_id
        super().__init__(f"Workflow not found: {workflow_id}")


class WorkflowConfigError(WorkflowError):
    """Invalid workflow configuration.

    Raised when a workflow's config.yaml is invalid or missing
    required fields.
    """

    def __init__(self, workflow_id: str, reason: str) -> None:
        self.workflow_id = workflow_id
        self.reason = reason
        super().__init__(f"Invalid workflow config for '{workflow_id}': {reason}")


class WorkflowAlreadyExistsError(WorkflowError):
    """Workflow already exists.

    Raised when attempting to create a workflow with an ID that
    already exists.
    """

    def __init__(self, workflow_id: str) -> None:
        self.workflow_id = workflow_id
        super().__init__(f"Workflow already exists: {workflow_id}")


# Tool Errors


class ToolError(RawError):
    """Base class for tool-related errors."""

    pass


class ToolNotFoundError(ToolError):
    """Tool not found.

    Raised when a tool name doesn't match any existing tool.
    """

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Tool not found: {tool_name}")


class ToolAlreadyExistsError(ToolError):
    """Tool already exists.

    Raised when attempting to create a tool with a name that
    already exists.
    """

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Tool already exists: {tool_name}")


class ToolHashMismatchError(ToolError):
    """Tool hash doesn't match expected value.

    Raised when a published workflow's tool hash doesn't match
    the current tool state, indicating the tool was modified.
    """

    def __init__(self, tool_name: str, expected_hash: str, actual_hash: str) -> None:
        self.tool_name = tool_name
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        super().__init__(
            f"Tool '{tool_name}' has been modified since workflow was published "
            f"(expected: {expected_hash[:12]}..., actual: {actual_hash[:12]}...)"
        )


# Execution Errors


class ExecutionError(RawError):
    """Base class for execution-related errors."""

    pass


class ExecutionFailedError(ExecutionError):
    """Workflow execution failed.

    Raised when a workflow execution completes with a non-zero exit code.
    """

    def __init__(self, workflow_id: str, exit_code: int, stderr: str = "") -> None:
        self.workflow_id = workflow_id
        self.exit_code = exit_code
        self.stderr = stderr
        message = f"Workflow '{workflow_id}' failed with exit code {exit_code}"
        if stderr:
            message += f": {stderr[:200]}"
        super().__init__(message)


class ExecutionTimeoutError(ExecutionError):
    """Workflow execution timed out.

    Raised when a workflow exceeds its maximum execution time.
    """

    def __init__(self, workflow_id: str, timeout_seconds: float) -> None:
        self.workflow_id = workflow_id
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Workflow '{workflow_id}' timed out after {timeout_seconds}s"
        )


class ScriptNotFoundError(ExecutionError):
    """Script file not found.

    Raised when the expected script (run.py, dry_run.py) doesn't exist.
    """

    def __init__(self, script_path: str) -> None:
        self.script_path = script_path
        super().__init__(f"Script not found: {script_path}")


# Validation Errors


class ValidationError(RawError):
    """Base class for validation errors."""

    pass


class InvalidArgumentError(ValidationError):
    """Invalid command argument.

    Raised when a CLI argument or function parameter is invalid.
    """

    def __init__(self, argument: str, reason: str) -> None:
        self.argument = argument
        self.reason = reason
        super().__init__(f"Invalid argument '{argument}': {reason}")

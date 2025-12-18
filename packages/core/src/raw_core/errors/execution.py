"""Execution-related errors for tools and workflows."""

from raw_core.errors.base import PlatformError


class ToolExecutionError(PlatformError):
    """Tool execution failures."""

    def __init__(self, tool_name: str, message: str, cause: Exception | None = None):
        super().__init__(f"Tool '{tool_name}' failed: {message}", cause)
        self.tool_name = tool_name


class ToolTimeoutError(ToolExecutionError):
    """Tool execution timed out."""

    def __init__(self, tool_name: str, timeout: float):
        super().__init__(tool_name, f"timed out after {timeout}s")
        self.timeout = timeout


class ToolNotFoundError(ToolExecutionError):
    """Tool not found in registry."""

    def __init__(self, tool_name: str):
        super().__init__(tool_name, "not found in registry")


class ConfigurationError(PlatformError):
    """Configuration or setup errors."""

    pass


class MissingAPIKeyError(ConfigurationError):
    """Fail-fast error for missing API keys."""

    def __init__(self, missing_keys: list[str]):
        self.missing_keys = missing_keys
        keys_str = ", ".join(missing_keys)
        super().__init__(f"Missing required API keys: {keys_str}")

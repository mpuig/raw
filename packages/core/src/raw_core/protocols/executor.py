"""Tool executor protocol."""

from typing import Any, Protocol


class ToolExecutor(Protocol):
    """Protocol for tool execution.

    Enables swapping execution strategies (sync, async, sandboxed)
    without changing the engine.
    """

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a tool by name with given arguments.

        Returns result dict on success, {"error": ...} on failure.
        """
        ...

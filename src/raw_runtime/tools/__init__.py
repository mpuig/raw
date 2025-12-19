"""Tool system for RAW workflows.

Tools are reusable actions that workflows can call. They provide a uniform
async iterator interface for both simple functions and complex services.

Usage:
    from raw_runtime.tools import Tool, tool, register_builtin_tools

    # Register pre-defined tools at startup
    register_builtin_tools()

    # Create programmatic tools with decorator
    @tool(description="Get account balance")
    def get_balance(account_id: str) -> float:
        return db.query(account_id)

    # In a workflow
    async for event in self.tool("email").run(to="...", subject="..."):
        ...
"""

from raw_runtime.tools.base import (
    Tool,
    ToolEvent,
    ToolEventType,
    ToolResult,
)
from raw_runtime.tools.decorator import tool
from raw_runtime.tools.registry import (
    ToolRegistry,
    get_tool,
    get_tool_registry,
    register_tool,
    set_tool_registry,
)

__all__ = [
    # Base
    "Tool",
    "ToolEvent",
    "ToolEventType",
    "ToolResult",
    # Decorator
    "tool",
    # Registry
    "ToolRegistry",
    "get_tool_registry",
    "set_tool_registry",
    "register_tool",
    "get_tool",
    # Builtin
    "register_builtin_tools",
]


def register_builtin_tools() -> None:
    """Register all pre-defined tools in the global registry.

    Call this at application startup to make builtin tools available.
    """
    from raw_runtime.tools.builtin import register_all_builtin_tools

    register_all_builtin_tools()

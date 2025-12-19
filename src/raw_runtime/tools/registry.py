"""Tool registry for RAW workflows.

Manages tool registration and lookup. Supports both global (pre-defined)
and workflow-local (programmatic) tools.
"""

from raw_runtime.tools.base import Tool


class ToolRegistry:
    """Registry for tool instances.

    Manages tool lifecycle and provides lookup by name.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def require(self, name: str) -> Tool:
        """Get a tool by name, raising if not found."""
        tool = self.get(name)
        if tool is None:
            available = ", ".join(sorted(self._tools.keys())) or "(none)"
            raise KeyError(f"Tool '{name}' not found. Available: {available}")
        return tool

    def list_all(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def list_by_trigger(self, trigger: str) -> list[Tool]:
        """List tools that can handle a given trigger."""
        return [tool for tool in self._tools.values() if trigger in tool.triggers]


# Global registry for pre-defined tools
_global_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def set_tool_registry(registry: ToolRegistry) -> None:
    """Set the global tool registry."""
    global _global_registry
    _global_registry = registry


def register_tool(tool: Tool) -> None:
    """Register a tool in the global registry."""
    get_tool_registry().register(tool)


def get_tool(name: str) -> Tool:
    """Get a tool from the global registry."""
    return get_tool_registry().require(name)

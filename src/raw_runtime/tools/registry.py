"""Tool registry for RAW workflows.

Manages tool registration and lookup. Supports both global (pre-defined)
and workflow-local (programmatic) tools.
"""

import logging
from pathlib import Path

from raw_runtime.models import ToolMetadata
from raw_runtime.tools.base import Tool

logger = logging.getLogger(__name__)


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

    def list_tools(self) -> list[str]:
        """List all registered tool names for introspection."""
        return sorted(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def get_tool_metadata(self, name: str) -> ToolMetadata:
        """Get comprehensive metadata about a tool.

        Args:
            name: Tool name to introspect.

        Returns:
            ToolMetadata with tool capabilities, parameters, and documentation.

        Raises:
            KeyError: If tool is not found.
        """
        tool = self.require(name)
        return tool.__class__.metadata()

    def discover_and_register(self, tools_dir: Path) -> int:
        """Discover tools in directory and register them.

        Scans the tools directory for valid tool packages and registers
        any discovered tools automatically.

        Args:
            tools_dir: Path to tools directory to scan

        Returns:
            Number of tools registered

        Example:
            registry = ToolRegistry()
            count = registry.discover_and_register(Path("tools"))
            print(f"Registered {count} tools")
        """
        from raw_runtime.tools.discovery import discover_tools

        discovered = discover_tools(tools_dir)
        count = 0

        for tool_name, tool_cls in discovered.items():
            try:
                # Instantiate if it's a class
                if isinstance(tool_cls, type):
                    tool_instance = tool_cls()
                else:
                    # Already an instance (from @tool decorator)
                    tool_instance = tool_cls

                self.register(tool_instance)
                count += 1
                logger.info(f"Registered tool: {tool_name}")

            except Exception as e:
                logger.warning(f"Failed to register tool {tool_name}: {e}")
                continue

        return count


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

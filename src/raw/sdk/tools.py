"""SDK functions for programmatic tool management."""

import shutil
from pathlib import Path
from typing import Literal

from raw.core.schemas import ToolConfig
from raw.discovery.registry import LocalToolRegistry, ToolInfo
from raw.scaffold.init import (
    create_tool as _create_tool,
)
from raw.scaffold.init import (
    find_tool as _find_tool,
)
from raw.scaffold.init import (
    get_tools_dir,
    load_tool_config,
    sanitize_tool_name,
    save_tool_config,
)
from raw.sdk.models import Tool


class ToolNotFoundError(Exception):
    """Raised when a tool cannot be found."""


def _tool_config_to_model(config: ToolConfig, path: Path) -> Tool:
    """Convert ToolConfig to SDK Tool model."""
    operations = [inp.name for inp in config.inputs]
    return Tool(
        name=config.name,
        description=config.description,
        version=config.version,
        operations=operations,
        path=path,
    )


def _load_tool_model(tool_path: Path) -> Tool:
    """Load tool config and convert to SDK model."""
    config = load_tool_config(tool_path)
    if not config:
        raise ValueError(f"Could not load tool config from {tool_path}")
    return _tool_config_to_model(config, tool_path)


def create_tool(
    name: str,
    description: str,
    tool_type: Literal["function", "class"] = "function",  # noqa: ARG001
    tools_dir: Path | None = None,
) -> Tool:
    """Create a new tool package.

    Args:
        name: Tool name (e.g., "stock_fetcher")
        description: Tool description for search
        tool_type: "function" for @tool decorator, "class" for Tool subclass
        tools_dir: Directory to create tool in (default: ./tools/)

    Returns:
        Tool object with metadata and path
    """
    if tools_dir is not None:
        import raw.scaffold.init

        original_get_tools_dir = raw.scaffold.init.get_tools_dir
        raw.scaffold.init.get_tools_dir = lambda _=None: tools_dir

        try:
            tool_dir, config = _create_tool(name, description)
        finally:
            raw.scaffold.init.get_tools_dir = original_get_tools_dir
    else:
        tool_dir, config = _create_tool(name, description)

    return _tool_config_to_model(config, tool_dir)


def list_tools(tools_dir: Path | None = None) -> list[Tool]:
    """List all tool packages.

    Args:
        tools_dir: Directory to search for tools (default: ./tools/)

    Returns:
        List of Tool objects
    """
    if tools_dir is None:
        tools_dir = get_tools_dir()

    registry = LocalToolRegistry(tools_dir)
    tool_infos: list[ToolInfo] = registry.list_tools()

    tools: list[Tool] = []
    for info in tool_infos:
        if info.path:
            try:
                tool = _load_tool_model(info.path)
                tools.append(tool)
            except ValueError:
                # Skip tools with invalid configs
                continue

    return tools


def get_tool(name: str, tools_dir: Path | None = None) -> Tool | None:
    """Get tool metadata by name.

    Args:
        name: Tool name
        tools_dir: Directory to search for tools (default: ./tools/)

    Returns:
        Tool object or None if not found
    """
    if tools_dir is None:
        tool_path = _find_tool(name)
    else:
        tool_path = tools_dir / sanitize_tool_name(name)
        if not tool_path.exists():
            tool_path = None

    if not tool_path:
        return None

    try:
        return _load_tool_model(tool_path)
    except ValueError:
        return None


def update_tool(
    name: str,
    description: str | None = None,
    version: str | None = None,
    tools_dir: Path | None = None,
) -> Tool:
    """Update tool metadata in config.yaml.

    Args:
        name: Tool name
        description: New description (optional)
        version: New version (optional)
        tools_dir: Directory to search for tools (default: ./tools/)

    Returns:
        Updated Tool object

    Raises:
        ToolNotFoundError: If tool doesn't exist
    """
    tool = get_tool(name, tools_dir)
    if not tool:
        raise ToolNotFoundError(f"Tool not found: {name}")

    config = load_tool_config(tool.path)
    if not config:
        raise ToolNotFoundError(f"Tool config not found: {name}")

    # Update fields
    if description is not None:
        config.description = description
    if version is not None:
        config.version = version

    save_tool_config(tool.path, config)

    return _tool_config_to_model(config, tool.path)


def delete_tool(name: str, tools_dir: Path | None = None) -> None:
    """Delete a tool package.

    Args:
        name: Tool name
        tools_dir: Directory to search for tools (default: ./tools/)

    Raises:
        ToolNotFoundError: If tool doesn't exist
    """
    tool = get_tool(name, tools_dir)
    if not tool:
        raise ToolNotFoundError(f"Tool not found: {name}")

    if not tool.path.exists():
        raise ToolNotFoundError(f"Tool directory not found: {name}")

    shutil.rmtree(tool.path)

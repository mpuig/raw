"""Tests for tool discovery."""

import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, ClassVar

import pytest

from raw_runtime.tools import Tool, ToolEvent, ToolRegistry
from raw_runtime.tools.discovery import (
    discover_tools,
    load_tool_metadata,
    scan_tool_module,
)


class SampleTool(Tool):
    """Sample tool for testing."""

    name: ClassVar[str] = "sample"
    description: ClassVar[str] = "Sample tool for testing"

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        """Run the tool."""
        yield self._emit_started(**config)
        yield self._emit_completed(result="ok")


def test_discover_tools_empty_directory(tmp_path: Path) -> None:
    """Test discovery in empty tools directory."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    discovered = discover_tools(tools_dir)
    assert discovered == {}


def test_discover_tools_nonexistent_directory(tmp_path: Path) -> None:
    """Test discovery handles nonexistent directory gracefully."""
    tools_dir = tmp_path / "nonexistent"

    discovered = discover_tools(tools_dir)
    assert discovered == {}


def test_discover_tools_ignores_hidden_dirs(tmp_path: Path) -> None:
    """Test discovery ignores hidden directories."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create hidden directory
    hidden_dir = tools_dir / ".hidden"
    hidden_dir.mkdir()
    (hidden_dir / "tool.py").write_text("# This should be ignored")

    # Create __pycache__
    pycache_dir = tools_dir / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "tool.py").write_text("# This should be ignored")

    discovered = discover_tools(tools_dir)
    assert discovered == {}


def test_discover_tools_with_tool_class(tmp_path: Path) -> None:
    """Test discovery of tool class."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create tool package with tool.py
    package_dir = tools_dir / "mytool"
    package_dir.mkdir()

    tool_code = """
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class MyTool(Tool):
    name: ClassVar[str] = "mytool"
    description: ClassVar[str] = "My test tool"

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_started(**config)
        yield self._emit_completed(result="done")
"""
    (package_dir / "tool.py").write_text(tool_code)

    discovered = discover_tools(tools_dir)
    assert "mytool" in discovered
    assert discovered["mytool"].__name__ == "MyTool"


def test_discover_tools_with_decorated_function(tmp_path: Path) -> None:
    """Test discovery of @tool decorated function."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create tool package with decorated function
    package_dir = tools_dir / "helper"
    package_dir.mkdir()

    tool_code = """
from raw_runtime.tools import tool

@tool(description="Helper function")
def helper_func(value: str) -> str:
    return f"processed: {value}"
"""
    (package_dir / "tool.py").write_text(tool_code)

    discovered = discover_tools(tools_dir)
    assert "helper" in discovered


def test_discover_tools_with_config_yaml(tmp_path: Path) -> None:
    """Test discovery loads config.yaml metadata."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    package_dir = tools_dir / "configured"
    package_dir.mkdir()

    tool_code = """
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class ConfiguredTool(Tool):
    name: ClassVar[str] = "configured"
    description: ClassVar[str] = "Configured tool"

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_completed(result="ok")
"""
    (package_dir / "tool.py").write_text(tool_code)

    config_yaml = """
name: custom_name
version: 1.0.0
description: Custom description
"""
    (package_dir / "config.yaml").write_text(config_yaml)

    discovered = discover_tools(tools_dir)
    # Should use name from config.yaml
    assert "custom_name" in discovered


def test_discover_tools_with_init_py(tmp_path: Path) -> None:
    """Test discovery finds tools in __init__.py."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    package_dir = tools_dir / "initool"
    package_dir.mkdir()

    init_code = """
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class InitTool(Tool):
    name: ClassVar[str] = "initool"
    description: ClassVar[str] = "Tool in init"

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_completed(result="ok")
"""
    (package_dir / "__init__.py").write_text(init_code)

    discovered = discover_tools(tools_dir)
    assert "initool" in discovered


def test_discover_tools_prefers_tool_py_over_init(tmp_path: Path) -> None:
    """Test discovery prefers tool.py over __init__.py."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    package_dir = tools_dir / "prefer"
    package_dir.mkdir()

    tool_code = """
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class ToolPyVersion(Tool):
    name: ClassVar[str] = "prefer"
    description: ClassVar[str] = "From tool.py"

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_completed(result="tool.py")
"""
    (package_dir / "tool.py").write_text(tool_code)

    init_code = """
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class InitPyVersion(Tool):
    name: ClassVar[str] = "prefer"
    description: ClassVar[str] = "From init"

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_completed(result="init.py")
"""
    (package_dir / "__init__.py").write_text(init_code)

    discovered = discover_tools(tools_dir)
    assert "prefer" in discovered
    # Should use tool.py version
    assert discovered["prefer"].__name__ == "ToolPyVersion"


def test_discover_tools_handles_import_errors(tmp_path: Path) -> None:
    """Test discovery gracefully handles import errors."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create tool with invalid syntax
    package_dir = tools_dir / "broken"
    package_dir.mkdir()
    (package_dir / "tool.py").write_text("import nonexistent_module\nthis is invalid syntax")

    # Create valid tool
    valid_dir = tools_dir / "valid"
    valid_dir.mkdir()
    valid_code = """
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class ValidTool(Tool):
    name: ClassVar[str] = "valid"
    description: ClassVar[str] = "Valid tool"

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_completed(result="ok")
"""
    (valid_dir / "tool.py").write_text(valid_code)

    discovered = discover_tools(tools_dir)
    # Should discover valid tool, skip broken one
    assert "valid" in discovered
    assert "broken" not in discovered


def test_discover_tools_multiple_packages(tmp_path: Path) -> None:
    """Test discovery finds multiple tool packages."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    for i in range(3):
        package_dir = tools_dir / f"tool{i}"
        package_dir.mkdir()

        tool_code = f"""
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class Tool{i}(Tool):
    name: ClassVar[str] = "tool{i}"
    description: ClassVar[str] = "Tool {i}"

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_completed(result="ok")
"""
        (package_dir / "tool.py").write_text(tool_code)

    discovered = discover_tools(tools_dir)
    assert len(discovered) == 3
    assert all(f"tool{i}" in discovered for i in range(3))


def test_load_tool_metadata_valid_yaml(tmp_path: Path) -> None:
    """Test loading valid config.yaml."""
    tool_dir = tmp_path / "mytool"
    tool_dir.mkdir()

    config = """
name: mytool
version: 1.0.0
description: My tool description
status: published
"""
    (tool_dir / "config.yaml").write_text(config)

    metadata = load_tool_metadata(tool_dir)
    assert metadata["name"] == "mytool"
    assert metadata["version"] == "1.0.0"
    assert metadata["description"] == "My tool description"


def test_load_tool_metadata_missing_file(tmp_path: Path) -> None:
    """Test loading metadata with no config.yaml."""
    tool_dir = tmp_path / "mytool"
    tool_dir.mkdir()

    metadata = load_tool_metadata(tool_dir)
    assert metadata == {}


def test_load_tool_metadata_invalid_yaml(tmp_path: Path) -> None:
    """Test loading malformed config.yaml."""
    tool_dir = tmp_path / "mytool"
    tool_dir.mkdir()

    (tool_dir / "config.yaml").write_text("invalid: yaml: content: [")

    metadata = load_tool_metadata(tool_dir)
    assert metadata == {}


def test_scan_tool_module_no_files(tmp_path: Path) -> None:
    """Test scanning package with no tool.py or __init__.py."""
    package_dir = tmp_path / "empty"
    package_dir.mkdir()

    result = scan_tool_module(package_dir)
    assert result is None


def test_scan_tool_module_finds_tool_class(tmp_path: Path) -> None:
    """Test scanning finds Tool subclass."""
    package_dir = tmp_path / "mytool"
    package_dir.mkdir()

    tool_code = """
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class MyAwesomeTool(Tool):
    name: ClassVar[str] = "awesome"
    description: ClassVar[str] = "Awesome tool"

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_completed(result="awesome")
"""
    (package_dir / "tool.py").write_text(tool_code)

    result = scan_tool_module(package_dir)
    assert result is not None
    assert result.__name__ == "MyAwesomeTool"


def test_scan_tool_module_ignores_base_tool(tmp_path: Path) -> None:
    """Test scanning doesn't return the base Tool class."""
    package_dir = tmp_path / "basetool"
    package_dir.mkdir()

    tool_code = """
from raw_runtime.tools import Tool

# Should not detect this as a tool
MyTool = Tool
"""
    (package_dir / "tool.py").write_text(tool_code)

    result = scan_tool_module(package_dir)
    assert result is None


def test_scan_tool_module_finds_decorated_function(tmp_path: Path) -> None:
    """Test scanning finds @tool decorated function."""
    package_dir = tmp_path / "decorated"
    package_dir.mkdir()

    tool_code = """
from raw_runtime.tools import tool

@tool(description="Decorated tool")
def my_tool_func(input: str) -> str:
    return f"processed: {input}"
"""
    (package_dir / "tool.py").write_text(tool_code)

    result = scan_tool_module(package_dir)
    assert result is not None
    # @tool decorator returns Tool instance
    assert isinstance(result, Tool)


def test_registry_discover_and_register(tmp_path: Path) -> None:
    """Test ToolRegistry.discover_and_register method."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create two tools
    for name in ["alpha", "beta"]:
        package_dir = tools_dir / name
        package_dir.mkdir()

        tool_code = f"""
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class {name.capitalize()}Tool(Tool):
    name: ClassVar[str] = "{name}"
    description: ClassVar[str] = "{name.capitalize()} tool"

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_completed(result="{name}")
"""
        (package_dir / "tool.py").write_text(tool_code)

    registry = ToolRegistry()
    count = registry.discover_and_register(tools_dir)

    assert count == 2
    assert registry.has_tool("alpha")
    assert registry.has_tool("beta")
    assert len(registry.list_all()) == 2


def test_registry_discover_and_register_empty(tmp_path: Path) -> None:
    """Test discover_and_register with no tools."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    registry = ToolRegistry()
    count = registry.discover_and_register(tools_dir)

    assert count == 0
    assert len(registry.list_all()) == 0


def test_registry_discover_and_register_nonexistent(tmp_path: Path) -> None:
    """Test discover_and_register with nonexistent directory."""
    tools_dir = tmp_path / "nonexistent"

    registry = ToolRegistry()
    count = registry.discover_and_register(tools_dir)

    assert count == 0


def test_registry_discover_and_register_handles_errors(tmp_path: Path) -> None:
    """Test discover_and_register handles registration errors gracefully."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create tool that will fail during instantiation
    package_dir = tools_dir / "failing"
    package_dir.mkdir()

    tool_code = """
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class FailingTool(Tool):
    name: ClassVar[str] = "failing"
    description: ClassVar[str] = "Fails on init"

    def __init__(self):
        raise RuntimeError("Cannot instantiate")

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_completed(result="never")
"""
    (package_dir / "tool.py").write_text(tool_code)

    # Create valid tool
    valid_dir = tools_dir / "valid"
    valid_dir.mkdir()
    valid_code = """
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class ValidTool(Tool):
    name: ClassVar[str] = "valid"
    description: ClassVar[str] = "Valid tool"

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_completed(result="ok")
"""
    (valid_dir / "tool.py").write_text(valid_code)

    registry = ToolRegistry()
    count = registry.discover_and_register(tools_dir)

    # Should register valid tool, skip failing one
    assert count == 1
    assert registry.has_tool("valid")
    assert not registry.has_tool("failing")


def test_registry_discover_and_register_decorated_tools(tmp_path: Path) -> None:
    """Test discover_and_register works with @tool decorated functions."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    package_dir = tools_dir / "decorated"
    package_dir.mkdir()

    tool_code = """
from raw_runtime.tools import tool

@tool(description="Decorated helper", name="decorated")
def helper(value: str) -> str:
    return value.upper()
"""
    (package_dir / "tool.py").write_text(tool_code)

    registry = ToolRegistry()
    count = registry.discover_and_register(tools_dir)

    assert count == 1
    assert registry.has_tool("decorated")


@pytest.mark.asyncio
async def test_discovered_tool_is_functional(tmp_path: Path) -> None:
    """Test that discovered tools can actually be called."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    package_dir = tools_dir / "functional"
    package_dir.mkdir()

    tool_code = """
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class FunctionalTool(Tool):
    name: ClassVar[str] = "functional"
    description: ClassVar[str] = "Functional tool"

    async def run(self, message: str, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_started(message=message)
        yield self._emit_completed(result=f"processed: {message}")
"""
    (package_dir / "tool.py").write_text(tool_code)

    registry = ToolRegistry()
    registry.discover_and_register(tools_dir)

    tool_instance = registry.require("functional")
    result = await tool_instance.call(message="hello")

    assert result.success is True
    assert result.data["result"] == "processed: hello"


def test_discover_tools_ignores_files_in_tools_root(tmp_path: Path) -> None:
    """Test discovery ignores files directly in tools/ directory."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create file in root (should be ignored)
    (tools_dir / "not_a_package.py").write_text("# This should be ignored")

    # Create __init__.py in root (should be ignored)
    (tools_dir / "__init__.py").write_text("# Package marker")

    discovered = discover_tools(tools_dir)
    assert discovered == {}


def teardown_module() -> None:
    """Clean up imported test modules."""
    # Remove any test modules from sys.modules to avoid conflicts
    modules_to_remove = [key for key in sys.modules if key.startswith("tools.")]
    for module_name in modules_to_remove:
        del sys.modules[module_name]

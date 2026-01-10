"""Integration tests for tool discovery with BaseWorkflow."""

import sys
from pathlib import Path

import pytest
from pydantic import BaseModel

from raw_runtime import BaseWorkflow
from raw_runtime.tools.registry import set_tool_registry


class TestParams(BaseModel):
    """Test workflow parameters."""

    value: str = "test"


class TestWorkflow(BaseWorkflow[TestParams]):
    """Test workflow for tool discovery integration."""

    def run(self) -> int:
        """Run the workflow."""
        return 0


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    """Reset the global tool registry before each test."""
    from raw_runtime.tools.registry import ToolRegistry

    set_tool_registry(ToolRegistry())


def test_base_workflow_tool_auto_discovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test BaseWorkflow.tool() triggers auto-discovery."""
    # Create tools directory with a tool
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    package_dir = tools_dir / "mytool"
    package_dir.mkdir()

    tool_code = """
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class MyTestTool(Tool):
    name: ClassVar[str] = "mytool"
    description: ClassVar[str] = "Test tool"

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_started(**config)
        yield self._emit_completed(result="success")
"""
    (package_dir / "tool.py").write_text(tool_code)

    # Change to tmp directory so tools/ is found
    monkeypatch.chdir(tmp_path)

    # Create workflow and request tool
    workflow = TestWorkflow(params=TestParams())
    tool = workflow.tool("mytool")

    assert tool is not None
    assert tool.name == "mytool"


def test_base_workflow_tool_not_found_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test BaseWorkflow.tool() raises helpful error if tool not found."""
    # Create empty tools directory
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    workflow = TestWorkflow(params=TestParams())

    with pytest.raises(KeyError) as exc_info:
        workflow.tool("nonexistent")

    error_msg = str(exc_info.value)
    assert "nonexistent" in error_msg
    assert "not found" in error_msg
    assert "Hint:" in error_msg


def test_base_workflow_tool_caches_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test tool discovery is cached across calls."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    package_dir = tools_dir / "cached"
    package_dir.mkdir()

    tool_code = """
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class CachedTool(Tool):
    name: ClassVar[str] = "cached"
    description: ClassVar[str] = "Cached tool"

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_completed(result="ok")
"""
    (package_dir / "tool.py").write_text(tool_code)

    monkeypatch.chdir(tmp_path)

    workflow = TestWorkflow(params=TestParams())

    # First call triggers discovery
    tool1 = workflow.tool("cached")
    assert tool1.name == "cached"

    # Second call should use cached registry
    tool2 = workflow.tool("cached")
    assert tool2.name == "cached"

    # Should be the same instance from registry
    assert tool1 is tool2


def test_base_workflow_tool_no_tools_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test BaseWorkflow.tool() handles missing tools/ directory."""
    # No tools directory
    monkeypatch.chdir(tmp_path)

    workflow = TestWorkflow(params=TestParams())

    with pytest.raises(KeyError) as exc_info:
        workflow.tool("missing")

    assert "missing" in str(exc_info.value)


@pytest.mark.asyncio
async def test_discovered_tool_integration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test discovered tool works end-to-end with BaseWorkflow."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    package_dir = tools_dir / "processor"
    package_dir.mkdir()

    tool_code = """
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class ProcessorTool(Tool):
    name: ClassVar[str] = "processor"
    description: ClassVar[str] = "Process data"

    async def run(self, data: str, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_started(data=data)
        result = f"processed: {data}"
        yield self._emit_completed(result=result)
"""
    (package_dir / "tool.py").write_text(tool_code)

    monkeypatch.chdir(tmp_path)

    workflow = TestWorkflow(params=TestParams())
    tool = workflow.tool("processor")

    # Use the tool
    result = await tool.call(data="hello")

    assert result.success is True
    assert result.data["result"] == "processed: hello"


def test_multiple_workflows_share_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test multiple workflow instances share the global tool registry."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    package_dir = tools_dir / "shared"
    package_dir.mkdir()

    tool_code = """
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class SharedTool(Tool):
    name: ClassVar[str] = "shared"
    description: ClassVar[str] = "Shared tool"

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_completed(result="shared")
"""
    (package_dir / "tool.py").write_text(tool_code)

    monkeypatch.chdir(tmp_path)

    # First workflow discovers tool
    workflow1 = TestWorkflow(params=TestParams())
    tool1 = workflow1.tool("shared")

    # Second workflow should use already-discovered tool
    workflow2 = TestWorkflow(params=TestParams())
    tool2 = workflow2.tool("shared")

    # Should be the same instance
    assert tool1 is tool2


def test_discovery_with_decorated_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test BaseWorkflow can discover and use @tool decorated functions."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    package_dir = tools_dir / "decorator_tool"
    package_dir.mkdir()

    tool_code = """
from raw_runtime.tools import tool

@tool(description="Decorated helper", name="decorator_tool")
def helper_function(value: str) -> str:
    return value.upper()
"""
    (package_dir / "tool.py").write_text(tool_code)

    monkeypatch.chdir(tmp_path)

    workflow = TestWorkflow(params=TestParams())
    tool = workflow.tool("decorator_tool")

    assert tool is not None
    assert tool.name == "decorator_tool"


def teardown_module() -> None:
    """Clean up imported test modules."""
    # Remove test modules from sys.modules
    modules_to_remove = [key for key in sys.modules if key.startswith("tools.")]
    for module_name in modules_to_remove:
        del sys.modules[module_name]

    # Reset global registry
    from raw_runtime.tools.registry import ToolRegistry

    set_tool_registry(ToolRegistry())

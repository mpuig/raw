"""Tests for ToolRegistry implementations."""

import tempfile
from pathlib import Path

from raw.discovery.registry import (
    CompositeRegistry,
    LocalToolRegistry,
    ToolInfo,
    ToolRegistry,
    get_tool_registry,
    set_tool_registry,
)


class TestToolInfo:
    """Tests for ToolInfo model."""

    def test_basic_tool_info(self) -> None:
        info = ToolInfo(name="test-tool", description="A test tool")
        assert info.name == "test-tool"
        assert info.description == "A test tool"
        assert info.version == "1.0.0"
        assert info.source == "local"

    def test_tool_info_with_git(self) -> None:
        info = ToolInfo(
            name="remote-tool",
            source="git",
            git_url="https://github.com/user/tool",
            git_ref="main",
        )
        assert info.source == "git"
        assert info.git_url == "https://github.com/user/tool"


class TestLocalToolRegistry:
    """Tests for LocalToolRegistry."""

    def test_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = LocalToolRegistry(Path(tmpdir))
            assert registry.list_tools() == []

    def test_nonexistent_directory(self) -> None:
        registry = LocalToolRegistry(Path("/nonexistent/path"))
        assert registry.list_tools() == []

    def test_loads_tool_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir)
            tool_dir = tools_dir / "my-tool"
            tool_dir.mkdir()

            config = """
name: my-tool
version: "2.0.0"
description: A test tool for testing
dependencies:
  - httpx>=0.27
inputs:
  - name: param1
    type: string
"""
            (tool_dir / "config.yaml").write_text(config)

            registry = LocalToolRegistry(tools_dir)
            tools = registry.list_tools()

            assert len(tools) == 1
            assert tools[0].name == "my-tool"
            assert tools[0].version == "2.0.0"
            assert tools[0].description == "A test tool for testing"
            assert tools[0].dependencies == ["httpx>=0.27"]

    def test_get_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir)
            tool_dir = tools_dir / "fetch-data"
            tool_dir.mkdir()
            (tool_dir / "config.yaml").write_text("name: fetch-data\ndescription: Fetch data")

            registry = LocalToolRegistry(tools_dir)

            tool = registry.get_tool("fetch-data")
            assert tool is not None
            assert tool.name == "fetch-data"

            assert registry.get_tool("nonexistent") is None

    def test_search_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir)

            for name in ["hackernews", "weather-api", "stock-data"]:
                tool_dir = tools_dir / name
                tool_dir.mkdir()
                (tool_dir / "config.yaml").write_text(f"name: {name}\ndescription: Tool for {name}")

            registry = LocalToolRegistry(tools_dir)
            results = registry.search("hack")

            assert len(results) == 1
            assert results[0].tool.name == "hackernews"
            assert results[0].score > 0

    def test_search_by_description(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir)

            tool_dir = tools_dir / "my-tool"
            tool_dir.mkdir()
            (tool_dir / "config.yaml").write_text("name: my-tool\ndescription: Fetch stock prices from Yahoo Finance")

            registry = LocalToolRegistry(tools_dir)
            results = registry.search("stock")

            assert len(results) == 1
            assert results[0].tool.name == "my-tool"

    def test_cache_invalidation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir)
            registry = LocalToolRegistry(tools_dir)

            assert registry.list_tools() == []

            # Add a tool
            tool_dir = tools_dir / "new-tool"
            tool_dir.mkdir()
            (tool_dir / "config.yaml").write_text("name: new-tool\ndescription: New tool")

            # Still empty due to cache
            assert registry.list_tools() == []

            # Invalidate cache
            registry.invalidate_cache()
            assert len(registry.list_tools()) == 1

    def test_ignores_hidden_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tools_dir = Path(tmpdir)

            # Hidden directory
            hidden = tools_dir / ".hidden"
            hidden.mkdir()
            (hidden / "config.yaml").write_text("name: hidden\ndescription: Hidden")

            # Underscore directory
            underscore = tools_dir / "_private"
            underscore.mkdir()
            (underscore / "config.yaml").write_text("name: private\ndescription: Private")

            # Normal directory
            normal = tools_dir / "normal"
            normal.mkdir()
            (normal / "config.yaml").write_text("name: normal\ndescription: Normal")

            registry = LocalToolRegistry(tools_dir)
            tools = registry.list_tools()

            assert len(tools) == 1
            assert tools[0].name == "normal"


class TestCompositeRegistry:
    """Tests for CompositeRegistry."""

    def test_combines_tools_from_multiple_registries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dir1 = Path(tmpdir) / "reg1"
            dir2 = Path(tmpdir) / "reg2"
            dir1.mkdir()
            dir2.mkdir()

            # Tool in first registry
            (dir1 / "tool1").mkdir()
            (dir1 / "tool1" / "config.yaml").write_text("name: tool1\ndescription: First")

            # Tool in second registry
            (dir2 / "tool2").mkdir()
            (dir2 / "tool2" / "config.yaml").write_text("name: tool2\ndescription: Second")

            reg1 = LocalToolRegistry(dir1)
            reg2 = LocalToolRegistry(dir2)
            composite = CompositeRegistry([reg1, reg2])

            tools = composite.list_tools()
            names = {t.name for t in tools}

            assert len(tools) == 2
            assert names == {"tool1", "tool2"}

    def test_first_registry_takes_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dir1 = Path(tmpdir) / "reg1"
            dir2 = Path(tmpdir) / "reg2"
            dir1.mkdir()
            dir2.mkdir()

            # Same tool name in both registries
            (dir1 / "shared").mkdir()
            (dir1 / "shared" / "config.yaml").write_text("name: shared\ndescription: From reg1")

            (dir2 / "shared").mkdir()
            (dir2 / "shared" / "config.yaml").write_text("name: shared\ndescription: From reg2")

            reg1 = LocalToolRegistry(dir1)
            reg2 = LocalToolRegistry(dir2)
            composite = CompositeRegistry([reg1, reg2])

            tool = composite.get_tool("shared")
            assert tool is not None
            assert tool.description == "From reg1"

    def test_search_merges_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dir1 = Path(tmpdir) / "reg1"
            dir2 = Path(tmpdir) / "reg2"
            dir1.mkdir()
            dir2.mkdir()

            (dir1 / "stock-api").mkdir()
            (dir1 / "stock-api" / "config.yaml").write_text("name: stock-api\ndescription: Stock data API")

            (dir2 / "stock-chart").mkdir()
            (dir2 / "stock-chart" / "config.yaml").write_text("name: stock-chart\ndescription: Chart stocks")

            reg1 = LocalToolRegistry(dir1)
            reg2 = LocalToolRegistry(dir2)
            composite = CompositeRegistry([reg1, reg2])

            results = composite.search("stock")
            names = {r.tool.name for r in results}

            assert len(results) == 2
            assert names == {"stock-api", "stock-chart"}


class TestGlobalRegistry:
    """Tests for global registry getter/setter."""

    def teardown_method(self) -> None:
        set_tool_registry(None)

    def test_default_registry(self) -> None:
        registry = get_tool_registry()
        assert isinstance(registry, LocalToolRegistry)

    def test_set_custom_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            custom = LocalToolRegistry(Path(tmpdir))
            set_tool_registry(custom)
            assert get_tool_registry() is custom


class TestProtocolCompliance:
    """Tests that implementations satisfy the ToolRegistry protocol."""

    def test_local_registry_is_tool_registry(self) -> None:
        registry = LocalToolRegistry()
        assert isinstance(registry, ToolRegistry)

    def test_composite_registry_is_tool_registry(self) -> None:
        registry = CompositeRegistry([])
        assert isinstance(registry, ToolRegistry)

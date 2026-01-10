"""Tests for SDK tool functions."""

from pathlib import Path

import pytest
import yaml

from raw.sdk import (
    ToolNotFoundError,
    create_tool,
    delete_tool,
    get_tool,
    list_tools,
    update_tool,
)


@pytest.fixture
def temp_tools_dir(tmp_path: Path) -> Path:
    """Create a temporary tools directory."""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "__init__.py").write_text('"""Tools package."""\n')
    return tools_dir


class TestCreateTool:
    """Tests for create_tool function."""

    def test_create_tool_minimal(self, temp_tools_dir: Path) -> None:
        """Test creating tool with minimal parameters."""
        tool = create_tool(
            name="stock_fetcher",
            description="Fetch stock data from Yahoo Finance",
            tools_dir=temp_tools_dir,
        )

        assert tool.name == "stock_fetcher"
        assert tool.description == "Fetch stock data from Yahoo Finance"
        assert tool.version == "1.0.0"
        assert tool.path.exists()

        # Verify config.yaml was created
        config_path = tool.path / "config.yaml"
        assert config_path.exists()

        config_data = yaml.safe_load(config_path.read_text())
        assert config_data["name"] == "stock_fetcher"
        assert config_data["description"] == "Fetch stock data from Yahoo Finance"
        assert config_data["status"] == "draft"

    def test_create_tool_function_type(self, temp_tools_dir: Path) -> None:
        """Test creating tool with function type."""
        tool = create_tool(
            name="email_sender",
            description="Send emails via SMTP",
            tool_type="function",
            tools_dir=temp_tools_dir,
        )

        assert tool.name == "email_sender"
        assert tool.path.exists()

    def test_create_tool_class_type(self, temp_tools_dir: Path) -> None:
        """Test creating tool with class type."""
        tool = create_tool(
            name="pdf_generator",
            description="Generate PDF reports",
            tool_type="class",
            tools_dir=temp_tools_dir,
        )

        assert tool.name == "pdf_generator"
        assert tool.path.exists()

    def test_create_tool_sanitizes_name(self, temp_tools_dir: Path) -> None:
        """Test that tool name is sanitized."""
        tool = create_tool(
            name="My-Cool Tool",
            description="Does cool things",
            tools_dir=temp_tools_dir,
        )

        assert tool.name == "my_cool_tool"
        assert (temp_tools_dir / "my_cool_tool").exists()

    def test_create_tool_duplicate_raises_error(self, temp_tools_dir: Path) -> None:
        """Test creating duplicate tool raises error."""
        create_tool(
            name="duplicate",
            description="First tool",
            tools_dir=temp_tools_dir,
        )

        with pytest.raises(ValueError, match="Tool already exists"):
            create_tool(
                name="duplicate",
                description="Second tool",
                tools_dir=temp_tools_dir,
            )


class TestListTools:
    """Tests for list_tools function."""

    def test_list_empty_tools(self, temp_tools_dir: Path) -> None:
        """Test listing tools when none exist."""
        tools = list_tools(temp_tools_dir)
        assert tools == []

    def test_list_tools(self, temp_tools_dir: Path) -> None:
        """Test listing multiple tools."""
        create_tool(
            name="tool1",
            description="First tool",
            tools_dir=temp_tools_dir,
        )
        create_tool(
            name="tool2",
            description="Second tool",
            tools_dir=temp_tools_dir,
        )

        tools = list_tools(temp_tools_dir)

        assert len(tools) == 2
        tool_names = {t.name for t in tools}
        assert "tool1" in tool_names
        assert "tool2" in tool_names

    def test_list_tools_filters_invalid_dirs(self, temp_tools_dir: Path) -> None:
        """Test that list_tools ignores invalid directories."""
        create_tool(
            name="valid_tool",
            description="Valid tool",
            tools_dir=temp_tools_dir,
        )

        # Create directories without config.yaml
        (temp_tools_dir / "invalid_dir").mkdir()
        (temp_tools_dir / ".hidden").mkdir()
        (temp_tools_dir / "__pycache__").mkdir()

        tools = list_tools(temp_tools_dir)
        assert len(tools) == 1
        assert tools[0].name == "valid_tool"

    def test_list_tools_returns_metadata(self, temp_tools_dir: Path) -> None:
        """Test that list_tools returns complete metadata."""
        create_tool(
            name="test_tool",
            description="Test description",
            tools_dir=temp_tools_dir,
        )

        tools = list_tools(temp_tools_dir)

        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "test_tool"
        assert tool.description == "Test description"
        assert tool.version == "1.0.0"
        assert isinstance(tool.operations, list)
        assert tool.path == temp_tools_dir / "test_tool"


class TestGetTool:
    """Tests for get_tool function."""

    def test_get_tool_by_name(self, temp_tools_dir: Path) -> None:
        """Test getting tool by name."""
        created = create_tool(
            name="my_tool",
            description="Test tool",
            tools_dir=temp_tools_dir,
        )

        tool = get_tool("my_tool", temp_tools_dir)

        assert tool is not None
        assert tool.name == created.name
        assert tool.description == created.description
        assert tool.path == created.path

    def test_get_tool_not_found(self, temp_tools_dir: Path) -> None:
        """Test getting non-existent tool returns None."""
        tool = get_tool("nonexistent", temp_tools_dir)
        assert tool is None

    def test_get_tool_invalid_config(self, temp_tools_dir: Path) -> None:
        """Test getting tool with invalid config returns None."""
        # Create directory without valid config
        tool_dir = temp_tools_dir / "broken_tool"
        tool_dir.mkdir()
        (tool_dir / "config.yaml").write_text("invalid: yaml: content:")

        tool = get_tool("broken_tool", temp_tools_dir)
        assert tool is None


class TestUpdateTool:
    """Tests for update_tool function."""

    def test_update_tool_description(self, temp_tools_dir: Path) -> None:
        """Test updating tool description."""
        create_tool(
            name="my_tool",
            description="Original description",
            tools_dir=temp_tools_dir,
        )

        updated = update_tool(
            "my_tool",
            description="Updated description",
            tools_dir=temp_tools_dir,
        )

        assert updated.description == "Updated description"

        # Verify config file was updated
        config_path = temp_tools_dir / "my_tool" / "config.yaml"
        config_data = yaml.safe_load(config_path.read_text())
        assert config_data["description"] == "Updated description"

    def test_update_tool_version(self, temp_tools_dir: Path) -> None:
        """Test updating tool version."""
        create_tool(
            name="my_tool",
            description="Test tool",
            tools_dir=temp_tools_dir,
        )

        updated = update_tool(
            "my_tool",
            version="2.0.0",
            tools_dir=temp_tools_dir,
        )

        assert updated.version == "2.0.0"

        # Verify config file was updated
        config_path = temp_tools_dir / "my_tool" / "config.yaml"
        config_data = yaml.safe_load(config_path.read_text())
        assert config_data["version"] == "2.0.0"

    def test_update_tool_multiple_fields(self, temp_tools_dir: Path) -> None:
        """Test updating multiple fields at once."""
        create_tool(
            name="my_tool",
            description="Original description",
            tools_dir=temp_tools_dir,
        )

        updated = update_tool(
            "my_tool",
            description="New description",
            version="3.0.0",
            tools_dir=temp_tools_dir,
        )

        assert updated.description == "New description"
        assert updated.version == "3.0.0"

    def test_update_tool_not_found(self, temp_tools_dir: Path) -> None:
        """Test updating non-existent tool raises error."""
        with pytest.raises(ToolNotFoundError, match="Tool not found"):
            update_tool(
                "nonexistent",
                description="New description",
                tools_dir=temp_tools_dir,
            )

    def test_update_tool_no_changes(self, temp_tools_dir: Path) -> None:
        """Test updating tool with no changes."""
        original = create_tool(
            name="my_tool",
            description="Original description",
            tools_dir=temp_tools_dir,
        )

        updated = update_tool("my_tool", tools_dir=temp_tools_dir)

        assert updated.description == original.description
        assert updated.version == original.version


class TestDeleteTool:
    """Tests for delete_tool function."""

    def test_delete_tool(self, temp_tools_dir: Path) -> None:
        """Test deleting a tool."""
        tool = create_tool(
            name="to_delete",
            description="Test tool",
            tools_dir=temp_tools_dir,
        )
        tool_path = tool.path

        assert tool_path.exists()

        delete_tool("to_delete", temp_tools_dir)

        assert not tool_path.exists()

    def test_delete_tool_not_found(self, temp_tools_dir: Path) -> None:
        """Test deleting non-existent tool raises error."""
        with pytest.raises(ToolNotFoundError, match="Tool not found"):
            delete_tool("nonexistent", temp_tools_dir)

    def test_delete_tool_removes_all_files(self, temp_tools_dir: Path) -> None:
        """Test that delete removes all tool files."""
        tool = create_tool(
            name="my_tool",
            description="Test tool",
            tools_dir=temp_tools_dir,
        )

        # Add extra files to the tool directory
        (tool.path / "extra_file.py").write_text("# Extra file")
        (tool.path / "subdir").mkdir()
        (tool.path / "subdir" / "nested.py").write_text("# Nested file")

        delete_tool("my_tool", temp_tools_dir)

        assert not tool.path.exists()


class TestToolModel:
    """Tests for Tool model."""

    def test_tool_from_config(self, temp_tools_dir: Path) -> None:
        """Test creating Tool model from config."""
        created = create_tool(
            name="test_tool",
            description="Test description",
            tools_dir=temp_tools_dir,
        )

        # Get it back
        tool = get_tool("test_tool", temp_tools_dir)

        assert tool is not None
        assert tool.name == created.name
        assert tool.description == created.description
        assert tool.version == created.version
        assert tool.path == created.path

    def test_tool_operations_from_inputs(self, temp_tools_dir: Path) -> None:
        """Test that operations are derived from tool inputs."""
        tool = create_tool(
            name="test_tool",
            description="Test tool",
            tools_dir=temp_tools_dir,
        )

        # Operations should be populated from inputs
        assert isinstance(tool.operations, list)


class TestToolIntegration:
    """Integration tests for tool operations."""

    def test_create_list_get_delete_flow(self, temp_tools_dir: Path) -> None:
        """Test complete tool lifecycle."""
        # Create
        tool = create_tool(
            name="lifecycle_tool",
            description="Test lifecycle",
            tools_dir=temp_tools_dir,
        )
        assert tool.name == "lifecycle_tool"

        # List
        tools = list_tools(temp_tools_dir)
        assert len(tools) == 1
        assert tools[0].name == "lifecycle_tool"

        # Get
        retrieved = get_tool("lifecycle_tool", temp_tools_dir)
        assert retrieved is not None
        assert retrieved.name == tool.name

        # Update
        updated = update_tool(
            "lifecycle_tool",
            description="Updated description",
            tools_dir=temp_tools_dir,
        )
        assert updated.description == "Updated description"

        # Delete
        delete_tool("lifecycle_tool", temp_tools_dir)
        assert get_tool("lifecycle_tool", temp_tools_dir) is None
        assert len(list_tools(temp_tools_dir)) == 0

    def test_multiple_tools_operations(self, temp_tools_dir: Path) -> None:
        """Test operations with multiple tools."""
        # Create multiple tools
        create_tool(
            name="tool_alpha",
            description="Alpha tool",
            tools_dir=temp_tools_dir,
        )
        create_tool(
            name="tool_beta",
            description="Beta tool",
            tools_dir=temp_tools_dir,
        )
        create_tool(
            name="tool_gamma",
            description="Gamma tool",
            tools_dir=temp_tools_dir,
        )

        # List all
        tools = list_tools(temp_tools_dir)
        assert len(tools) == 3

        # Update one
        update_tool("tool_beta", version="2.0.0", tools_dir=temp_tools_dir)

        # Verify others unchanged
        alpha = get_tool("tool_alpha", temp_tools_dir)
        gamma = get_tool("tool_gamma", temp_tools_dir)
        assert alpha is not None
        assert gamma is not None
        assert alpha.version == "1.0.0"
        assert gamma.version == "1.0.0"

        # Delete one
        delete_tool("tool_beta", temp_tools_dir)

        # Verify others remain
        tools = list_tools(temp_tools_dir)
        assert len(tools) == 2
        tool_names = {t.name for t in tools}
        assert "tool_alpha" in tool_names
        assert "tool_gamma" in tool_names
        assert "tool_beta" not in tool_names

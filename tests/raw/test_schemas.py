"""Tests for RAW schemas."""

from datetime import datetime

from raw.core.schemas import (
    DataType,
    InputDefinition,
    LibrariesConfig,
    OutputDefinition,
    StepDefinition,
    ToolConfig,
    ToolStatus,
    WorkflowConfig,
    WorkflowDescription,
    WorkflowStatus,
)


def test_input_definition() -> None:
    """Test InputDefinition creation."""
    input_def = InputDefinition(
        name="ticker",
        type=DataType.STRING,
        description="Stock symbol",
        required=True,
    )
    assert input_def.name == "ticker"
    assert input_def.type == DataType.STRING
    assert input_def.required is True


def test_input_definition_with_default() -> None:
    """Test InputDefinition with default value."""
    input_def = InputDefinition(
        name="period",
        type=DataType.STRING,
        description="Time period",
        required=False,
        default="3mo",
    )
    assert input_def.default == "3mo"
    assert input_def.required is False


def test_output_definition() -> None:
    """Test OutputDefinition creation."""
    output_def = OutputDefinition(
        name="report",
        type=DataType.FILE,
        format="pdf",
        description="Analysis report",
    )
    assert output_def.name == "report"
    assert output_def.type == DataType.FILE
    assert output_def.format == "pdf"


def test_step_definition() -> None:
    """Test StepDefinition creation."""
    step = StepDefinition(
        id="fetch-data",
        name="Fetch Data",
        description="Fetch stock data from Yahoo Finance",
        tool="fetch_stock-data",
        inputs={"ticker": "$input.ticker"},
        outputs=[OutputDefinition(name="price_data", type=DataType.DATAFRAME)],
    )
    assert step.id == "fetch-data"
    assert step.tool == "fetch_stock-data"
    assert step.inputs["ticker"] == "$input.ticker"


def test_workflow_description() -> None:
    """Test WorkflowDescription creation."""
    desc = WorkflowDescription(
        intent="Analyze stock prices",
        inputs=[InputDefinition(name="ticker", type=DataType.STRING)],
        outputs=[OutputDefinition(name="report", type=DataType.FILE)],
    )
    assert desc.intent == "Analyze stock prices"
    assert len(desc.inputs) == 1
    assert len(desc.outputs) == 1


def test_workflow_config() -> None:
    """Test WorkflowConfig creation."""
    config = WorkflowConfig(
        id="20251206-test-abc123",
        name="test-workflow",
        description=WorkflowDescription(intent="Test workflow"),
    )
    assert config.id == "20251206-test-abc123"
    assert config.status == "draft"  # Enum value
    assert config.version == "1.0.0"
    assert isinstance(config.created_at, datetime)


def test_workflow_config_with_steps() -> None:
    """Test WorkflowConfig with steps."""
    config = WorkflowConfig(
        id="20251206-test-abc123",
        name="test-workflow",
        description=WorkflowDescription(intent="Test workflow"),
        steps=[
            StepDefinition(
                id="step-1",
                name="Step 1",
                description="First step",
                tool="my-tool",
            )
        ],
    )
    assert len(config.steps) == 1
    assert config.steps[0].id == "step-1"


def test_workflow_status_enum_values() -> None:
    """Test that workflow status uses enum values."""
    config = WorkflowConfig(
        id="test",
        name="test",
        status=WorkflowStatus.GENERATED,
        description=WorkflowDescription(intent="Test"),
    )
    # model_dump should return string value, not enum
    data = config.model_dump()
    assert data["status"] == "generated"


def test_tool_config() -> None:
    """Test ToolConfig creation."""
    config = ToolConfig(
        name="fetch_stock-data",
        description="Fetch stock data from Yahoo Finance",
        inputs=[InputDefinition(name="ticker", type=DataType.STRING)],
        outputs=[OutputDefinition(name="data", type=DataType.DATAFRAME)],
        dependencies=["yfinance>=0.2.0", "pandas>=2.0"],
    )
    assert config.name == "fetch_stock-data"
    assert config.status == "draft"  # Enum value
    assert len(config.dependencies) == 2


def test_tool_status_enum_values() -> None:
    """Test that tool status uses enum values."""
    config = ToolConfig(
        name="test",
        status=ToolStatus.PUBLISHED,
        description="Test tool",
    )
    data = config.model_dump()
    assert data["status"] == "published"


def test_libraries_config_defaults() -> None:
    """Test LibrariesConfig default values."""
    config = LibrariesConfig()
    assert config.data_fetching["stocks"] == "yfinance"
    assert config.data_processing["dataframes"] == "pandas"
    assert config.visualization["charts"] == "matplotlib"


def test_libraries_config_get_library() -> None:
    """Test LibrariesConfig.get_library method."""
    config = LibrariesConfig()
    assert config.get_library("data_fetching", "stocks") == "yfinance"
    assert config.get_library("data_processing", "dataframes") == "pandas"
    assert config.get_library("nonexistent", "task") is None


def test_libraries_config_all_libraries() -> None:
    """Test LibrariesConfig.all_libraries method."""
    config = LibrariesConfig()
    all_libs = config.all_libraries()
    assert "stocks" in all_libs
    assert all_libs["stocks"] == "yfinance"
    assert "dataframes" in all_libs


def test_tool_dependency() -> None:
    """Test ToolDependency creation."""
    from raw.core.schemas import ToolDependency

    dep = ToolDependency(name="hackernews", source="local")
    assert dep.name == "hackernews"
    assert dep.source == "local"
    assert dep.version is None


def test_tool_dependency_git() -> None:
    """Test ToolDependency with git source."""
    from raw.core.schemas import ToolDependency

    dep = ToolDependency(
        name="remote-tool",
        source="git",
        git_url="https://github.com/user/tool",
        git_ref="v1.0.0",
    )
    assert dep.source == "git"
    assert dep.git_url == "https://github.com/user/tool"
    assert dep.git_ref == "v1.0.0"


def test_dependency_config() -> None:
    """Test DependencyConfig creation and methods."""
    from raw.core.schemas import DependencyConfig, ToolDependency

    config = DependencyConfig()
    assert config.tools == []

    # Add tools
    tool1 = ToolDependency(name="tool1", source="local")
    tool2 = ToolDependency(name="tool2", source="git", git_url="https://example.com/tool2")

    config.add_tool(tool1)
    config.add_tool(tool2)

    assert len(config.tools) == 2
    assert config.get_tool("tool1") == tool1
    assert config.get_tool("nonexistent") is None


def test_dependency_config_update_tool() -> None:
    """Test that add_tool updates existing tools."""
    from raw.core.schemas import DependencyConfig, ToolDependency

    config = DependencyConfig()
    config.add_tool(ToolDependency(name="tool1", version="1.0.0"))
    config.add_tool(ToolDependency(name="tool1", version="2.0.0"))

    assert len(config.tools) == 1
    assert config.get_tool("tool1").version == "2.0.0"


def test_dependency_config_remove_tool() -> None:
    """Test removing tools from DependencyConfig."""
    from raw.core.schemas import DependencyConfig, ToolDependency

    config = DependencyConfig()
    config.add_tool(ToolDependency(name="tool1"))
    config.add_tool(ToolDependency(name="tool2"))

    assert config.remove_tool("tool1") is True
    assert config.remove_tool("tool1") is False  # Already removed
    assert len(config.tools) == 1


def test_dependency_config_list_by_source() -> None:
    """Test listing tools by source."""
    from raw.core.schemas import DependencyConfig, ToolDependency

    config = DependencyConfig()
    config.add_tool(ToolDependency(name="local1", source="local"))
    config.add_tool(ToolDependency(name="local2", source="local"))
    config.add_tool(ToolDependency(name="git1", source="git"))

    local = config.list_local()
    installed = config.list_installed()

    assert len(local) == 2
    assert len(installed) == 1
    assert installed[0].name == "git1"


def test_libraries_config_custom() -> None:
    """Test LibrariesConfig with custom libraries."""
    config = LibrariesConfig(custom={"my_task": "my_library"})
    assert config.custom["my_task"] == "my_library"
    all_libs = config.all_libraries()
    assert all_libs["my_task"] == "my_library"

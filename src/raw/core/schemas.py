"""Pydantic schemas for RAW workflows and tools."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStatus(str, Enum):
    """Workflow lifecycle status."""

    DRAFT = "draft"
    GENERATED = "generated"
    TESTED = "tested"
    PUBLISHED = "published"


class ToolStatus(str, Enum):
    """Tool lifecycle status."""

    DRAFT = "draft"
    TESTED = "tested"
    PUBLISHED = "published"


class DataType(str, Enum):
    """Supported data types for inputs/outputs."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    DATAFRAME = "DataFrame"
    FILE = "file"
    ANY = "any"


class InputDefinition(BaseModel):
    """Definition of an input parameter."""

    name: str
    type: DataType = DataType.STRING
    description: str = ""
    required: bool = True
    default: Any = None


class OutputDefinition(BaseModel):
    """Definition of an output."""

    name: str
    type: DataType = DataType.ANY
    description: str = ""
    format: str | None = None  # For file types: pdf, markdown, json, etc.


class StepDefinition(BaseModel):
    """Definition of a workflow step."""

    id: str
    name: str
    description: str
    tool: str
    tool_version: str | None = None  # Pinned on publish
    tool_hash: str | None = None  # SHA256 hash of tool files, pinned on publish
    inputs: dict[str, str] = Field(default_factory=dict)  # Maps tool inputs to sources
    outputs: list[OutputDefinition] = Field(default_factory=list)


class WorkflowDescription(BaseModel):
    """High-level workflow description."""

    intent: str
    inputs: list[InputDefinition] = Field(default_factory=list)
    outputs: list[OutputDefinition] = Field(default_factory=list)


class WorkflowConfig(BaseModel):
    """Complete workflow configuration."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    name: str
    version: str = "1.0.0"
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    published_at: datetime | None = None

    description: WorkflowDescription
    steps: list[StepDefinition] = Field(default_factory=list)
    tool_snapshots: dict[str, dict] | None = None


class ToolConfig(BaseModel):
    """Tool configuration."""

    model_config = ConfigDict(use_enum_values=True)

    name: str
    version: str = "1.0.0"
    status: ToolStatus = ToolStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    description: str
    inputs: list[InputDefinition] = Field(default_factory=list)
    outputs: list[OutputDefinition] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)  # PEP 723 deps
    tool_hash: str | None = None  # SHA256 hash of tool files, set on publish


class ToolDependency(BaseModel):
    """A tool dependency specification."""

    name: str  # Tool name (e.g., "hackernews")
    source: str = "local"  # "local", "git", "registry"
    version: str | None = None  # Version constraint (e.g., ">=1.0.0")
    git_url: str | None = None  # Git URL for remote tools
    git_ref: str | None = None  # Git ref (branch, tag, commit)
    installed_at: datetime | None = None  # When installed
    content_hash: str | None = None  # SHA256 of tool files


class DependencyConfig(BaseModel):
    """Tool dependencies configuration for raw.yaml."""

    model_config = ConfigDict(use_enum_values=True)

    tools: list[ToolDependency] = Field(default_factory=list)

    def get_tool(self, name: str) -> ToolDependency | None:
        """Get a tool dependency by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def add_tool(self, tool: ToolDependency) -> None:
        """Add or update a tool dependency."""
        existing = self.get_tool(tool.name)
        if existing:
            self.tools.remove(existing)
        self.tools.append(tool)

    def remove_tool(self, name: str) -> bool:
        """Remove a tool dependency. Returns True if removed."""
        tool = self.get_tool(name)
        if tool:
            self.tools.remove(tool)
            return True
        return False

    def list_local(self) -> list[ToolDependency]:
        """List locally-created tools."""
        return [t for t in self.tools if t.source == "local"]

    def list_installed(self) -> list[ToolDependency]:
        """List installed (remote) tools."""
        return [t for t in self.tools if t.source != "local"]


class LibrariesConfig(BaseModel):
    """Preferred libraries configuration."""

    data_fetching: dict[str, str] = Field(
        default_factory=lambda: {
            "stocks": "yfinance",
            "web": "requests",
            "api": "httpx",
        }
    )

    data_processing: dict[str, str] = Field(
        default_factory=lambda: {
            "dataframes": "pandas",
            "numerical": "numpy",
        }
    )

    visualization: dict[str, str] = Field(
        default_factory=lambda: {
            "charts": "matplotlib",
            "interactive": "plotly",
        }
    )

    file_formats: dict[str, str] = Field(
        default_factory=lambda: {
            "pdf": "reportlab",
            "excel": "openpyxl",
            "markdown": "markdown",
        }
    )

    communication: dict[str, str] = Field(
        default_factory=lambda: {
            "email": "smtplib",
            "slack": "slack-sdk",
        }
    )

    custom: dict[str, str] = Field(default_factory=dict)

    def get_library(self, category: str, task: str) -> str | None:
        """Get preferred library for a category/task."""
        cat_dict = getattr(self, category, None)
        if cat_dict and isinstance(cat_dict, dict):
            return cat_dict.get(task)  # type: ignore[no-any-return]
        return self.custom.get(task)

    def all_libraries(self) -> dict[str, str]:
        """Get all libraries as a flat dict."""
        result = {}
        for cat in [
            "data_fetching",
            "data_processing",
            "visualization",
            "file_formats",
            "communication",
            "custom",
        ]:
            cat_dict = getattr(self, cat, {})
            if isinstance(cat_dict, dict):
                result.update(cat_dict)
        return result

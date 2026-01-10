# RAW Python SDK

Programmatic API for creating and managing RAW workflows and tools.

## Overview

The SDK provides a clean, typed interface for workflow and tool construction without requiring CLI commands. Agents can use this to build workflows and tools programmatically.

## Usage

### Managing Tools

```python
from raw.sdk import create_tool, list_tools, get_tool, update_tool, delete_tool

# Create a new tool
tool = create_tool(
    name="stock_fetcher",
    description="Fetch real-time stock prices from Yahoo Finance API"
)

# List all tools
tools = list_tools()
for t in tools:
    print(f"{t.name} v{t.version}: {t.description}")

# Get specific tool
tool = get_tool("stock_fetcher")
if tool:
    print(f"Found: {tool.name} at {tool.path}")

# Update tool metadata
updated = update_tool("stock_fetcher", version="2.0.0", description="Enhanced stock fetcher")

# Delete tool
delete_tool("stock_fetcher")
```

### Managing Workflows

```python
from raw.sdk import create_workflow, add_step, list_workflows

# Create a new workflow
workflow = create_workflow(
    name="stock-analysis",
    intent="Fetch TSLA stock data and generate report"
)

# Add steps
add_step(
    workflow,
    name="fetch-data",
    tool="stock_fetcher",
    config={"ticker": "TSLA", "period": "1mo"}
)

add_step(
    workflow,
    name="generate-report",
    tool="pdf_generator",
    config={"template": "stock_report.html"}
)

# List all workflows
workflows = list_workflows()
for wf in workflows:
    print(f"{wf.id}: {wf.name} ({wf.status})")
```

## API Reference

### Tool Management Functions

#### `create_tool(name: str, description: str, tool_type: Literal["function", "class"] = "function", tools_dir: Path | None = None) -> Tool`
Create a new tool package.

**Parameters:**
- `name`: Tool name (e.g., "stock_fetcher")
- `description`: Tool description for search
- `tool_type`: "function" for @tool decorator, "class" for Tool subclass
- `tools_dir`: Directory to create tool in (default: ./tools/)

**Returns:** `Tool` object with metadata and path

#### `list_tools(tools_dir: Path | None = None) -> list[Tool]`
List all tool packages.

**Parameters:**
- `tools_dir`: Directory to search for tools (default: ./tools/)

**Returns:** List of `Tool` objects

#### `get_tool(name: str, tools_dir: Path | None = None) -> Tool | None`
Get tool metadata by name.

**Parameters:**
- `name`: Tool name
- `tools_dir`: Directory to search for tools (default: ./tools/)

**Returns:** `Tool` object or `None` if not found

#### `update_tool(name: str, description: str | None = None, version: str | None = None, tools_dir: Path | None = None) -> Tool`
Update tool metadata in config.yaml.

**Parameters:**
- `name`: Tool name
- `description`: New description (optional)
- `version`: New version (optional)
- `tools_dir`: Directory to search for tools (default: ./tools/)

**Returns:** Updated `Tool` object

**Raises:** `ToolNotFoundError` if tool doesn't exist

#### `delete_tool(name: str, tools_dir: Path | None = None) -> None`
Delete a tool package.

**Parameters:**
- `name`: Tool name
- `tools_dir`: Directory to search for tools (default: ./tools/)

**Raises:** `ToolNotFoundError` if tool doesn't exist

### Workflow Management Functions

#### `create_workflow(name: str, intent: str | None = None) -> Workflow`
Create a new workflow programmatically.

**Parameters:**
- `name`: Human-readable workflow name
- `intent`: Natural language description of what the workflow does

**Returns:** `Workflow` object with metadata and path

#### `list_workflows() -> list[Workflow]`
List all workflows in the project.

**Returns:** List of `Workflow` objects

#### `get_workflow(workflow_id: str) -> Workflow | None`
Get a workflow by ID or partial match.

**Parameters:**
- `workflow_id`: Full or partial workflow ID

**Returns:** `Workflow` object or `None` if not found

#### `update_workflow(workflow: Workflow, **kwargs) -> Workflow`
Update workflow metadata.

**Parameters:**
- `workflow`: Workflow to update
- `**kwargs`: Fields to update (name, intent, status, version)

**Returns:** Updated `Workflow` object

#### `delete_workflow(workflow: Workflow) -> None`
Delete a workflow and all its files.

**Parameters:**
- `workflow`: Workflow to delete

**Raises:** `WorkflowNotFoundError` if workflow doesn't exist

#### `add_step(workflow: Workflow, name: str, tool: str | None = None, code: str | None = None, config: dict | None = None) -> Step`
Add a step to a workflow.

**Parameters:**
- `workflow`: Workflow to add step to
- `name`: Step name
- `tool`: Tool name to use (mutually exclusive with code)
- `code`: Inline Python code (mutually exclusive with tool)
- `config`: Configuration dict (maps to step inputs)

**Returns:** `Step` object

**Raises:** `ValueError` if neither or both tool and code are provided

### Models

#### `Tool`
Represents a tool with its metadata.

**Attributes:**
- `name: str` - Tool name
- `description: str` - Tool description
- `version: str` - Tool version
- `operations: list[str]` - List of operations (derived from inputs)
- `path: Path` - Filesystem path to tool directory

#### `Workflow`
Represents a workflow with its metadata and steps.

**Attributes:**
- `id: str` - Unique workflow ID
- `name: str` - Human-readable name
- `path: Path` - Filesystem path to workflow directory
- `status: WorkflowStatus` - Lifecycle status (DRAFT, GENERATED, TESTED, PUBLISHED)
- `description: WorkflowDescription` - Intent and I/O definitions
- `steps: list[StepDefinition]` - Workflow steps
- `version: str` - Workflow version

#### `Step`
Represents a workflow step.

**Attributes:**
- `id: str` - Unique step ID
- `name: str` - Step name
- `description: str` - Step description
- `tool: str` - Tool name
- `inputs: dict[str, Any]` - Input configuration

## Clean Architecture

The SDK follows clean architecture principles:
- **Separation of Concerns**: SDK layer is separate from CLI and core logic
- **Dependency Injection**: Delegates to existing `raw.discovery.workflow` functions
- **Type Safety**: Full type hints with Pydantic models
- **Immutability**: Models are immutable by default

## Testing

Comprehensive test suite with 47 tests covering all functionality:

```bash
uv run pytest tests/raw_sdk/ -v
```

All tests use temporary directories and proper mocking to avoid side effects.

Test coverage:
- Tool SDK: 91% coverage (24 tests)
- Workflow SDK: 100% coverage (23 tests)

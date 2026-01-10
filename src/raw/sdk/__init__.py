"""RAW Python SDK for programmatic workflow construction.

This SDK provides a clean, typed API for creating and managing workflows
and tools programmatically instead of via CLI commands.

Example:
    >>> from raw.sdk import create_workflow, add_step, create_tool
    >>> # Create a tool
    >>> tool = create_tool(
    ...     name="stock_fetcher",
    ...     description="Fetch real-time stock prices from Yahoo Finance"
    ... )
    >>> # Create a workflow
    >>> workflow = create_workflow(
    ...     name="stock-analysis",
    ...     intent="Fetch TSLA stock data and generate report"
    ... )
    >>> add_step(
    ...     workflow,
    ...     name="fetch-data",
    ...     tool="stock_fetcher",
    ...     config={"ticker": "TSLA"}
    ... )
"""

from raw.sdk.models import Step, Tool, Workflow
from raw.sdk.tools import (
    ToolNotFoundError,
    create_tool,
    delete_tool,
    get_tool,
    list_tools,
    update_tool,
)
from raw.sdk.workflow import (
    WorkflowNotFoundError,
    add_step,
    create_workflow,
    delete_workflow,
    get_workflow,
    list_workflows,
    update_workflow,
)

__all__ = [
    "Step",
    "Tool",
    "Workflow",
    "ToolNotFoundError",
    "WorkflowNotFoundError",
    "add_step",
    "create_tool",
    "create_workflow",
    "delete_tool",
    "delete_workflow",
    "get_tool",
    "get_workflow",
    "list_tools",
    "list_workflows",
    "update_tool",
    "update_workflow",
]

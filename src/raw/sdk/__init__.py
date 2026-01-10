"""RAW Python SDK for programmatic workflow construction.

This SDK provides a clean, typed API for creating and managing workflows
programmatically instead of via CLI commands.

Example:
    >>> from raw.sdk import create_workflow, add_step
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

from raw.sdk.models import Step, Workflow
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
    "Workflow",
    "WorkflowNotFoundError",
    "add_step",
    "create_workflow",
    "delete_workflow",
    "get_workflow",
    "list_workflows",
    "update_workflow",
]

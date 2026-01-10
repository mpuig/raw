"""SDK functions for programmatic workflow construction."""

import shutil
import uuid
from pathlib import Path
from typing import Any

from raw.core.schemas import (
    StepDefinition,
    WorkflowConfig,
)
from raw.discovery.workflow import (
    create_draft_workflow as _create_draft_workflow,
)
from raw.discovery.workflow import (
    find_workflow as _find_workflow,
)
from raw.discovery.workflow import (
    list_workflows as _list_workflows,
)
from raw.scaffold.init import (
    load_workflow_config,
    save_workflow_config,
)
from raw.sdk.models import Step, Workflow


class WorkflowNotFoundError(Exception):
    """Raised when a workflow cannot be found."""


def _workflow_config_to_model(config: WorkflowConfig, path: Path) -> Workflow:
    """Convert WorkflowConfig to SDK Workflow model."""
    return Workflow(
        id=config.id,
        name=config.name,
        path=path,
        status=config.status,
        description=config.description,
        steps=config.steps,
        version=config.version,
    )


def _load_workflow_model(workflow_path: Path) -> Workflow:
    """Load workflow config and convert to SDK model."""
    config = load_workflow_config(workflow_path)
    if not config:
        raise ValueError(f"Could not load workflow config from {workflow_path}")
    return _workflow_config_to_model(config, workflow_path)


def create_workflow(
    name: str,
    intent: str | None = None,
    description: str | None = None,  # noqa: ARG001
) -> Workflow:
    """Create a new workflow programmatically.

    Args:
        name: Human-readable workflow name
        intent: Natural language description of what the workflow does
        description: Optional additional description (currently unused, for API compatibility)

    Returns:
        Workflow object with metadata and path
    """
    if intent is None:
        intent = f"Scaffold workflow: {name}"

    workflow_dir, config = _create_draft_workflow(name, intent)
    return _workflow_config_to_model(config, workflow_dir)


def list_workflows() -> list[Workflow]:
    """List all workflows in the project.

    Returns:
        List of Workflow objects
    """
    workflow_dicts = _list_workflows()
    workflows = []

    for wf_dict in workflow_dicts:
        path = Path(wf_dict["path"])
        try:
            workflow = _load_workflow_model(path)
            workflows.append(workflow)
        except (ValueError, KeyError):
            # Skip workflows with invalid configs
            continue

    return workflows


def get_workflow(workflow_id: str) -> Workflow | None:
    """Get a workflow by ID or partial match.

    Args:
        workflow_id: Full or partial workflow ID

    Returns:
        Workflow object or None if not found
    """
    workflow_path = _find_workflow(workflow_id)
    if not workflow_path:
        return None

    try:
        return _load_workflow_model(workflow_path)
    except ValueError:
        return None


def update_workflow(workflow: Workflow, **kwargs: Any) -> Workflow:
    """Update workflow metadata.

    Args:
        workflow: Workflow to update
        **kwargs: Fields to update (name, intent, status, etc.)

    Returns:
        Updated Workflow object
    """
    config = load_workflow_config(workflow.path)
    if not config:
        raise WorkflowNotFoundError(f"Workflow not found: {workflow.id}")

    # Update fields
    if "name" in kwargs:
        config.name = kwargs["name"]
    if "intent" in kwargs:
        config.description.intent = kwargs["intent"]
    if "status" in kwargs:
        config.status = kwargs["status"]
    if "version" in kwargs:
        config.version = kwargs["version"]

    save_workflow_config(workflow.path, config)

    return _workflow_config_to_model(config, workflow.path)


def delete_workflow(workflow: Workflow) -> None:
    """Delete a workflow and all its files.

    Args:
        workflow: Workflow to delete

    Raises:
        WorkflowNotFoundError: If workflow directory doesn't exist
    """
    if not workflow.path.exists():
        raise WorkflowNotFoundError(f"Workflow not found: {workflow.id}")

    shutil.rmtree(workflow.path)


def add_step(
    workflow: Workflow,
    name: str,
    code: str | None = None,
    tool: str | None = None,
    config: dict[str, Any] | None = None,
) -> Step:
    """Add a step to a workflow.

    Args:
        workflow: Workflow to add step to
        name: Step name
        code: Optional inline Python code for the step
        tool: Optional tool name to use
        config: Optional configuration dict (maps to step inputs)

    Returns:
        Step object

    Raises:
        ValueError: If neither tool nor code is provided, or both are provided
    """
    if tool is None and code is None:
        raise ValueError("Either tool or code must be provided")

    if tool is not None and code is not None:
        raise ValueError("Cannot specify both tool and code")

    wf_config = load_workflow_config(workflow.path)
    if not wf_config:
        raise WorkflowNotFoundError(f"Workflow not found: {workflow.id}")

    # Generate step ID
    step_id = f"step-{uuid.uuid4().hex[:8]}"

    # Create step definition
    if tool is not None:
        description = f"Execute {tool}"
        step_def = StepDefinition(
            id=step_id,
            name=name,
            description=description,
            tool=tool,
            inputs=config or {},
        )
    else:
        # Code-based step (create inline tool reference)
        description = f"Custom code: {name}"
        step_def = StepDefinition(
            id=step_id,
            name=name,
            description=description,
            tool="__inline__",
            inputs={"code": code},
        )

    wf_config.steps.append(step_def)
    save_workflow_config(workflow.path, wf_config)

    # Return SDK Step model
    return Step(
        id=step_def.id,
        name=step_def.name,
        description=step_def.description,
        tool=step_def.tool,
        inputs=step_def.inputs,
    )

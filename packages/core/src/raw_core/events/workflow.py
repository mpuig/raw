"""Workflow events for agent execution tracking."""

from typing import Any

from raw_core.events.base import Event


class StepStarted(Event):
    """Emitted when a workflow step begins execution."""

    workflow_id: str
    step_name: str
    step_index: int


class StepCompleted(Event):
    """Emitted when a workflow step completes."""

    workflow_id: str
    step_name: str
    step_index: int
    result: Any = None
    error: str | None = None


class WorkflowStarted(Event):
    """Emitted when a workflow begins execution."""

    workflow_id: str
    workflow_name: str


class WorkflowCompleted(Event):
    """Emitted when a workflow completes."""

    workflow_id: str
    workflow_name: str
    success: bool
    error: str | None = None

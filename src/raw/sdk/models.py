"""SDK data models for programmatic workflow construction."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from raw.core.schemas import StepDefinition, WorkflowDescription, WorkflowStatus


class Workflow(BaseModel):
    """Represents a workflow with its metadata and steps."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    name: str
    path: Path
    status: WorkflowStatus
    description: WorkflowDescription
    steps: list[StepDefinition] = Field(default_factory=list)
    version: str = "1.0.0"


class Step(BaseModel):
    """Represents a workflow step."""

    id: str
    name: str
    description: str
    tool: str
    inputs: dict[str, Any] = Field(default_factory=dict)

"""Pydantic models for RAW runtime.

These models define the structure of workflow execution data,
including step results, artifacts, and the manifest format.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    """Status of a workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunStatus(str, Enum):
    """Status of a workflow run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CRASHED = "crashed"  # Process terminated unexpectedly


class StepResult(BaseModel):
    """Result of a single workflow step execution."""

    name: str = Field(..., description="Step name from @raw_step decorator")
    status: StepStatus = Field(..., description="Execution status")
    started_at: datetime = Field(..., description="When step started")
    ended_at: datetime | None = Field(default=None, description="When step ended")
    duration_seconds: float | None = Field(default=None, description="Execution duration")
    retries: int = Field(default=0, description="Number of retry attempts")
    cached: bool = Field(default=False, description="Whether result was from cache")
    result: Any = Field(default=None, description="Return value from step function")
    error: str | None = Field(default=None, description="Error message if failed")


class Artifact(BaseModel):
    """A file or output produced by the workflow."""

    type: str = Field(..., description="Artifact type (chart, report, data, etc.)")
    path: str = Field(..., description="Relative path to artifact file")
    size_bytes: int | None = Field(default=None, description="File size in bytes")


class WorkflowInfo(BaseModel):
    """Metadata about the workflow definition."""

    id: str = Field(..., description="Unique workflow ID (yyyymmdd-name-uuid)")
    short_name: str = Field(..., description="Human-readable short name")
    version: str = Field(default="1.0.0", description="Workflow version")
    created_at: datetime = Field(..., description="When workflow was created")


class EnvironmentInfo(BaseModel):
    """Information about the execution environment."""

    hostname: str = Field(..., description="Machine hostname")
    python_version: str = Field(..., description="Python version")
    raw_version: str = Field(default="0.1.0", description="RAW version")
    working_directory: str = Field(..., description="Working directory path")


class RunInfo(BaseModel):
    """Information about a specific workflow run."""

    run_id: str = Field(..., description="Unique run ID")
    workflow_id: str = Field(..., description="Parent workflow ID")
    started_at: datetime = Field(..., description="When run started")
    ended_at: datetime | None = Field(default=None, description="When run ended")
    status: RunStatus = Field(default=RunStatus.PENDING, description="Run status")
    duration_seconds: float | None = Field(default=None, description="Total duration")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Input parameters")
    environment: EnvironmentInfo | None = Field(default=None, description="Environment info")


class LogsInfo(BaseModel):
    """Paths to log files."""

    stdout: str | None = Field(default=None, description="Path to stdout log")
    stderr: str | None = Field(default=None, description="Path to stderr log")


class ToolMetadata(BaseModel):
    """Metadata about a registered tool for introspection."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    operations: list[str] = Field(default_factory=list, description="Available operations")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parameter schemas")
    version: str | None = Field(default=None, description="Tool version")
    documentation: str | None = Field(default=None, description="Detailed documentation")
    triggers: list[str] = Field(
        default_factory=list, description="Event triggers this tool handles"
    )


class ProvenanceInfo(BaseModel):
    """Provenance metadata for a workflow run."""

    git_sha: str | None = Field(default=None, description="Git commit SHA")
    git_branch: str | None = Field(default=None, description="Git branch")
    git_dirty: bool = Field(default=False, description="Uncommitted changes present")
    workflow_hash: str | None = Field(default=None, description="Workflow file hash")
    tool_versions: dict[str, str] = Field(
        default_factory=dict, description="Tool name to version hash"
    )
    config_snapshot: dict[str, Any] = Field(
        default_factory=dict, description="Config at run time (secrets redacted)"
    )
    resumed_from: str | None = Field(default=None, description="Previous run ID if resumed")


class Manifest(BaseModel):
    """Complete manifest for a workflow run.

    This is the canonical format for tracking workflow execution.
    It serves as the contract between:
    - Local storage (.raw/manifest.json)
    - Future RAW Server API
    - Agent queries
    """

    schema_version: str = Field(default="1.0.0", description="Manifest schema version")
    workflow: WorkflowInfo = Field(..., description="Workflow metadata")
    run: RunInfo = Field(..., description="Run details")
    steps: list[StepResult] = Field(default_factory=list, description="Step results")
    artifacts: list[Artifact] = Field(default_factory=list, description="Generated artifacts")
    logs: LogsInfo = Field(default_factory=LogsInfo, description="Log file paths")
    provenance: ProvenanceInfo | None = Field(default=None, description="Provenance metadata")
    error: str | None = Field(default=None, description="Top-level error if run failed")

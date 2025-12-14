"""Server models for RAW daemon mode.

Pydantic models for request/response payloads and registry state.
Separated from server.py for better testability and SRP.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


# --- Request/Response Models ---


class WorkflowTriggerRequest(BaseModel):
    """Request body for triggering a workflow."""

    args: list[str] = []


class ApprovalRequest(BaseModel):
    """Request body for approving/rejecting a step."""

    decision: str = "approve"


class RegisterRequest(BaseModel):
    """Request body for workflow registration."""

    run_id: str
    workflow_id: str
    pid: int


class WaitingRequest(BaseModel):
    """Request body for marking a run as waiting."""

    event_type: Literal["approval", "webhook"] = "approval"
    step_name: str
    prompt: str | None = None
    options: list[str] | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 300


class CompleteRequest(BaseModel):
    """Request body for marking a run as complete."""

    status: Literal["success", "failed"] = "success"
    error: str | None = None


# --- Registry Models ---


class WaitingState(BaseModel):
    """State for a run waiting for an event."""

    event_type: Literal["approval", "webhook"]
    step_name: str
    prompt: str | None = None
    options: list[str] | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    timeout_at: datetime


class Event(BaseModel):
    """Event delivered to a waiting run."""

    event_type: Literal["approval", "webhook"]
    step_name: str
    payload: dict[str, Any]
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConnectedRun(BaseModel):
    """State for a connected workflow run."""

    run_id: str
    workflow_id: str
    pid: int
    status: Literal["running", "waiting", "completed", "failed", "stale"] = "running"
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    waiting_for: WaitingState | None = None


# --- Legacy Models (for subprocess-based runs) ---


class WorkflowRun(BaseModel):
    """Active workflow run state (subprocess mode)."""

    workflow_id: str
    run_id: str
    started_at: datetime
    process: asyncio.subprocess.Process | None = None
    status: str = "running"

    model_config = {"arbitrary_types_allowed": True}

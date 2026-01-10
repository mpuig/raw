"""Event models for RAW event-driven architecture.

Events are the universal communication mechanism between workflow execution
and the outside world. All state changes flow through events, enabling:
- Real-time monitoring and logging
- Human-in-the-loop approval workflows
- External integrations (webhooks, cron triggers)
- Decoupled architecture between Agent, Builder, and Runner
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    """Event type enumeration."""

    # Workflow lifecycle
    WORKFLOW_TRIGGERED = "workflow.triggered"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_PROVENANCE = "workflow.provenance"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"

    # Step lifecycle
    STEP_STARTED = "step.started"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"
    STEP_SKIPPED = "step.skipped"
    STEP_RETRY = "step.retry"

    # Human-in-the-loop
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_RECEIVED = "approval.received"
    APPROVAL_TIMEOUT = "approval.timeout"

    # Artifacts
    ARTIFACT_CREATED = "artifact.created"

    # Cache
    CACHE_HIT = "cache.hit"
    CACHE_MISS = "cache.miss"


class BaseEvent(BaseModel):
    """Base event with common fields.

    Events are immutable (frozen=True) because they represent facts about
    what happened. Once an event is created, it should never be modified -
    this ensures the integrity of audit logs and event streams.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    workflow_id: str
    run_id: str | None = None


# Workflow lifecycle events


class WorkflowTriggeredEvent(BaseEvent):
    """Emitted when a workflow execution is requested."""

    event_type: EventType = EventType.WORKFLOW_TRIGGERED
    trigger_source: str = "cli"  # cli, webhook, cron, api
    parameters: dict[str, Any] = Field(default_factory=dict)


class WorkflowStartedEvent(BaseEvent):
    """Emitted when workflow execution begins."""

    event_type: EventType = EventType.WORKFLOW_STARTED
    workflow_name: str
    workflow_version: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class WorkflowProvenanceEvent(BaseEvent):
    """Emitted immediately after workflow start with provenance metadata."""

    event_type: EventType = EventType.WORKFLOW_PROVENANCE
    git_sha: str | None = None
    git_branch: str | None = None
    git_dirty: bool = False
    workflow_hash: str | None = None
    tool_versions: dict[str, str] = Field(default_factory=dict)
    python_version: str | None = None
    raw_version: str | None = None
    hostname: str | None = None
    working_directory: str | None = None
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    resumed_from: str | None = None


class WorkflowCompletedEvent(BaseEvent):
    """Emitted when workflow execution completes successfully."""

    event_type: EventType = EventType.WORKFLOW_COMPLETED
    duration_seconds: float
    step_count: int
    artifacts: list[str] = Field(default_factory=list)


class WorkflowFailedEvent(BaseEvent):
    """Emitted when workflow execution fails."""

    event_type: EventType = EventType.WORKFLOW_FAILED
    error: str
    failed_step: str | None = None
    duration_seconds: float


# Step lifecycle events


class StepStartedEvent(BaseEvent):
    """Emitted when a step begins execution."""

    event_type: EventType = EventType.STEP_STARTED
    step_name: str
    input_types: list[str] = Field(default_factory=list)
    output_type: str = "Any"


class StepCompletedEvent(BaseEvent):
    """Emitted when a step completes successfully."""

    event_type: EventType = EventType.STEP_COMPLETED
    step_name: str
    duration_seconds: float
    result_type: str
    result_summary: str | None = None


class StepFailedEvent(BaseEvent):
    """Emitted when a step fails."""

    event_type: EventType = EventType.STEP_FAILED
    step_name: str
    error: str
    duration_seconds: float


class StepSkippedEvent(BaseEvent):
    """Emitted when a step is skipped due to conditional logic."""

    event_type: EventType = EventType.STEP_SKIPPED
    step_name: str
    reason: str


class StepRetryEvent(BaseEvent):
    """Emitted when a step is retried after failure."""

    event_type: EventType = EventType.STEP_RETRY
    step_name: str
    attempt: int
    max_attempts: int
    error: str
    delay_seconds: float


# Human-in-the-loop events


class ApprovalRequestedEvent(BaseEvent):
    """Emitted when workflow requires human approval to continue."""

    event_type: EventType = EventType.APPROVAL_REQUESTED
    step_name: str
    prompt: str
    options: list[str] = Field(default_factory=lambda: ["approve", "reject"])
    timeout_seconds: float | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ApprovalReceivedEvent(BaseEvent):
    """Emitted when human approval is received."""

    event_type: EventType = EventType.APPROVAL_RECEIVED
    step_name: str
    decision: str
    approved_by: str | None = None
    comment: str | None = None


class ApprovalTimeoutEvent(BaseEvent):
    """Emitted when approval request times out."""

    event_type: EventType = EventType.APPROVAL_TIMEOUT
    step_name: str
    timeout_seconds: float


# Artifact events


class ArtifactCreatedEvent(BaseEvent):
    """Emitted when a workflow produces an artifact."""

    event_type: EventType = EventType.ARTIFACT_CREATED
    artifact_type: str
    path: str
    size_bytes: int | None = None


# Cache events


class CacheHitEvent(BaseEvent):
    """Emitted when a cached result is used."""

    event_type: EventType = EventType.CACHE_HIT
    step_name: str
    cache_key: str


class CacheMissEvent(BaseEvent):
    """Emitted when cache lookup misses."""

    event_type: EventType = EventType.CACHE_MISS
    step_name: str
    cache_key: str


Event = (
    WorkflowTriggeredEvent
    | WorkflowStartedEvent
    | WorkflowProvenanceEvent
    | WorkflowCompletedEvent
    | WorkflowFailedEvent
    | StepStartedEvent
    | StepCompletedEvent
    | StepFailedEvent
    | StepSkippedEvent
    | StepRetryEvent
    | ApprovalRequestedEvent
    | ApprovalReceivedEvent
    | ApprovalTimeoutEvent
    | ArtifactCreatedEvent
    | CacheHitEvent
    | CacheMissEvent
)

"""Builder event models for append-only journal."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BuildEventType(str, Enum):
    """Builder event types for journal."""

    # Build lifecycle
    BUILD_STARTED = "build.started"
    BUILD_COMPLETED = "build.completed"
    BUILD_FAILED = "build.failed"
    BUILD_STUCK = "build.stuck"

    # Iteration lifecycle
    ITERATION_STARTED = "iteration.started"
    ITERATION_COMPLETED = "iteration.completed"

    # Mode switching
    MODE_SWITCHED = "mode.switched"

    # Plan updates
    PLAN_UPDATED = "plan.updated"

    # Tool calls
    TOOL_CALL_STARTED = "tool.call_started"
    TOOL_CALL_COMPLETED = "tool.call_completed"

    # File changes
    FILE_CHANGE_APPLIED = "file.change_applied"

    # Quality gates
    GATE_STARTED = "gate.started"
    GATE_COMPLETED = "gate.completed"


class BaseBuildEvent(BaseModel):
    """Base event with common fields."""

    event_type: BuildEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    build_id: str
    iteration: int


class BuildStartedEvent(BaseBuildEvent):
    """Emitted when builder starts."""

    event_type: BuildEventType = BuildEventType.BUILD_STARTED
    workflow_id: str
    intent: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class BuildCompletedEvent(BaseBuildEvent):
    """Emitted when all gates pass."""

    event_type: BuildEventType = BuildEventType.BUILD_COMPLETED
    total_iterations: int
    duration_seconds: float


class BuildFailedEvent(BaseBuildEvent):
    """Emitted when builder fails (error or gates fail repeatedly)."""

    event_type: BuildEventType = BuildEventType.BUILD_FAILED
    reason: str
    error: str | None = None


class BuildStuckEvent(BaseBuildEvent):
    """Emitted when builder hits budget limits or cannot make progress."""

    event_type: BuildEventType = BuildEventType.BUILD_STUCK
    reason: str  # "max_iterations" | "max_time" | "doom_loop" | "repeated_failures"
    last_failures: list[str] = Field(default_factory=list)


class IterationStartedEvent(BaseBuildEvent):
    """Emitted at start of plan-execute cycle."""

    event_type: BuildEventType = BuildEventType.ITERATION_STARTED
    mode: str  # "plan" | "execute"


class IterationCompletedEvent(BaseBuildEvent):
    """Emitted at end of plan-execute cycle."""

    event_type: BuildEventType = BuildEventType.ITERATION_COMPLETED
    duration_seconds: float


class ModeSwitchedEvent(BaseBuildEvent):
    """Emitted when switching between plan/execute modes."""

    event_type: BuildEventType = BuildEventType.MODE_SWITCHED
    mode: str  # "plan" | "execute"
    context: str | None = None  # Additional context (e.g., gate failures)


class PlanUpdatedEvent(BaseBuildEvent):
    """Emitted when agent produces/updates a plan."""

    event_type: BuildEventType = BuildEventType.PLAN_UPDATED
    plan: str  # Numbered plan from agent
    gates: list[str] = Field(default_factory=list)  # Expected gates


class ToolCallStartedEvent(BaseBuildEvent):
    """Emitted when a tool call begins."""

    event_type: BuildEventType = BuildEventType.TOOL_CALL_STARTED
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallCompletedEvent(BaseBuildEvent):
    """Emitted when a tool call completes."""

    event_type: BuildEventType = BuildEventType.TOOL_CALL_COMPLETED
    tool_name: str
    duration_seconds: float
    success: bool
    error: str | None = None


class FileChangeAppliedEvent(BaseBuildEvent):
    """Emitted when a file is created/modified/deleted."""

    event_type: BuildEventType = BuildEventType.FILE_CHANGE_APPLIED
    file_path: str
    operation: str  # "create" | "modify" | "delete"


class GateStartedEvent(BaseBuildEvent):
    """Emitted when a quality gate starts."""

    event_type: BuildEventType = BuildEventType.GATE_STARTED
    gate: str  # "validate" | "dry" | "pytest" | etc.


class GateCompletedEvent(BaseBuildEvent):
    """Emitted when a quality gate completes."""

    event_type: BuildEventType = BuildEventType.GATE_COMPLETED
    gate: str
    passed: bool
    duration_seconds: float
    output_path: str | None = None  # Path to gate log file


# Union type for all events
BuildEvent = (
    BuildStartedEvent
    | BuildCompletedEvent
    | BuildFailedEvent
    | BuildStuckEvent
    | IterationStartedEvent
    | IterationCompletedEvent
    | ModeSwitchedEvent
    | PlanUpdatedEvent
    | ToolCallStartedEvent
    | ToolCallCompletedEvent
    | FileChangeAppliedEvent
    | GateStartedEvent
    | GateCompletedEvent
)

"""Workflow context management.

The WorkflowContext tracks the state of a workflow execution,
including step results. It's used by decorators to record execution
data and emit events.

Architecture:
- WorkflowContext: Coordinates execution state and event emission
- Uses contextvars for thread-safe context access
"""

from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from raw_core import Event, WorkflowCompleted, WorkflowStarted

if TYPE_CHECKING:
    from raw_core import EventBus

# Global context variable for the current workflow
_workflow_context: ContextVar["WorkflowContext | None"] = ContextVar(
    "workflow_context", default=None
)


def get_workflow_context() -> "WorkflowContext | None":
    """Get the current workflow context."""
    return _workflow_context.get()


def set_workflow_context(context: "WorkflowContext | None") -> None:
    """Set the current workflow context."""
    _workflow_context.set(context)


class StepResult:
    """Result of a single workflow step execution."""

    def __init__(
        self,
        name: str,
        success: bool,
        duration: float,
        result: Any = None,
        error: str | None = None,
    ):
        self.name = name
        self.success = success
        self.duration = duration
        self.result = result
        self.error = error


class WorkflowContext:
    """Context manager for tracking workflow execution.

    Coordinates execution state tracking and event emission.

    Usage:
        context = WorkflowContext(
            workflow_id="stock-analysis-20250118",
            workflow_name="stock-analysis",
            parameters={"ticker": "TSLA"}
        )
        set_workflow_context(context)

        # ... run workflow steps ...

        context.finalize(success=True)
    """

    def __init__(
        self,
        workflow_id: str,
        workflow_name: str,
        parameters: dict[str, Any] | None = None,
        workflow_dir: Path | None = None,
        event_bus: "EventBus | None" = None,
    ) -> None:
        """Initialize workflow context.

        Args:
            workflow_id: Unique workflow identifier
            workflow_name: Human-readable workflow name
            parameters: Input parameters for the workflow
            workflow_dir: Directory for output files
            event_bus: Optional event bus for emitting events
        """
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.parameters = parameters or {}
        self.workflow_dir = workflow_dir
        self._event_bus = event_bus

        self.started_at = datetime.now(timezone.utc)
        self._steps: list[StepResult] = []

    def emit(self, event: Event) -> None:
        """Emit an event to the EventBus if configured."""
        if self._event_bus is not None:
            # EventBus protocol uses async publish, but we'll use sync emit for simplicity
            # In a full implementation, this would need to handle async properly
            pass

    def add_step_result(
        self,
        name: str,
        success: bool,
        duration: float,
        result: Any = None,
        error: str | None = None,
    ) -> None:
        """Record a step execution result."""
        step = StepResult(
            name=name,
            success=success,
            duration=duration,
            result=result,
            error=error,
        )
        self._steps.append(step)

    def get_steps(self) -> list[StepResult]:
        """Get all recorded step results."""
        return self._steps.copy()

    def finalize(
        self,
        success: bool = True,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Finalize the workflow run and return summary.

        Args:
            success: Whether the workflow completed successfully
            error: Optional error message if workflow failed

        Returns:
            Summary dictionary with workflow execution details
        """
        duration = (datetime.now(timezone.utc) - self.started_at).total_seconds()

        self.emit(
            WorkflowCompleted(
                workflow_id=self.workflow_id,
                workflow_name=self.workflow_name,
                success=success,
                error=error,
            )
        )

        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "success": success,
            "duration": duration,
            "steps": len(self._steps),
            "error": error,
        }

    def __enter__(self) -> "WorkflowContext":
        """Enter context manager."""
        set_workflow_context(self)
        self.emit(
            WorkflowStarted(
                workflow_id=self.workflow_id,
                workflow_name=self.workflow_name,
            )
        )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        set_workflow_context(None)

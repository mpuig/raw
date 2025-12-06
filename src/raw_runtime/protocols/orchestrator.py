"""Orchestrator protocol definition."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class OrchestratorRunStatus(str, Enum):
    """Status of a workflow run."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class OrchestratorRunInfo:
    """Information about a workflow run."""

    run_id: str
    workflow_id: str
    status: OrchestratorRunStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    exit_code: int | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ended_at(self) -> datetime | None:
        """Alias for completed_at for backwards compatibility."""
        return self.completed_at


@runtime_checkable
class Orchestrator(Protocol):
    """Protocol for workflow orchestrators.

    Implementations handle the mechanics of triggering workflows
    and tracking their execution status.
    """

    def trigger(
        self,
        workflow_id: str,
        args: list[str] | None = None,
        wait: bool = False,
        timeout_seconds: float | None = None,
    ) -> OrchestratorRunInfo:
        """Trigger a workflow execution.

        Args:
            workflow_id: ID of workflow to run
            args: Command-line arguments to pass
            wait: If True, block until workflow completes
            timeout_seconds: Maximum wait time (only if wait=True)

        Returns:
            Run information including status
        """
        ...

    def get_status(self, run_id: str) -> OrchestratorRunInfo:
        """Get the current status of a workflow run.

        Args:
            run_id: Unique identifier for the run

        Returns:
            Run information including current status

        Raises:
            ValueError: If run not found
        """
        ...

    def wait_for_completion(
        self,
        run_id: str,
        timeout_seconds: float | None = None,
        poll_interval: float = 1.0,
    ) -> OrchestratorRunInfo:
        """Wait for a workflow run to complete.

        Args:
            run_id: Unique identifier for the run
            timeout_seconds: Maximum time to wait
            poll_interval: Time between status checks

        Returns:
            Final run information

        Raises:
            TimeoutError: If timeout exceeded
            ValueError: If run not found
        """
        ...

    def list_runs(
        self,
        workflow_id: str | None = None,
        status: OrchestratorRunStatus | None = None,
        limit: int = 100,
    ) -> list[OrchestratorRunInfo]:
        """List workflow runs with optional filtering.

        Args:
            workflow_id: Filter by workflow ID
            status: Filter by status
            limit: Maximum number of runs to return

        Returns:
            List of run information
        """
        ...

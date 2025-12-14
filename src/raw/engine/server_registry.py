"""Run registry for connected workflow management.

Tracks connected workflow runs and their state, enabling:
- Run registration and lifecycle management
- Approval and webhook event delivery
- Heartbeat-based health monitoring
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from raw.engine.server_models import ConnectedRun, Event, WaitingState


class RunRegistry:
    """Registry for connected workflow runs.

    Manages the lifecycle of workflow runs that connect back to the server.
    Supports approval workflows and webhook event delivery.
    """

    def __init__(self) -> None:
        self.runs: dict[str, ConnectedRun] = {}
        self.events: dict[str, list[Event]] = {}

    def register(self, run_id: str, workflow_id: str, pid: int) -> ConnectedRun:
        """Register a new connected run."""
        run = ConnectedRun(run_id=run_id, workflow_id=workflow_id, pid=pid)
        self.runs[run_id] = run
        self.events[run_id] = []
        return run

    def get(self, run_id: str) -> ConnectedRun | None:
        """Get a run by ID."""
        return self.runs.get(run_id)

    def mark_waiting(
        self,
        run_id: str,
        event_type: Literal["approval", "webhook"],
        step_name: str,
        prompt: str | None = None,
        options: list[str] | None = None,
        context: dict[str, Any] | None = None,
        timeout_seconds: float = 300,
    ) -> None:
        """Mark a run as waiting for an event."""
        run = self.runs.get(run_id)
        if run:
            run.status = "waiting"
            run.waiting_for = WaitingState(
                event_type=event_type,
                step_name=step_name,
                prompt=prompt,
                options=options,
                context=context or {},
                timeout_at=datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds),
            )

    def heartbeat(self, run_id: str) -> bool:
        """Update heartbeat timestamp. Returns False if run not found."""
        run = self.runs.get(run_id)
        if run:
            run.last_heartbeat = datetime.now(timezone.utc)
            if run.status == "stale":
                run.status = "running"
            return True
        return False

    def complete(self, run_id: str, status: Literal["success", "failed"] = "success") -> None:
        """Mark a run as completed."""
        run = self.runs.get(run_id)
        if run:
            run.status = "completed" if status == "success" else "failed"
            run.waiting_for = None

    def unregister(self, run_id: str) -> None:
        """Remove a run from the registry."""
        self.runs.pop(run_id, None)
        self.events.pop(run_id, None)

    def push_event(self, run_id: str, event: Event) -> bool:
        """Push an event to a run's queue. Returns False if run not found."""
        if run_id not in self.events:
            return False
        self.events[run_id].append(event)
        return True

    def pop_events(self, run_id: str) -> list[Event]:
        """Pop and return all pending events for a run."""
        events = self.events.get(run_id, [])
        self.events[run_id] = []
        return events

    def list_runs(self) -> list[ConnectedRun]:
        """List all connected runs."""
        return list(self.runs.values())

    def list_waiting(self) -> list[tuple[str, WaitingState]]:
        """List all runs waiting for events."""
        return [
            (run_id, run.waiting_for)
            for run_id, run in self.runs.items()
            if run.waiting_for is not None
        ]

"""Manifest reducer - rebuild manifest from event journal.

Implements event sourcing pattern: fold events.jsonl → manifest.json
Enables crash recovery by reconstructing manifests from event history.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from raw_runtime.journal import JournalReader
from raw_runtime.models import (
    Artifact,
    EnvironmentInfo,
    LogsInfo,
    Manifest,
    ProvenanceInfo,
    RunInfo,
    RunStatus,
    StepResult,
    StepStatus,
    WorkflowInfo,
)


def _parse_timestamp(timestamp_str: str | None) -> datetime:
    """Parse ISO timestamp with variable microsecond precision.

    Handles timestamps like:
    - 2025-01-10T12:00:00Z
    - 2025-01-10T12:00:00.5Z  (pad to 500000 microseconds)
    - 2025-01-10T12:00:00.123456Z

    Args:
        timestamp_str: ISO format timestamp string

    Returns:
        Parsed datetime with UTC timezone
    """
    if not timestamp_str:
        return datetime.now(timezone.utc)

    # Replace Z with +00:00 for Python compatibility
    ts = timestamp_str.replace("Z", "+00:00")

    # Pad microseconds to 6 digits if present
    # Match pattern: YYYY-MM-DDTHH:MM:SS.f+TZ where f is 1-5 digits
    match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\.(\d{1,5})([+-]\d{2}:\d{2})", ts)
    if match:
        date_part, microseconds, tz_part = match.groups()
        # Pad microseconds to 6 digits
        padded_microseconds = microseconds.ljust(6, "0")
        ts = f"{date_part}.{padded_microseconds}{tz_part}"

    return datetime.fromisoformat(ts)


class ManifestReducer:
    """Reduces event journal to manifest.

    Processes events in order, folding them into a Manifest object.
    Handles:
    - Step lifecycle: started → completed/failed/skipped
    - Artifact creation
    - Workflow completion
    - Partial/corrupt journals (graceful degradation)

    Usage:
        reducer = ManifestReducer()
        manifest = reducer.reduce_from_file(Path("events.jsonl"))
    """

    def __init__(self) -> None:
        """Initialize reducer with empty state."""
        self._workflow_id: str | None = None
        self._run_id: str | None = None
        self._workflow_name: str | None = None
        self._workflow_version: str | None = None
        self._parameters: dict[str, Any] = {}
        self._started_at: datetime | None = None
        self._ended_at: datetime | None = None
        self._status: RunStatus = RunStatus.RUNNING
        self._error: str | None = None
        self._environment: EnvironmentInfo | None = None

        # Track steps by name (step_name → StepResult)
        # Multiple events for same step (started, retries, completed/failed)
        self._steps: dict[str, StepResult] = {}
        self._artifacts: list[Artifact] = []
        self._provenance: dict[str, Any] | None = None

    def reduce_from_file(self, journal_path: Path) -> Manifest:
        """Reduce journal file to manifest.

        Args:
            journal_path: Path to events.jsonl

        Returns:
            Reconstructed Manifest

        Raises:
            ValueError: If journal is empty or missing required events
        """
        reader = JournalReader(journal_path)
        events = reader.read_events()

        if not events:
            raise ValueError(f"Journal is empty: {journal_path}")

        for event_data in events:
            self._process_event(event_data)

        return self._build_manifest()

    def reduce_from_events(self, events: list[dict]) -> Manifest:
        """Reduce list of events to manifest.

        Args:
            events: List of event dictionaries

        Returns:
            Reconstructed Manifest
        """
        if not events:
            raise ValueError("No events to reduce")

        for event_data in events:
            self._process_event(event_data)

        return self._build_manifest()

    def _process_event(self, event: dict) -> None:
        """Process a single event."""
        event_type = event.get("event_type")

        if event_type == "workflow.started":
            self._handle_workflow_started(event)
        elif event_type == "workflow.provenance":
            self._handle_workflow_provenance(event)
        elif event_type == "step.started":
            self._handle_step_started(event)
        elif event_type == "step.completed":
            self._handle_step_completed(event)
        elif event_type == "step.failed":
            self._handle_step_failed(event)
        elif event_type == "step.skipped":
            self._handle_step_skipped(event)
        elif event_type == "step.retry":
            self._handle_step_retry(event)
        elif event_type == "artifact.created":
            self._handle_artifact_created(event)
        elif event_type == "cache.hit":
            self._handle_cache_hit(event)
        elif event_type == "workflow.completed":
            self._handle_workflow_completed(event)
        elif event_type == "workflow.failed":
            self._handle_workflow_failed(event)
        # Other event types (approval, cache.miss, etc.) are logged but don't affect manifest

    def _handle_workflow_started(self, event: dict) -> None:
        """Handle workflow.started event."""
        self._workflow_id = event["workflow_id"]
        self._run_id = event["run_id"]
        self._workflow_name = event.get("workflow_name", self._workflow_id)
        self._workflow_version = event.get("workflow_version")
        self._parameters = event.get("parameters", {})

        # Parse timestamp
        self._started_at = _parse_timestamp(event.get("timestamp"))

        # Set initial status
        self._status = RunStatus.RUNNING

    def _handle_workflow_provenance(self, event: dict) -> None:
        """Handle workflow.provenance event."""
        self._provenance = {
            "git_sha": event.get("git_sha"),
            "git_branch": event.get("git_branch"),
            "git_dirty": event.get("git_dirty", False),
            "workflow_hash": event.get("workflow_hash"),
            "tool_versions": event.get("tool_versions", {}),
            "config_snapshot": event.get("config_snapshot", {}),
            "resumed_from": event.get("resumed_from"),
        }

    def _handle_step_started(self, event: dict) -> None:
        """Handle step.started event."""
        step_name = event["step_name"]
        started_at = _parse_timestamp(event.get("timestamp"))

        # Create or update step result
        self._steps[step_name] = StepResult(
            name=step_name,
            status=StepStatus.RUNNING,
            started_at=started_at,
        )

    def _handle_step_completed(self, event: dict) -> None:
        """Handle step.completed event."""
        step_name = event["step_name"]
        duration = event.get("duration_seconds", 0.0)
        ended_at = _parse_timestamp(event.get("timestamp"))

        # Get existing step or create new one (if no step.started event)
        step = self._steps.get(step_name)
        if step:
            # Update existing step
            self._steps[step_name] = StepResult(
                name=step.name,
                status=StepStatus.SUCCESS,
                started_at=step.started_at,
                ended_at=ended_at,
                duration_seconds=duration,
                retries=step.retries,
                cached=step.cached,
                result=step.result,
                error=None,
            )
        else:
            # Create new step (missing step.started)
            self._steps[step_name] = StepResult(
                name=step_name,
                status=StepStatus.SUCCESS,
                started_at=ended_at,
                ended_at=ended_at,
                duration_seconds=duration,
            )

    def _handle_step_failed(self, event: dict) -> None:
        """Handle step.failed event."""
        step_name = event["step_name"]
        error = event.get("error", "Unknown error")
        duration = event.get("duration_seconds", 0.0)
        ended_at = _parse_timestamp(event.get("timestamp"))

        # Get existing step or create new one
        step = self._steps.get(step_name)
        if step:
            self._steps[step_name] = StepResult(
                name=step.name,
                status=StepStatus.FAILED,
                started_at=step.started_at,
                ended_at=ended_at,
                duration_seconds=duration,
                retries=step.retries,
                cached=step.cached,
                result=step.result,
                error=error,
            )
        else:
            self._steps[step_name] = StepResult(
                name=step_name,
                status=StepStatus.FAILED,
                started_at=ended_at,
                ended_at=ended_at,
                duration_seconds=duration,
                error=error,
            )

    def _handle_step_skipped(self, event: dict) -> None:
        """Handle step.skipped event."""
        step_name = event["step_name"]
        reason = event.get("reason")
        timestamp = _parse_timestamp(event.get("timestamp"))

        self._steps[step_name] = StepResult(
            name=step_name,
            status=StepStatus.SKIPPED,
            started_at=timestamp,
            ended_at=timestamp,
            duration_seconds=0.0,
            error=reason,
        )

    def _handle_step_retry(self, event: dict) -> None:
        """Handle step.retry event - increment retry count."""
        step_name = event["step_name"]
        step = self._steps.get(step_name)

        if step:
            # Increment retry count
            self._steps[step_name] = StepResult(
                name=step.name,
                status=step.status,
                started_at=step.started_at,
                ended_at=step.ended_at,
                duration_seconds=step.duration_seconds,
                retries=step.retries + 1,
                cached=step.cached,
                result=step.result,
                error=step.error,
            )

    def _handle_cache_hit(self, event: dict) -> None:
        """Handle cache.hit event - mark step as cached."""
        step_name = event["step_name"]
        step = self._steps.get(step_name)

        if step:
            self._steps[step_name] = StepResult(
                name=step.name,
                status=step.status,
                started_at=step.started_at,
                ended_at=step.ended_at,
                duration_seconds=step.duration_seconds,
                retries=step.retries,
                cached=True,
                result=step.result,
                error=step.error,
            )

    def _handle_artifact_created(self, event: dict) -> None:
        """Handle artifact.created event."""
        artifact = Artifact(
            type=event.get("artifact_type", "unknown"),
            path=event["path"],
            size_bytes=event.get("size_bytes"),
        )
        self._artifacts.append(artifact)

    def _handle_workflow_completed(self, event: dict) -> None:
        """Handle workflow.completed event."""
        self._status = RunStatus.SUCCESS
        self._error = None
        self._ended_at = _parse_timestamp(event.get("timestamp"))

    def _handle_workflow_failed(self, event: dict) -> None:
        """Handle workflow.failed event."""
        error = event.get("error", "Unknown error")

        # Check if this is a crashed workflow (reconciliation marker)
        if error.startswith("CRASHED:"):
            self._status = RunStatus.CRASHED
            self._error = error[8:].strip()  # Remove "CRASHED: " prefix
        else:
            self._status = RunStatus.FAILED
            self._error = error

        self._ended_at = _parse_timestamp(event.get("timestamp"))

    def _build_manifest(self) -> Manifest:
        """Build final Manifest from accumulated state."""
        if not self._workflow_id or not self._run_id or not self._started_at:
            raise ValueError("Missing required workflow metadata (workflow.started event)")

        # Calculate duration
        ended_at = self._ended_at or datetime.now(timezone.utc)
        duration = (ended_at - self._started_at).total_seconds()

        # Build WorkflowInfo
        workflow_info = WorkflowInfo(
            id=self._workflow_id,
            short_name=self._workflow_name or self._workflow_id,
            version=self._workflow_version or "1.0.0",
            created_at=self._started_at,
        )

        # Build EnvironmentInfo (minimal if not provided)
        if not self._environment:
            self._environment = EnvironmentInfo(
                hostname="unknown",
                python_version="unknown",
                raw_version="0.1.0",
                working_directory="unknown",
            )

        # Build RunInfo
        run_info = RunInfo(
            run_id=self._run_id,
            workflow_id=self._workflow_id,
            started_at=self._started_at,
            ended_at=ended_at,
            status=self._status,
            duration_seconds=duration,
            parameters=self._parameters,
            environment=self._environment,
        )

        # Build logs info (minimal)
        logs = LogsInfo(
            stdout="output.log",  # Convention
        )

        # Convert steps dict to list (preserve insertion order)
        steps = list(self._steps.values())

        # Build provenance if available
        provenance_info = None
        if self._provenance:
            provenance_info = ProvenanceInfo(**self._provenance)

        return Manifest(
            schema_version="1.0.0",
            workflow=workflow_info,
            run=run_info,
            steps=steps,
            artifacts=self._artifacts,
            logs=logs,
            provenance=provenance_info,
            error=self._error,
        )


__all__ = ["ManifestReducer"]

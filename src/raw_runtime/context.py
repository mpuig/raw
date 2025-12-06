"""Workflow context management.

The WorkflowContext tracks the state of a workflow execution,
including step results and artifacts. It's used by decorators
to record execution data into the manifest.

With EventBus integration, the context emits events for all state
changes, enabling real-time monitoring and decoupled handlers.
"""

import socket
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from raw_runtime.models import (
    Artifact,
    EnvironmentInfo,
    LogsInfo,
    Manifest,
    RunInfo,
    RunStatus,
    StepResult,
    WorkflowInfo,
)

if TYPE_CHECKING:
    from raw_runtime.bus import EventBus

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


class WorkflowContext:
    """Context manager for tracking workflow execution.

    This class maintains the state of a running workflow and provides
    methods for decorators to record step results and artifacts.

    Usage:
        context = WorkflowContext(
            workflow_id="20250106-stock-analysis-a1b2c3",
            short_name="stock-analysis",
            parameters={"ticker": "TSLA"}
        )
        set_workflow_context(context)

        # ... run workflow steps ...

        context.finalize(status="success")
    """

    def __init__(
        self,
        workflow_id: str,
        short_name: str,
        parameters: dict[str, Any] | None = None,
        workflow_dir: Path | None = None,
        event_bus: "EventBus | None" = None,
        workflow_version: str | None = None,
    ) -> None:
        """Initialize workflow context."""
        self.workflow_id = workflow_id
        self.short_name = short_name
        self.parameters = parameters or {}
        self.workflow_dir = workflow_dir
        self._event_bus = event_bus
        self.workflow_version = workflow_version

        now = datetime.now(timezone.utc)
        self.run_timestamp = now.strftime("%Y%m%d%H%M%S")
        self.run_id = f"run_{now.strftime('%Y%m%d_%H%M%S')}"
        self.started_at = now

        self._steps: list[StepResult] = []
        self._artifacts: list[Artifact] = []

        self._environment = EnvironmentInfo(
            hostname=socket.gethostname(),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            raw_version="0.1.0",
            working_directory=str(Path.cwd()),
        )

    def emit(self, event: Any) -> None:
        """Emit an event to the EventBus if configured."""
        if self._event_bus is not None:
            self._event_bus.emit(event)

    def add_step_result(self, step: StepResult) -> None:
        """Record a step execution result."""
        self._steps.append(step)

    def skip_step(self, name: str, reason: str | None = None) -> None:
        """Record a skipped step.

        Use this to mark steps that were defined but not executed
        due to conditional logic.
        """
        from raw_runtime.models import StepStatus

        now = datetime.now(timezone.utc)
        step = StepResult(
            name=name,
            status=StepStatus.SKIPPED,
            started_at=now,
            ended_at=now,
            duration_seconds=0.0,
            error=reason,
        )
        self._steps.append(step)

    def add_artifact(self, artifact_type: str, path: Path | str) -> None:
        """Record an artifact produced by the workflow."""
        from raw_runtime.events import ArtifactCreatedEvent

        path = Path(path)
        size = path.stat().st_size if path.exists() else None

        artifact = Artifact(
            type=artifact_type,
            path=str(path),
            size_bytes=size,
        )
        self._artifacts.append(artifact)

        self.emit(
            ArtifactCreatedEvent(
                workflow_id=self.workflow_id,
                run_id=self.run_id,
                artifact_type=artifact_type,
                path=str(path),
                size_bytes=size,
            )
        )

    def get_steps(self) -> list[StepResult]:
        """Get all recorded step results."""
        return self._steps.copy()

    def get_artifacts(self) -> list[Artifact]:
        """Get all recorded artifacts."""
        return self._artifacts.copy()

    def build_manifest(
        self,
        status: RunStatus,
        error: str | None = None,
    ) -> Manifest:
        """Build the complete manifest for this run."""
        now = datetime.now(timezone.utc)
        duration = (now - self.started_at).total_seconds()

        workflow_info = WorkflowInfo(
            id=self.workflow_id,
            short_name=self.short_name,
            version="1.0.0",
            created_at=self.started_at,
        )

        run_info = RunInfo(
            run_id=self.run_id,
            workflow_id=self.workflow_id,
            started_at=self.started_at,
            ended_at=now,
            status=status,
            duration_seconds=duration,
            parameters=self.parameters,
            environment=self._environment,
        )

        logs = LogsInfo()
        if self.workflow_dir:
            log_path = self.workflow_dir / "output.log"
            logs.stdout = str(log_path)

        return Manifest(
            schema_version="1.0.0",
            workflow=workflow_info,
            run=run_info,
            steps=self._steps,
            artifacts=self._artifacts,
            logs=logs,
            error=error,
        )

    def finalize(
        self,
        status: str = "success",
        error: str | None = None,
    ) -> Manifest:
        """Finalize the workflow run and save manifest."""
        from raw_runtime.events import WorkflowCompletedEvent, WorkflowFailedEvent

        run_status = RunStatus(status)
        manifest = self.build_manifest(status=run_status, error=error)

        duration = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        if run_status == RunStatus.SUCCESS:
            self.emit(
                WorkflowCompletedEvent(
                    workflow_id=self.workflow_id,
                    run_id=self.run_id,
                    duration_seconds=duration,
                    step_count=len(self._steps),
                    artifacts=[a.path for a in self._artifacts],
                )
            )
        else:
            failed_step = None
            for step in reversed(self._steps):
                if step.status.value == "failed":
                    failed_step = step.name
                    break
            self.emit(
                WorkflowFailedEvent(
                    workflow_id=self.workflow_id,
                    run_id=self.run_id,
                    error=error or "Unknown error",
                    failed_step=failed_step,
                    duration_seconds=duration,
                )
            )

        # Save manifest if workflow_dir is set
        if self.workflow_dir:
            self._save_manifest(manifest)

        return manifest

    def _save_manifest(self, manifest: Manifest) -> None:
        """Save manifest to workflow_dir/manifest.json.

        When run via CLI, workflow_dir is the run directory (e.g., runs/20251208-xxxxx/).
        The manifest is saved directly there, not in a .raw subdirectory.
        """
        if not self.workflow_dir:
            return

        manifest_path = self.workflow_dir / "manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2, exclude_none=True))

    def __enter__(self) -> "WorkflowContext":
        """Enter context manager."""
        from raw_runtime.events import WorkflowStartedEvent

        set_workflow_context(self)
        self.emit(
            WorkflowStartedEvent(
                workflow_id=self.workflow_id,
                run_id=self.run_id,
                workflow_name=self.short_name,
                workflow_version=self.workflow_version,
                parameters=self.parameters,
            )
        )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        set_workflow_context(None)

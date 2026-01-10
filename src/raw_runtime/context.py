"""Workflow context management.

The WorkflowContext tracks the state of a workflow execution,
including step results and artifacts. It's used by decorators
to record execution data into the manifest.

With EventBus integration, the context emits events for all state
changes, enabling real-time monitoring and decoupled handlers.

Architecture:
- WorkflowContext: Coordinates execution state and event emission
- ManifestBuilder: Constructs manifests from execution data
- ManifestWriter: Persists manifests (injectable for testing)
"""

from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from raw_runtime.manifest import ManifestBuilder, ManifestWriter, get_manifest_writer
from raw_runtime.models import (
    Artifact,
    Manifest,
    RunStatus,
    StepResult,
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

    Coordinates execution state tracking and event emission.
    Delegates manifest building to ManifestBuilder and persistence to ManifestWriter.

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
        manifest_writer: ManifestWriter | None = None,
    ) -> None:
        """Initialize workflow context.

        Args:
            workflow_id: Unique workflow identifier
            short_name: Human-readable workflow name
            parameters: Input parameters for the workflow
            workflow_dir: Directory for output files
            event_bus: Optional event bus for emitting events
            workflow_version: Version string for the workflow
            manifest_writer: Optional writer for manifest persistence (DI)
        """
        self.workflow_id = workflow_id
        self.short_name = short_name
        self.parameters = parameters or {}
        self.workflow_dir = workflow_dir
        self._event_bus = event_bus
        self.workflow_version = workflow_version
        self._manifest_writer = manifest_writer or get_manifest_writer()

        now = datetime.now(timezone.utc)
        self.run_timestamp = now.strftime("%Y%m%d%H%M%S")
        self.run_id = f"run_{now.strftime('%Y%m%d_%H%M%S')}"
        self.started_at = now

        self._steps: list[StepResult] = []
        self._artifacts: list[Artifact] = []

        # Cache metrics for agentic steps
        self.agentic_cache_hits: int = 0
        self.agentic_cache_misses: int = 0

        # Cost tracking for agentic steps
        self.agentic_costs: list[dict[str, Any]] = []
        self.total_agentic_cost: float = 0.0

        self._manifest_builder = ManifestBuilder(
            workflow_id=workflow_id,
            short_name=short_name,
            started_at=now,
            run_id=self.run_id,
            parameters=self.parameters,
            workflow_dir=workflow_dir,
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

    def log_cache_hit(self) -> None:
        """Log an agentic cache hit."""
        self.agentic_cache_hits += 1

    def log_cache_miss(self) -> None:
        """Log an agentic cache miss."""
        self.agentic_cache_misses += 1

    def log_agentic_step(
        self,
        step_name: str,
        cost: float,
        tokens: dict[str, int],
        model: str,
        prompt: str | None = None,
    ) -> None:
        """Log cost and token usage for an agentic step.

        Args:
            step_name: Name of the agentic step
            cost: Cost in USD
            tokens: Dictionary with 'input' and 'output' token counts
            model: Model identifier
            prompt: Optional prompt text (first 100 chars stored)
        """
        step_data: dict[str, Any] = {
            "step_name": step_name,
            "cost": cost,
            "tokens": tokens,
            "model": model,
        }

        if prompt:
            step_data["prompt_preview"] = prompt[:100]

        self.agentic_costs.append(step_data)
        self.total_agentic_cost += cost

    def build_manifest(
        self,
        status: RunStatus,
        error: str | None = None,
    ) -> Manifest:
        """Build the complete manifest for this run.

        Delegates to ManifestBuilder for actual construction.
        """
        return self._manifest_builder.build(
            steps=self._steps,
            artifacts=self._artifacts,
            status=status,
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

        Delegates to ManifestWriter for actual persistence.
        When run via CLI, workflow_dir is the run directory (e.g., runs/20251208-xxxxx/).
        """
        if not self.workflow_dir:
            return

        manifest_path = self.workflow_dir / "manifest.json"
        self._manifest_writer.write(manifest, manifest_path)

    def __enter__(self) -> "WorkflowContext":
        """Enter context manager."""
        from raw_runtime.events import WorkflowProvenanceEvent, WorkflowStartedEvent
        from raw_runtime.provenance import capture_provenance

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

        # Emit provenance event immediately after workflow start
        provenance = capture_provenance()
        self.emit(
            WorkflowProvenanceEvent(
                workflow_id=self.workflow_id,
                run_id=self.run_id,
                **provenance,
            )
        )

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        set_workflow_context(None)

"""Event handlers for RAW workflows.

Handlers process events emitted by the EventBus. Each handler serves
a specific purpose:
- ConsoleEventHandler: Pretty console output for `raw run`
- JournalEventHandler: Append-only JSONL journal for crash recovery
- FileEventHandler: JSON logging for `raw serve` (future)
"""

from pathlib import Path

from rich.console import Console

from raw_runtime.events import (
    ArtifactCreatedEvent,
    CacheHitEvent,
    Event,
    EventType,
    StepCompletedEvent,
    StepFailedEvent,
    StepRetryEvent,
    StepSkippedEvent,
    StepStartedEvent,
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
    WorkflowStartedEvent,
)
from raw_runtime.journal import LocalJournalWriter


class ConsoleEventHandler:
    """Pretty console output for workflow events.

    Used by `raw run` to display real-time progress.
    """

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def __call__(self, event: Event) -> None:
        """Handle an event by printing to console."""
        match event.event_type:
            case EventType.WORKFLOW_STARTED:
                self._handle_workflow_started(event)  # type: ignore[arg-type]
            case EventType.WORKFLOW_COMPLETED:
                self._handle_workflow_completed(event)  # type: ignore[arg-type]
            case EventType.WORKFLOW_FAILED:
                self._handle_workflow_failed(event)  # type: ignore[arg-type]
            case EventType.STEP_STARTED:
                self._handle_step_started(event)  # type: ignore[arg-type]
            case EventType.STEP_COMPLETED:
                self._handle_step_completed(event)  # type: ignore[arg-type]
            case EventType.STEP_FAILED:
                self._handle_step_failed(event)  # type: ignore[arg-type]
            case EventType.STEP_SKIPPED:
                self._handle_step_skipped(event)  # type: ignore[arg-type]
            case EventType.STEP_RETRY:
                self._handle_step_retry(event)  # type: ignore[arg-type]
            case EventType.ARTIFACT_CREATED:
                self._handle_artifact_created(event)  # type: ignore[arg-type]
            case EventType.CACHE_HIT:
                self._handle_cache_hit(event)  # type: ignore[arg-type]
            case _:
                pass

    def _handle_workflow_started(self, event: WorkflowStartedEvent) -> None:
        version = f" v{event.workflow_version}" if event.workflow_version else ""
        self.console.print(f"[bold blue]▶[/] Starting [bold]{event.workflow_name}[/]{version}")

    def _handle_workflow_completed(self, event: WorkflowCompletedEvent) -> None:
        self.console.print()
        self.console.print(
            f"[bold green]✓[/] Completed in {event.duration_seconds:.2f}s "
            f"({event.step_count} steps)"
        )
        if event.artifacts:
            self.console.print(f"  Artifacts: {', '.join(event.artifacts)}")

    def _handle_workflow_failed(self, event: WorkflowFailedEvent) -> None:
        self.console.print()
        step_info = f" in {event.failed_step}" if event.failed_step else ""
        self.console.print(f"[bold red]✗[/] Failed{step_info} after {event.duration_seconds:.2f}s")
        self.console.print(f"  [red]{event.error}[/]")

    def _handle_step_started(self, event: StepStartedEvent) -> None:
        type_sig = ""
        if event.input_types:
            type_sig = f"({', '.join(event.input_types)}) → {event.output_type}"
        else:
            type_sig = f"() → {event.output_type}"
        self.console.print(f"[bold blue]►[/] [bold]{event.step_name}[/] [dim]{type_sig}[/]")

    def _handle_step_completed(self, event: StepCompletedEvent) -> None:
        self.console.print(
            f"[bold green]✓[/] [bold]{event.step_name}[/] → {event.result_type} "
            f"({event.duration_seconds:.2f}s)"
        )

    def _handle_step_failed(self, event: StepFailedEvent) -> None:
        self.console.print(
            f"[bold red]✗[/] [bold]{event.step_name}[/] Failed "
            f"({event.duration_seconds:.2f}s): {event.error}"
        )

    def _handle_step_skipped(self, event: StepSkippedEvent) -> None:
        self.console.print(
            f"[dim]⊘[/] [dim]{event.step_name}[/] [yellow]SKIPPED[/]: {event.reason}"
        )

    def _handle_step_retry(self, event: StepRetryEvent) -> None:
        self.console.print(
            f"[yellow]↻[/] Retry {event.attempt}/{event.max_attempts} after error: {event.error}"
        )

    def _handle_artifact_created(self, event: ArtifactCreatedEvent) -> None:
        size = f" ({event.size_bytes} bytes)" if event.size_bytes else ""
        self.console.print(f"[cyan]📄[/] Created {event.artifact_type}: {event.path}{size}")

    def _handle_cache_hit(self, event: CacheHitEvent) -> None:
        self.console.print(f"[cyan]💾[/] Using cached result for {event.step_name}")


class JournalEventHandler:
    """Journal event handler for crash recovery and provenance.

    Writes all events to .raw/runs/{run_id}/events.jsonl in real-time
    with immediate flush for crash safety.
    """

    def __init__(self, journal_path: Path) -> None:
        """Initialize journal event handler.

        Args:
            journal_path: Path to events.jsonl file
        """
        self._writer = LocalJournalWriter(journal_path)

    def __call__(self, event: Event) -> None:
        """Handle an event by writing to journal.

        Events are written immediately with fsync for crash safety.
        """
        self._writer.write_event(event)

    def flush(self) -> None:
        """Flush journal to disk."""
        self._writer.flush()

    def close(self) -> None:
        """Close journal file."""
        self._writer.close()

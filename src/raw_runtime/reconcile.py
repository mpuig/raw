"""Run reconciliation - detect and mark crashed/stale workflows.

Scans run directories, checks for incomplete runs (status=RUNNING), and marks
them as crashed by appending a workflow.crashed event to the journal.

Implements crash recovery reconciliation following the Kubernetes pattern:
- Detect stale runs from on-disk state
- Never delete data
- Write terminal status back to journal
- Derived manifest reflects crashed status
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import NamedTuple

from raw_runtime.journal import JournalReader, LocalJournalWriter
from raw_runtime.models import RunStatus
from raw_runtime.reducer import ManifestReducer


class ReconciliationResult(NamedTuple):
    """Result of reconciling a single run."""

    run_id: str
    previous_status: RunStatus
    new_status: RunStatus
    action: str  # "marked_crashed", "marked_cancelled", "no_action"
    message: str


def reconcile_run(
    run_dir: Path,
    stale_timeout_seconds: int = 3600,
    mark_as_crashed: bool = True,
) -> ReconciliationResult | None:
    """Reconcile a single run directory.

    Checks if the run is in a non-terminal state and hasn't been updated
    recently. If so, marks it as crashed by appending a workflow.crashed
    event to the journal.

    Args:
        run_dir: Path to run directory (e.g., .raw/runs/{run_id})
        stale_timeout_seconds: Consider run stale if last event is older than this
        mark_as_crashed: If True, write workflow.crashed event. If False, dry-run.

    Returns:
        ReconciliationResult if action taken, None if run is healthy
    """
    journal_path = run_dir / "events.jsonl"

    if not journal_path.exists():
        # No journal - can't reconcile
        return None

    # Rebuild manifest from journal
    try:
        reducer = ManifestReducer()
        manifest = reducer.reduce_from_file(journal_path)
    except Exception as e:
        # Corrupt journal - skip reconciliation
        return ReconciliationResult(
            run_id=run_dir.name,
            previous_status=RunStatus.RUNNING,
            new_status=RunStatus.RUNNING,
            action="error",
            message=f"Failed to read journal: {e}",
        )

    # Check if run is in terminal state
    if manifest.run.status in (
        RunStatus.SUCCESS,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
        RunStatus.CRASHED,
    ):
        # Already terminal - no action needed
        return None

    # Run is RUNNING or PENDING - check if stale
    # Use journal file modification time as proxy for last activity
    journal_mtime = datetime.fromtimestamp(journal_path.stat().st_mtime, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    age = (now - journal_mtime).total_seconds()

    if age < stale_timeout_seconds:
        # Run is active (recent journal modification) - no action needed
        return None

    # Run is stale - mark as crashed
    if mark_as_crashed:
        _write_crashed_event(
            journal_path=journal_path,
            workflow_id=manifest.workflow.id,
            run_id=manifest.run.run_id,
            error=f"Process terminated unexpectedly. Last activity: {journal_mtime.isoformat()}",
            duration_seconds=(now - manifest.run.started_at).total_seconds(),
        )

        return ReconciliationResult(
            run_id=manifest.run.run_id,
            previous_status=manifest.run.status,
            new_status=RunStatus.CRASHED,
            action="marked_crashed",
            message=f"Stale run (inactive for {age:.0f}s), marked as crashed",
        )
    else:
        # Dry-run mode
        return ReconciliationResult(
            run_id=manifest.run.run_id,
            previous_status=manifest.run.status,
            new_status=RunStatus.CRASHED,
            action="would_mark_crashed",
            message=f"Would mark as crashed (inactive for {age:.0f}s)",
        )


def scan_and_reconcile(
    workflows_dir: Path,
    stale_timeout_seconds: int = 3600,
    dry_run: bool = False,
) -> list[ReconciliationResult]:
    """Scan all runs and reconcile stale ones.

    Args:
        workflows_dir: Path to workflows directory (e.g., .raw/workflows)
        stale_timeout_seconds: Consider run stale if last event is older than this
        dry_run: If True, report what would be done without writing events

    Returns:
        List of reconciliation results (only runs that needed action)
    """
    results = []

    # Scan all workflow directories
    if not workflows_dir.exists():
        return results

    for workflow_dir in workflows_dir.iterdir():
        if not workflow_dir.is_dir():
            continue

        runs_dir = workflow_dir / "runs"
        if not runs_dir.exists():
            continue

        # Check each run
        for run_dir in runs_dir.iterdir():
            if not run_dir.is_dir():
                continue

            result = reconcile_run(
                run_dir=run_dir,
                stale_timeout_seconds=stale_timeout_seconds,
                mark_as_crashed=not dry_run,
            )

            if result:
                results.append(result)

    return results


def _write_crashed_event(
    journal_path: Path,
    workflow_id: str,
    run_id: str,
    error: str,
    duration_seconds: float,
) -> None:
    """Write workflow.crashed event to journal.

    This marks the run as crashed in the event log, which will be reflected
    in the derived manifest.
    """
    from raw_runtime.events import EventType

    # Create workflow.failed event (no workflow.crashed event type yet)
    # Use workflow.failed with "CRASHED: " prefix in error message
    event_data = {
        "event_type": EventType.WORKFLOW_FAILED.value,
        "workflow_id": workflow_id,
        "run_id": run_id,
        "error": f"CRASHED: {error}",
        "failed_step": None,
        "duration_seconds": duration_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event_id": "reconcile-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
    }

    # Append to journal
    with LocalJournalWriter(journal_path) as writer:
        # Write raw event dict (not Event object)
        import json

        journal_entry = {"version": 1, "event": event_data}
        line = json.dumps(journal_entry, default=str) + "\n"

        # Append directly to file
        with open(journal_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()


__all__ = [
    "ReconciliationResult",
    "reconcile_run",
    "scan_and_reconcile",
]

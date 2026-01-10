"""Resume functionality for interrupted workflow runs.

Enables continuing execution from where it left off by:
- Reading journal to identify completed steps
- Configuring WorkflowContext to skip completed steps
- Linking resumed run to original run for provenance
"""

from pathlib import Path

from raw_runtime.models import StepStatus
from raw_runtime.reducer import ManifestReducer


def prepare_resume_state(journal_path: Path) -> tuple[set[str], str]:
    """Prepare resume state from a previous run's journal.

    Reads the journal, identifies which steps completed successfully,
    and returns information needed to configure resume.

    Args:
        journal_path: Path to events.jsonl from previous run

    Returns:
        Tuple of (completed_step_names, previous_run_id)

    Raises:
        ValueError: If journal is missing, corrupt, or has no workflow.started event
    """
    if not journal_path.exists():
        raise ValueError(f"Journal not found: {journal_path}")

    # Rebuild manifest from journal to get step states
    reducer = ManifestReducer()
    try:
        manifest = reducer.reduce_from_file(journal_path)
    except Exception as e:
        raise ValueError(f"Failed to read journal: {e}") from e

    # Collect step names that completed successfully
    completed_steps = {
        step.name for step in manifest.steps if step.status == StepStatus.SUCCESS
    }

    return completed_steps, manifest.run.run_id


def configure_context_for_resume(
    context: "WorkflowContext", journal_path: Path  # type: ignore[name-defined]
) -> None:
    """Configure a WorkflowContext to resume from a previous run.

    Reads the journal from the previous run and configures the context
    to skip steps that already completed successfully.

    Args:
        context: WorkflowContext to configure for resume
        journal_path: Path to events.jsonl from previous run

    Raises:
        ValueError: If journal is invalid or cannot be read
    """
    completed_steps, previous_run_id = prepare_resume_state(journal_path)

    context.resume_completed_steps = completed_steps
    context.resumed_from_run_id = previous_run_id


__all__ = [
    "prepare_resume_state",
    "configure_context_for_resume",
]

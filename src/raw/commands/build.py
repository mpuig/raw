"""Build command implementation - agentic workflow development."""

import sys

from raw.builder import build_workflow


def build_command(
    workflow_id: str | None,
    max_iterations: int | None,
    max_minutes: int | None,
    resume: str | None,
    last: bool,
    prompt_workflow_selection: callable,
) -> None:
    """Build a workflow using the agentic builder loop.

    This function contains the business logic for the build command.
    The CLI layer (cli.py) handles argument parsing and delegates here.

    Args:
        workflow_id: Workflow identifier (prompts if None)
        max_iterations: Maximum plan-execute cycles
        max_minutes: Maximum wall time in minutes
        resume: Build ID to resume from
        last: Resume from last build
        prompt_workflow_selection: Function to prompt user for workflow selection
    """
    # Handle resume flags (mutually exclusive with workflow_id in CLI validation)
    if resume or last:
        if workflow_id:
            print("Error: Cannot specify workflow_id with --resume or --last")
            sys.exit(1)

        # Resume doesn't need workflow_id (extracted from build journal)
        exit_code = build_workflow(
            workflow_id="",  # Will be loaded from journal
            max_iterations=max_iterations,
            max_minutes=max_minutes,
            resume=resume,
            last=last,
        )
        sys.exit(exit_code)

    # Normal build flow - need workflow_id
    if not workflow_id:
        selected = prompt_workflow_selection(action="build")
        if not selected:
            print("No workflows found. Run 'raw create' first.")
            sys.exit(1)
        workflow_id = selected

    # Execute builder
    exit_code = build_workflow(
        workflow_id=workflow_id,
        max_iterations=max_iterations,
        max_minutes=max_minutes,
        resume=None,
        last=False,
    )

    sys.exit(exit_code)

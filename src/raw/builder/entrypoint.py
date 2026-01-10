"""Builder entrypoint - main entry function for raw build command."""

from pathlib import Path


def build_workflow(
    workflow_id: str,
    *,
    max_iterations: int | None = None,
    max_minutes: int | None = None,
    resume: str | None = None,
    last: bool = False,
) -> int:
    """Build a workflow using the agentic builder loop.

    The builder implements plan → execute → verify → iterate cycles:
    1. Plan mode: Analyze requirements, create numbered plan (read-only)
    2. Execute mode: Apply changes to workflow and tools
    3. Verify: Run quality gates (validate, dry, optional tests)
    4. Iterate: If gates fail, feed failures into next plan cycle

    Args:
        workflow_id: Workflow identifier to build
        max_iterations: Maximum plan-execute cycles (default: config or 10)
        max_minutes: Maximum wall time in minutes (default: config or 30)
        resume: Resume from specific build_id
        last: Resume from last build (convenience flag)

    Returns:
        Exit code: 0 on success, non-zero on failure

    Example:
        raw build my-workflow
        raw build my-workflow --max-iterations 5
        raw build --resume build-abc123
        raw build --last
    """
    # TODO: Implement builder loop controller
    # For now, just print a message and return success
    print(f"[Builder] Building workflow: {workflow_id}")

    if resume:
        print(f"[Builder] Resuming from build: {resume}")
    elif last:
        print("[Builder] Resuming from last build")

    if max_iterations:
        print(f"[Builder] Max iterations: {max_iterations}")

    if max_minutes:
        print(f"[Builder] Max minutes: {max_minutes}")

    print("[Builder] Skeleton command - full implementation coming soon")
    print("[Builder] Exit code: 0")

    return 0

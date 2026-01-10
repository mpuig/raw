"""Builder entrypoint - main entry function for raw build command."""

import asyncio
from pathlib import Path

from raw.builder.config import load_builder_config, merge_cli_overrides
from raw.builder.loop import builder_loop
from raw.builder.resume import (
    ResumeError,
    find_build_to_resume,
    replay_journal_for_resume,
)


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
    # Load configuration from .raw/config.yaml
    config = load_builder_config(Path.cwd())

    # Merge CLI overrides
    config = merge_cli_overrides(config, max_iterations, max_minutes)

    # Handle resume
    resume_state = None
    if resume or last:
        try:
            # Find build to resume
            build_id_to_resume = find_build_to_resume(build_id=resume, last=last)

            # Replay journal to reconstruct state
            resume_state = replay_journal_for_resume(build_id_to_resume)

            # Override workflow_id from resumed state if not specified
            if not workflow_id:
                workflow_id = resume_state.workflow_id

            # Merge config from resumed build (CLI overrides still apply)
            from raw.builder.config import BuilderConfig

            resumed_config = BuilderConfig.model_validate(resume_state.config)
            resumed_config = merge_cli_overrides(resumed_config, max_iterations, max_minutes)
            config = resumed_config

        except ResumeError as e:
            print(f"[Builder] Resume error: {e}")
            return 1

    # Validate workflow_id is present
    if not workflow_id:
        print("[Builder] Error: workflow_id required (use: raw build <workflow-id>)")
        return 1

    # Run builder loop (async)
    try:
        result = asyncio.run(
            builder_loop(workflow_id, intent=None, config=config, resume_state=resume_state)
        )
        return result.exit_code()
    except ValueError as e:
        print(f"[Builder] Error: {e}")
        return 1
    except KeyboardInterrupt:
        print(f"\n[Builder] Build interrupted by user")
        return 1
    except Exception as e:
        print(f"[Builder] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1

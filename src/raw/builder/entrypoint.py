"""Builder entrypoint - main entry function for raw build command."""

import asyncio
from pathlib import Path

from raw.builder.config import load_builder_config, merge_cli_overrides
from raw.builder.loop import builder_loop


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

    # Handle resume (TODO: implement resume logic in raw-7kx.9)
    if resume or last:
        print(f"[Builder] Resume functionality not yet implemented")
        print(f"[Builder] Use: raw build {workflow_id}")
        return 1

    # Run builder loop (async)
    try:
        result = asyncio.run(builder_loop(workflow_id, intent=None, config=config))
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

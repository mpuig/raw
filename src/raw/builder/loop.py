"""Builder loop controller - orchestrates plan → execute → verify → iterate cycles."""

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from raw.builder.config import BuilderConfig
from raw.builder.events import (
    BuildCompletedEvent,
    BuildFailedEvent,
    BuildStartedEvent,
    BuildStuckEvent,
    GateCompletedEvent,
    GateStartedEvent,
    IterationCompletedEvent,
    IterationStartedEvent,
    ModeSwitchedEvent,
    PlanUpdatedEvent,
)
from raw.builder.gates import format_gate_failures, run_gates, save_gate_output
from raw.builder.journal import BuilderJournal
from raw.builder.mode import BuildMode
from raw.builder.skills import discover_skills
from raw.discovery.workflow import find_workflow


class BuildResult:
    """Result of a builder run."""

    def __init__(self, status: str, build_id: str, iterations: int, message: str | None = None):
        """Initialize build result.

        Args:
            status: "success" | "failed" | "stuck"
            build_id: Unique build identifier
            iterations: Number of iterations completed
            message: Optional message (error or stuck reason)
        """
        self.status = status
        self.build_id = build_id
        self.iterations = iterations
        self.message = message

    def exit_code(self) -> int:
        """Get exit code for CLI.

        Returns:
            0 for success, 1 for failed, 2 for stuck
        """
        if self.status == "success":
            return 0
        elif self.status == "stuck":
            return 2
        else:
            return 1


async def builder_loop(
    workflow_id: str,
    intent: str | None,
    config: BuilderConfig,
) -> BuildResult:
    """Execute builder loop with plan → execute → verify → iterate cycles.

    Args:
        workflow_id: Workflow to build
        intent: Optional intent override
        config: Builder configuration

    Returns:
        BuildResult with status and metadata

    Raises:
        ValueError: If workflow not found
    """
    # Resolve workflow
    workflow_dir = find_workflow(workflow_id)
    if not workflow_dir:
        raise ValueError(f"Workflow not found: {workflow_id}")

    # Generate build ID
    build_id = f"build-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    # Create journal
    with BuilderJournal(build_id) as journal:
        # Emit build started
        journal.write(
            BuildStartedEvent(
                build_id=build_id,
                iteration=0,
                workflow_id=workflow_id,
                intent=intent,
                config=config.model_dump(),
            )
        )

        # Discover skills
        skills = discover_skills()

        # Initialize state
        iteration = 0
        mode = BuildMode.PLAN if config.mode.plan_first else BuildMode.EXECUTE
        start_time = time.time()
        last_failures: list[str] = []
        doom_loop_counter = 0
        last_gate_results_signature: str | None = None

        print(f"[Builder] Starting build: {build_id}")
        print(f"[Builder] Workflow: {workflow_id}")
        print(f"[Builder] Skills: {len(skills)} discovered")
        print(f"[Builder] Mode: {mode.value}")

        # Main loop
        while True:
            iteration += 1

            # Budget checks
            if iteration > config.budgets.max_iterations:
                return _finish_stuck(
                    journal,
                    build_id,
                    iteration,
                    "max_iterations",
                    last_failures,
                    f"Exceeded maximum iterations ({config.budgets.max_iterations})",
                )

            elapsed_minutes = (time.time() - start_time) / 60
            if elapsed_minutes > config.budgets.max_minutes:
                return _finish_stuck(
                    journal,
                    build_id,
                    iteration,
                    "max_time",
                    last_failures,
                    f"Exceeded time limit ({config.budgets.max_minutes} minutes)",
                )

            # Start iteration
            journal.write(
                IterationStartedEvent(
                    build_id=build_id,
                    iteration=iteration,
                    mode=mode.value,
                )
            )

            print(f"\n[Builder] Iteration {iteration} ({mode.value} mode)")

            if mode == BuildMode.PLAN:
                # PLAN MODE: Generate numbered plan with gates
                plan = await _run_plan_mode(journal, build_id, iteration, workflow_id, skills, config)

                if not plan:
                    return _finish_failed(
                        journal,
                        build_id,
                        iteration,
                        "Failed to generate plan",
                    )

                # Switch to execute mode
                mode = BuildMode.EXECUTE
                journal.write(
                    ModeSwitchedEvent(
                        build_id=build_id,
                        iteration=iteration,
                        mode="execute",
                    )
                )

            elif mode == BuildMode.EXECUTE:
                # EXECUTE MODE: Apply changes according to plan
                success = await _run_execute_mode(
                    journal,
                    build_id,
                    iteration,
                    workflow_id,
                    config,
                )

                if not success:
                    return _finish_failed(
                        journal,
                        build_id,
                        iteration,
                        "Execute mode failed",
                    )

                # VERIFY: Run quality gates
                print(f"[Builder] Running quality gates...")

                gate_results = await run_gates(workflow_id, config, workflow_dir)

                # Save gate outputs
                for result in gate_results:
                    journal.write(
                        GateStartedEvent(
                            build_id=build_id,
                            iteration=iteration,
                            gate=result.gate,
                        )
                    )

                    log_path = save_gate_output(result, journal.build_dir)

                    journal.write(
                        GateCompletedEvent(
                            build_id=build_id,
                            iteration=iteration,
                            gate=result.gate,
                            passed=result.passed,
                            duration_seconds=result.duration_seconds,
                            output_path=str(log_path),
                        )
                    )

                    status = "✓ PASS" if result.passed else "✗ FAIL"
                    print(f"  {status} {result.gate} ({result.duration_seconds:.2f}s)")

                # Check if all gates passed
                all_passed = all(r.passed for r in gate_results)

                if all_passed:
                    # SUCCESS!
                    duration = time.time() - start_time
                    journal.write(
                        BuildCompletedEvent(
                            build_id=build_id,
                            iteration=iteration,
                            total_iterations=iteration,
                            duration_seconds=duration,
                        )
                    )

                    print(f"\n[Builder] ✓ Build completed successfully!")
                    print(f"[Builder] Iterations: {iteration}")
                    print(f"[Builder] Duration: {duration:.1f}s")
                    print(f"[Builder] Build ID: {build_id}")

                    return BuildResult("success", build_id, iteration)

                # Gates failed - prepare feedback
                failures = format_gate_failures(gate_results)
                last_failures.append(failures)

                # Check for doom loop (same failures repeatedly)
                gate_signature = "|".join(
                    f"{r.gate}:{r.passed}" for r in sorted(gate_results, key=lambda x: x.gate)
                )

                if gate_signature == last_gate_results_signature:
                    doom_loop_counter += 1
                else:
                    doom_loop_counter = 0

                last_gate_results_signature = gate_signature

                if doom_loop_counter >= config.budgets.doom_loop_threshold:
                    return _finish_stuck(
                        journal,
                        build_id,
                        iteration,
                        "doom_loop",
                        last_failures,
                        f"Same gate failures {doom_loop_counter} times in a row",
                    )

                # Switch back to plan mode with gate feedback
                mode = BuildMode.PLAN
                journal.write(
                    ModeSwitchedEvent(
                        build_id=build_id,
                        iteration=iteration,
                        mode="plan",
                        context=failures,
                    )
                )

                print(f"[Builder] {failures}")
                print(f"[Builder] Switching to plan mode for iteration {iteration + 1}")

            # Complete iteration
            iteration_duration = time.time() - start_time
            journal.write(
                IterationCompletedEvent(
                    build_id=build_id,
                    iteration=iteration,
                    duration_seconds=iteration_duration,
                )
            )

        # Should never reach here (budgets catch infinite loops)


async def _run_plan_mode(
    journal: BuilderJournal,
    build_id: str,
    iteration: int,
    workflow_id: str,
    skills: list,
    config: BuilderConfig,
) -> str | None:
    """Run plan mode - agent generates numbered plan.

    Args:
        journal: Builder journal
        build_id: Build identifier
        iteration: Current iteration
        workflow_id: Workflow being built
        skills: Discovered skills
        config: Builder configuration

    Returns:
        Plan text or None if failed
    """
    # TODO: Implement LLM integration
    # For now, return a mock plan
    plan = f"""
## Analysis
Workflow {workflow_id} needs implementation.

## Approach
Follow standard workflow pattern.

## Steps
1. Read existing run.py
2. Validate structure
3. Update as needed

## Quality Gates
- validate: Structural validation
- dry: Dry run with mocks
"""

    journal.write(
        PlanUpdatedEvent(
            build_id=build_id,
            iteration=iteration,
            plan=plan,
            gates=config.gates.default,
        )
    )

    print(f"[Builder] Plan generated")
    return plan


async def _run_execute_mode(
    journal: BuilderJournal,
    build_id: str,
    iteration: int,
    workflow_id: str,
    config: BuilderConfig,
) -> bool:
    """Run execute mode - agent implements plan.

    Args:
        journal: Builder journal
        build_id: Build identifier
        iteration: Current iteration
        workflow_id: Workflow being built
        config: Builder configuration

    Returns:
        True if execution succeeded
    """
    # TODO: Implement LLM integration
    # For now, assume execution succeeds
    print(f"[Builder] Executing plan...")
    return True


def _finish_stuck(
    journal: BuilderJournal,
    build_id: str,
    iteration: int,
    reason: str,
    last_failures: list[str],
    message: str,
) -> BuildResult:
    """Finish build with STUCK status."""
    journal.write(
        BuildStuckEvent(
            build_id=build_id,
            iteration=iteration,
            reason=reason,
            last_failures=last_failures[-3:] if last_failures else [],
        )
    )

    print(f"\n[Builder] ⚠ Build stuck: {message}")
    print(f"[Builder] Reason: {reason}")
    print(f"[Builder] Build ID: {build_id}")

    if last_failures:
        print(f"[Builder] Recent failures:")
        for failure in last_failures[-3:]:
            print(f"  • {failure}")

    return BuildResult("stuck", build_id, iteration, message)


def _finish_failed(
    journal: BuilderJournal,
    build_id: str,
    iteration: int,
    error: str,
) -> BuildResult:
    """Finish build with FAILED status."""
    journal.write(
        BuildFailedEvent(
            build_id=build_id,
            iteration=iteration,
            reason="execution_failed",
            error=error,
        )
    )

    print(f"\n[Builder] ✗ Build failed: {error}")
    print(f"[Builder] Build ID: {build_id}")

    return BuildResult("failed", build_id, iteration, error)

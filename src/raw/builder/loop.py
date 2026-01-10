"""Builder loop controller - orchestrates plan → execute → verify → iterate cycles."""

import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from raw.builder.config import BuilderConfig

if TYPE_CHECKING:
    from raw.builder.resume import ResumeState

logger = logging.getLogger(__name__)
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
    resume_state: "ResumeState | None" = None,
) -> BuildResult:
    """Execute builder loop with plan → execute → verify → iterate cycles.

    Args:
        workflow_id: Workflow to build
        intent: Optional intent override
        config: Builder configuration
        resume_state: Optional state from previous build to resume

    Returns:
        BuildResult with status and metadata

    Raises:
        ValueError: If workflow not found
    """
    # Resolve workflow
    workflow_dir = find_workflow(workflow_id)
    if not workflow_dir:
        raise ValueError(f"Workflow not found: {workflow_id}")

    # Initialize or resume
    if resume_state:
        # RESUME: Use state from previous build
        build_id = resume_state.build_id
        iteration = resume_state.last_iteration
        mode = resume_state.current_mode
        start_time = resume_state.start_timestamp
        last_failures = resume_state.last_failures
        doom_loop_counter = resume_state.doom_loop_counter
        last_gate_results_signature = resume_state.last_gate_results_signature

        logger.info("Resuming build: %s", build_id)
        logger.info("Workflow: %s", workflow_id)
        logger.info("Last iteration: %d", iteration)
        logger.info("Current mode: %s", mode.value)
    else:
        # NEW BUILD: Initialize fresh state
        build_id = f"build-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        iteration = 0
        mode = BuildMode.PLAN if config.mode.plan_first else BuildMode.EXECUTE
        start_time = time.time()
        last_failures = []
        doom_loop_counter = 0
        last_gate_results_signature = None

        logger.info("Starting build: %s", build_id)
        logger.info("Workflow: %s", workflow_id)
        logger.info("Mode: %s", mode.value)

    # Discover skills
    skills = discover_skills()
    if not resume_state:
        logger.info("Skills: %d discovered", len(skills))

    # Create or open journal
    with BuilderJournal(build_id) as journal:
        # Emit build started only for new builds
        if not resume_state:
            journal.write(
                BuildStartedEvent(
                    build_id=build_id,
                    iteration=0,
                    workflow_id=workflow_id,
                    intent=intent,
                    config=config.model_dump(),
                )
            )

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
            iteration_start = time.time()
            journal.write(
                IterationStartedEvent(
                    build_id=build_id,
                    iteration=iteration,
                    mode=mode.value,
                )
            )

            logger.info("Iteration %d (%s mode)", iteration, mode.value)

            if mode == BuildMode.PLAN:
                # PLAN MODE: Generate numbered plan with gates
                plan = await _run_plan_mode(
                    journal,
                    build_id,
                    iteration,
                    workflow_id,
                    skills,
                    config,
                    intent=intent,
                    last_failures=last_failures,
                )

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
                logger.info("Running quality gates...")

                gate_results = await run_gates(
                    workflow_id,
                    config,
                    workflow_dir,
                    journal=journal,
                    build_id=build_id,
                    iteration=iteration,
                )

                # Log gate results
                for result in gate_results:
                    status = "PASS" if result.passed else "FAIL"
                    logger.info("Gate %s: %s (%.2fs)", result.gate, status, result.duration_seconds)

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

                    logger.info("Build completed successfully")
                    logger.info("Iterations: %d", iteration)
                    logger.info("Duration: %.1fs", duration)
                    logger.info("Build ID: %s", build_id)

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

                logger.warning("Gates failed: %s", failures)
                logger.info("Switching to plan mode for iteration %d", iteration + 1)

            # Complete iteration
            iteration_duration = time.time() - iteration_start
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
    intent: str | None = None,
    last_failures: list[str] | None = None,
) -> str | None:
    """Run plan mode - agent generates numbered plan.

    Args:
        journal: Builder journal
        build_id: Build identifier
        iteration: Current iteration
        workflow_id: Workflow being built
        skills: Discovered skills
        config: Builder configuration
        intent: User's original intent
        last_failures: Previous failures for retry context

    Returns:
        Plan text or None if failed
    """
    from raw.builder.context import BuilderContext
    from raw.builder.llm import BuilderLLM

    logger.info("Running plan mode with LLM...")

    try:
        # Build context
        context = BuilderContext(
            workflow_id=workflow_id,
            intent=intent,
            last_failures=last_failures or [],
        )

        # Generate system prompt
        system_prompt = context.build_system_prompt("plan")

        # Inject system-architecture skill if available
        skill_injection = context.format_skills_for_injection(["system-architecture"])
        if skill_injection:
            system_prompt += "\n" + skill_injection

        # Build user message
        if iteration == 1:
            user_message = f"Create a plan for workflow '{workflow_id}'."
            if intent:
                user_message += f"\n\nUser requirements:\n{intent}"
        else:
            user_message = "The previous iteration failed. Create an updated plan that addresses the failures."

        # Generate plan
        llm = BuilderLLM()
        plan = llm.generate(
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=8192,
            temperature=1.0,
        )

        # Save plan to build directory
        plan_file = journal.build_dir / "plan.md"
        plan_file.write_text(plan)

        # Write event
        journal.write(
            PlanUpdatedEvent(
                build_id=build_id,
                iteration=iteration,
                plan=plan,
                gates=config.gates.default,
            )
        )

        logger.info("Plan generated successfully")
        return plan

    except Exception as e:
        logger.error("Failed to generate plan: %s", e)
        return None


async def _run_execute_mode(
    journal: BuilderJournal,
    build_id: str,
    iteration: int,
    workflow_id: str,
    config: BuilderConfig,
    plan: str | None = None,
) -> bool:
    """Run execute mode - agent implements plan.

    Args:
        journal: Builder journal
        build_id: Build identifier
        iteration: Current iteration
        workflow_id: Workflow being built
        config: Builder configuration
        plan: The plan to execute

    Returns:
        True if execution succeeded
    """
    from anthropic import Anthropic
    from anthropic.types import TextBlock, ToolUseBlock

    from raw.builder.context import BuilderContext
    from raw.builder.tools import get_builder_tools, handle_tool_call

    logger.info("Running execute mode with LLM...")

    try:
        # Build context
        context = BuilderContext(workflow_id=workflow_id)
        system_prompt = context.build_system_prompt("execute")

        # Load plan from build directory
        if plan is None:
            plan_file = journal.build_dir / "plan.md"
            if plan_file.exists():
                plan = plan_file.read_text()

        # Initialize LLM with tools
        llm = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        tools = get_builder_tools()

        # Build initial message with plan
        messages = []
        if plan:
            messages.append({
                "role": "user",
                "content": f"Execute this plan:\n\n{plan}",
            })
        else:
            messages.append({
                "role": "user",
                "content": f"Implement workflow '{workflow_id}'.",
            })

        # Agentic loop - LLM uses tools until done
        max_turns = 50  # Safety limit
        for turn in range(max_turns):
            logger.info("Execute mode turn %d/%d", turn + 1, max_turns)

            # Call LLM with tools
            response = llm.messages.create(
                model="claude-sonnet-4-20250514",
                system=system_prompt,
                messages=messages,
                max_tokens=8192,
                tools=tools,
            )

            # Add assistant response to conversation
            assistant_message = {"role": "assistant", "content": response.content}
            messages.append(assistant_message)

            # Check if we're done (no tool calls)
            tool_uses = [block for block in response.content if isinstance(block, ToolUseBlock)]
            if not tool_uses:
                # Agent finished
                logger.info("Execute mode completed")
                return True

            # Execute tool calls
            tool_results = []
            for tool_use in tool_uses:
                logger.info("Executing tool: %s", tool_use.name)

                # Log tool call event
                from raw.builder.events import ToolCallStartedEvent

                journal.write(
                    ToolCallStartedEvent(
                        build_id=build_id,
                        iteration=iteration,
                        tool=tool_use.name,
                        parameters=tool_use.input,
                    )
                )

                # Execute tool
                try:
                    result = await handle_tool_call(tool_use, workflow_id)

                    # Log completion
                    from raw.builder.events import ToolCallCompletedEvent

                    journal.write(
                        ToolCallCompletedEvent(
                            build_id=build_id,
                            iteration=iteration,
                            tool=tool_use.name,
                            success=True,
                            result=str(result)[:500],  # Truncate for journal
                        )
                    )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result,
                    })

                except Exception as e:
                    logger.warning("Tool call failed: %s", e)

                    # Log failure
                    from raw.builder.events import ToolCallCompletedEvent

                    journal.write(
                        ToolCallCompletedEvent(
                            build_id=build_id,
                            iteration=iteration,
                            tool=tool_use.name,
                            success=False,
                            result=str(e),
                        )
                    )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": f"Error: {e}",
                        "is_error": True,
                    })

            # Add tool results to conversation
            messages.append({"role": "user", "content": tool_results})

        # Hit max turns without completion
        logger.warning("Execute mode hit max turns (%d)", max_turns)
        return False

    except Exception as e:
        logger.error("Execute mode failed: %s", e)
        return False


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

    logger.warning("Build stuck: %s", message)
    logger.warning("Reason: %s", reason)
    logger.info("Build ID: %s", build_id)

    if last_failures:
        logger.warning("Recent failures:")
        for failure in last_failures[-3:]:
            logger.warning("  - %s", failure)

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

    logger.error("Build failed: %s", error)
    logger.info("Build ID: %s", build_id)

    return BuildResult("failed", build_id, iteration, error)

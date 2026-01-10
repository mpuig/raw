"""Builder resume - replay journal and reconstruct state."""

from dataclasses import dataclass
from pathlib import Path

from raw.builder.events import BuildEventType
from raw.builder.journal import BuilderJournalReader, get_last_build, list_builds
from raw.builder.mode import BuildMode


@dataclass
class ResumeState:
    """State reconstructed from journal for resuming a build."""

    build_id: str
    workflow_id: str
    intent: str | None
    config: dict
    last_iteration: int
    current_mode: BuildMode
    start_timestamp: float
    last_failures: list[str]
    doom_loop_counter: int
    last_gate_results_signature: str | None
    build_dir: Path

    def is_resumable(self) -> bool:
        """Check if build can be resumed (not already complete/failed/stuck)."""
        return True  # Will be set during replay


class ResumeError(Exception):
    """Error during resume operation."""

    pass


def find_build_to_resume(build_id: str | None = None, last: bool = False) -> str:
    """Find build ID to resume.

    Args:
        build_id: Specific build ID to resume
        last: Resume last build

    Returns:
        Build ID to resume

    Raises:
        ResumeError: If build not found or ambiguous
    """
    if build_id and last:
        raise ResumeError("Cannot specify both --resume and --last")

    if build_id:
        # Validate build exists
        builds = list_builds()
        if not any(b["build_id"] == build_id for b in builds):
            raise ResumeError(f"Build not found: {build_id}")
        return build_id

    if last:
        # Get most recent build
        last_build = get_last_build()
        if not last_build:
            raise ResumeError("No previous builds found")
        return last_build["build_id"]

    raise ResumeError("Must specify either --resume <build_id> or --last")


def replay_journal_for_resume(build_id: str, builds_dir: Path | None = None) -> ResumeState:
    """Replay journal to reconstruct build state.

    Args:
        build_id: Build ID to resume
        builds_dir: Directory containing builds (defaults to .raw/builds)

    Returns:
        ResumeState with reconstructed state

    Raises:
        ResumeError: If build cannot be resumed
    """
    if builds_dir is None:
        builds_dir = Path.cwd() / ".raw" / "builds"

    build_dir = builds_dir / build_id
    if not build_dir.exists():
        raise ResumeError(f"Build directory not found: {build_dir}")

    # Read journal
    journal_path = build_dir / "events.jsonl"
    if not journal_path.exists():
        raise ResumeError(f"Journal not found: {journal_path}")

    reader = BuilderJournalReader(journal_path)

    try:
        events = reader.read_events()
    except FileNotFoundError as e:
        raise ResumeError(f"Journal not found: {e}")

    if not events:
        raise ResumeError(f"Empty journal for build: {build_id}")

    # Reconstruct state by replaying events
    workflow_id: str | None = None
    intent: str | None = None
    config: dict | None = None
    start_timestamp: float | None = None
    last_iteration = 0
    current_mode = BuildMode.PLAN
    last_failures: list[str] = []
    doom_loop_counter = 0
    last_gate_results_signature: str | None = None
    terminal_event: str | None = None  # Track if build already finished

    for event in events:
        event_type = event.get("event_type")

        if event_type == BuildEventType.BUILD_STARTED.value:
            workflow_id = event.get("workflow_id")
            intent = event.get("intent")
            config = event.get("config")
            start_timestamp = event.get("timestamp", 0)

        elif event_type == BuildEventType.ITERATION_STARTED.value:
            last_iteration = event.get("iteration", 0)
            mode_str = event.get("mode", "plan")
            current_mode = BuildMode.PLAN if mode_str == "plan" else BuildMode.EXECUTE

        elif event_type == BuildEventType.MODE_SWITCHED.value:
            mode_str = event.get("mode", "plan")
            current_mode = BuildMode.PLAN if mode_str == "plan" else BuildMode.EXECUTE
            # Context may contain failure messages
            context = event.get("context")
            if context:
                last_failures.append(context)

        elif event_type == BuildEventType.GATE_COMPLETED.value:
            # Track gate results for doom loop detection
            gate_name = event.get("gate")
            passed = event.get("passed")
            if gate_name and passed is not None:
                # Build gate signature (will be reconstructed properly later)
                pass

        elif event_type == BuildEventType.BUILD_COMPLETED.value:
            terminal_event = "completed"

        elif event_type == BuildEventType.BUILD_FAILED.value:
            terminal_event = "failed"

        elif event_type == BuildEventType.BUILD_STUCK.value:
            terminal_event = "stuck"

    # Validate required fields
    if not workflow_id:
        raise ResumeError("Cannot determine workflow_id from journal")

    if config is None:
        raise ResumeError("Cannot determine config from journal")

    if start_timestamp is None:
        raise ResumeError("Cannot determine start_timestamp from journal")

    # Check if build already finished
    if terminal_event:
        raise ResumeError(
            f"Cannot resume build that already {terminal_event}. "
            f"Use 'raw build {workflow_id}' to start a new build."
        )

    # Reconstruct gate results signature for doom loop detection
    # We need to look at the most recent GATE_COMPLETED events in the last iteration
    gate_results_in_last_iteration: list[tuple[str, bool]] = []
    current_iteration_events = [e for e in events if e.get("iteration") == last_iteration]

    for event in current_iteration_events:
        if event.get("event_type") == BuildEventType.GATE_COMPLETED.value:
            gate = event.get("gate")
            passed = event.get("passed")
            if gate and passed is not None:
                gate_results_in_last_iteration.append((gate, passed))

    if gate_results_in_last_iteration:
        # Sort and create signature
        gate_results_in_last_iteration.sort(key=lambda x: x[0])
        last_gate_results_signature = "|".join(f"{g}:{p}" for g, p in gate_results_in_last_iteration)

        # Check if we're in a doom loop by looking at previous iterations
        # Count how many times we've seen this exact signature
        iteration_gate_signatures: list[str] = []
        for iter_num in range(1, last_iteration + 1):
            iter_events = [e for e in events if e.get("iteration") == iter_num]
            gate_results: list[tuple[str, bool]] = []

            for event in iter_events:
                if event.get("event_type") == BuildEventType.GATE_COMPLETED.value:
                    gate = event.get("gate")
                    passed = event.get("passed")
                    if gate and passed is not None:
                        gate_results.append((gate, passed))

            if gate_results:
                gate_results.sort(key=lambda x: x[0])
                sig = "|".join(f"{g}:{p}" for g, p in gate_results)
                iteration_gate_signatures.append(sig)

        # Count consecutive occurrences of the same signature at the end
        doom_loop_counter = 0
        if iteration_gate_signatures:
            last_sig = iteration_gate_signatures[-1]
            for sig in reversed(iteration_gate_signatures):
                if sig == last_sig:
                    doom_loop_counter += 1
                else:
                    break

    # Determine next mode
    # If we completed an iteration in EXECUTE mode and gates failed, next is PLAN
    # If we completed PLAN, next is EXECUTE
    last_completed_mode = None
    for event in reversed(events):
        if event.get("event_type") == BuildEventType.MODE_SWITCHED.value:
            mode_str = event.get("mode", "plan")
            last_completed_mode = BuildMode.PLAN if mode_str == "plan" else BuildMode.EXECUTE
            current_mode = last_completed_mode
            break

    return ResumeState(
        build_id=build_id,
        workflow_id=workflow_id,
        intent=intent,
        config=config,
        last_iteration=last_iteration,
        current_mode=current_mode,
        start_timestamp=start_timestamp,
        last_failures=last_failures,
        doom_loop_counter=doom_loop_counter,
        last_gate_results_signature=last_gate_results_signature,
        build_dir=build_dir,
    )


def print_resume_summary(state: ResumeState) -> None:
    """Print summary of resumed build state."""
    print(f"[Builder] Resuming build: {state.build_id}")
    print(f"[Builder] Workflow: {state.workflow_id}")
    print(f"[Builder] Last iteration: {state.last_iteration}")
    print(f"[Builder] Current mode: {state.current_mode.value}")

    if state.last_failures:
        print(f"[Builder] Previous failures: {len(state.last_failures)}")
        for failure in state.last_failures[-2:]:
            print(f"  • {failure}")

    if state.doom_loop_counter > 0:
        print(f"[Builder] Doom loop counter: {state.doom_loop_counter}")

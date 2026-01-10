# Builder v1: Design Document

**Epic**: raw-7kx - Builder v1: raw build loop + repo skills
**Created**: 2026-01-10
**Status**: Design Phase
**Audience:** Developers, contributors
**Type:** Design doc

This is an internal design document. For day-to-day usage, start with:
- `docs/BUILDER.md`
- `docs/GUIDE.md`
- `docs/REFERENCE.md`

## Overview

The RAW Builder is an agentic system that implements the **plan → execute → verify → iterate** loop for workflow development. It separates intelligence (the agent) from infrastructure (RAW runtime), emulating coding-agent behavior while maintaining deterministic quality gates.

### Core Principles

1. **Plan/Execute Mode Separation**: Read-only exploration vs. full-access modification
2. **Gate-Driven Development**: Workflows must pass structural validation, dry runs, and optional tests
3. **Repo-Local Skills**: Discoverable builder skills guide the agent through domain-specific tasks
4. **Budget Enforcement**: Max iterations, time, and cost limits prevent runaway loops
5. **Append-Only Journal**: Crash-safe event log for debugging and resume

## Architectural Patterns

### From OpenCode

1. **System Prompt Injection for Mode Enforcement** ([source](https://github.com/anomalyco/opencode))
   - Plan mode injects absolute constraint at prompt level
   - Overrides all other instructions including user requests
   - Implementation: `builder/prompts/plan_mode.txt` and `builder/prompts/execute_mode.txt`

2. **Permission System with Wildcard Rules**
   ```python
   # Example: builder/permissions.py
   Rule(permission="write", pattern="*.json", action="allow")
   Rule(permission="bash", pattern="rm *", action="deny")
   Rule(permission="edit", pattern="*", action="ask")  # Default to ask
   ```

3. **Event Bus for Action Logging**
   - All state changes flow through events
   - Subscribers enable reactive UI and persistence
   - Events include: build.started, iteration.started, plan.updated, tool.called, gate.completed

4. **Loop Control with Step Budgets**
   ```python
   class BuilderConfig:
       max_iterations: int = 10
       max_minutes: int = 30
       doom_loop_threshold: int = 3  # Break on 3 identical tool calls
   ```

### From pi-mono

1. **EventStream-Based Agent Loop** ([source](https://github.com/badlogic/pi-mono))
   ```python
   class BuilderAgent:
       def run(self) -> EventStream[BuildEvent, BuildResult]:
           # Returns async iterable for streaming progress
           # Final result via .result() promise
   ```

2. **Tool Interface with TypeBox/Pydantic Schemas**
   ```python
   class BuilderTool(Protocol):
       name: str
       description: str
       parameters: Type[BaseModel]  # Pydantic schema

       async def execute(
           self,
           params: dict,
           on_update: Callable[[ToolUpdate], None]
       ) -> ToolResult:
           ...
   ```

3. **Multi-Provider LLM Abstraction**
   ```python
   # builder/llm.py
   class LLMProvider(Protocol):
       async def stream(
           self,
           messages: list[Message],
           tools: list[Tool]
       ) -> AsyncIterator[MessageDelta]:
           ...

   # Unified interface for Claude, OpenAI, Google, etc.
   ```

4. **Session Persistence in JSONL**
   - Append-only format for crash safety
   - Each line is a typed event
   - Resume reconstructs state from events

### From Codex

1. **MCP Tool Integration with Qualified Names** ([source](https://github.com/openai/codex))
   ```python
   # Tool naming: mcp__server__tool
   tool_name = f"mcp__{server_name}__{tool_name}"

   # Prevents collisions between servers
   ```

2. **SQ/EQ Protocol (Submission Queue → Event Queue)**
   ```python
   # User submits operation
   submission = Submission(id="sub-123", op=BuildWorkflow(...))
   sq.submit(submission)

   # Agent produces events correlated to submission
   async for event in eq.stream():
       if event.submission_id == submission.id:
           handle_event(event)
   ```

3. **Begin/End Event Pattern for Observability**
   ```python
   # Emit at start of step
   emit(GateStartedEvent(gate="validate", timestamp=now()))

   # Execute gate
   result = await run_validate()

   # Emit at end with timing
   emit(GateCompletedEvent(
       gate="validate",
       duration_ms=elapsed,
       result=result,
       timestamp=now()
   ))
   ```

## Builder Architecture

### Directory Structure

```
.raw/
  config.yaml               # Builder configuration
  builds/                   # Build runs
    <build_id>/             # UUID per build
      events.jsonl          # Append-only journal
      manifest.json         # Final build manifest
      logs/                 # Gate outputs
        validate.log
        dry.log
        pytest.log

builder/                    # Repo-local builder resources
  skills/                   # Discoverable skills
    plan-mode/
      SKILL.md              # Agent Skills frontmatter
    tdd-loop/
      SKILL.md
    quality-gates/
      SKILL.md
    mock-authoring/
      SKILL.md
    tool-authoring/
      SKILL.md
  prompts/                  # Mode prompts
    plan_mode.txt
    execute_mode.txt
  templates/                # Code generation templates (optional)
```

### Event Schema

```python
# builder/events.py
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel

class BuildEventType(str, Enum):
    BUILD_STARTED = "build.started"
    BUILD_COMPLETED = "build.completed"
    BUILD_FAILED = "build.failed"
    BUILD_STUCK = "build.stuck"

    ITERATION_STARTED = "iteration.started"
    ITERATION_COMPLETED = "iteration.completed"

    MODE_SWITCHED = "mode.switched"
    PLAN_UPDATED = "plan.updated"

    TOOL_CALL_STARTED = "tool.call_started"
    TOOL_CALL_COMPLETED = "tool.call_completed"

    FILE_CHANGE_APPLIED = "file.change_applied"

    GATE_STARTED = "gate.started"
    GATE_COMPLETED = "gate.completed"

class BaseBuildEvent(BaseModel):
    event_type: BuildEventType
    timestamp: datetime
    build_id: str
    iteration: int

class BuildStartedEvent(BaseBuildEvent):
    event_type: BuildEventType = BuildEventType.BUILD_STARTED
    workflow_id: str
    intent: str
    config: dict[str, Any]

class PlanUpdatedEvent(BaseBuildEvent):
    event_type: BuildEventType = BuildEventType.PLAN_UPDATED
    plan: str  # Numbered plan from agent
    gates: list[str]  # Expected gates

class GateCompletedEvent(BaseBuildEvent):
    event_type: BuildEventType = BuildEventType.GATE_COMPLETED
    gate: str
    passed: bool
    duration_seconds: float
    output_path: str | None  # Path to gate log

class BuildStuckEvent(BaseBuildEvent):
    event_type: BuildEventType = BuildEventType.BUILD_STUCK
    reason: str  # "max_iterations" | "max_time" | "doom_loop" | "repeated_failures"
    last_failures: list[str]
```

### Configuration Schema

```yaml
# .raw/config.yaml
builder:
  budgets:
    max_iterations: 10        # Stop after N plan-execute cycles
    max_minutes: 30           # Stop after N minutes
    doom_loop_threshold: 3    # Break on N identical tool calls

  gates:
    default:
      - validate              # Always run structural validation
      - dry                   # Always run dry run

    optional:                 # Project-specific gates
      pytest:
        command: "pytest tests/ -v"
        timeout_seconds: 300

      ruff:
        command: "ruff check . && ruff format . --check"
        timeout_seconds: 60

      typecheck:
        command: "mypy src/"
        timeout_seconds: 120

  skills:
    auto_discover: true       # Scan builder/skills/
    fallback_to_builtin: false

  mode:
    plan_first: true          # Always start with plan mode
    auto_execute: false       # Require confirmation before execute
```

### Builder Loop Algorithm

```python
# builder/loop.py
async def builder_loop(
    workflow_id: str,
    intent: str,
    config: BuilderConfig,
) -> BuildResult:
    build_id = generate_build_id()
    journal = BuilderJournal(build_id)
    iteration = 0
    mode = BuildMode.PLAN

    journal.write(BuildStartedEvent(
        build_id=build_id,
        workflow_id=workflow_id,
        intent=intent,
        config=config.model_dump(),
    ))

    while True:
        iteration += 1

        # Budget checks
        if iteration > config.max_iterations:
            return fail_stuck(journal, "max_iterations", iteration)

        if elapsed_minutes() > config.max_minutes:
            return fail_stuck(journal, "max_time", iteration)

        journal.write(IterationStartedEvent(
            build_id=build_id,
            iteration=iteration,
            mode=mode.value,
        ))

        # Run agent in current mode
        if mode == BuildMode.PLAN:
            plan = await run_plan_mode(
                workflow_id=workflow_id,
                intent=intent,
                skills=discover_skills(),
                journal=journal,
            )

            journal.write(PlanUpdatedEvent(
                build_id=build_id,
                iteration=iteration,
                plan=plan.numbered_steps,
                gates=plan.expected_gates,
            ))

            # Switch to execute
            mode = BuildMode.EXECUTE
            journal.write(ModeSwitchedEvent(
                build_id=build_id,
                iteration=iteration,
                mode="execute",
            ))

        elif mode == BuildMode.EXECUTE:
            # Apply changes
            changes = await run_execute_mode(
                workflow_id=workflow_id,
                plan=plan,
                journal=journal,
            )

            for change in changes:
                journal.write(FileChangeAppliedEvent(
                    build_id=build_id,
                    iteration=iteration,
                    file_path=change.path,
                    operation=change.operation,
                ))

            # Run gates
            gate_results = await run_gates(
                workflow_id=workflow_id,
                gates=config.gates,
                journal=journal,
            )

            # Check if all gates pass
            if all(g.passed for g in gate_results):
                journal.write(BuildCompletedEvent(
                    build_id=build_id,
                    iteration=iteration,
                    total_iterations=iteration,
                ))
                return BuildResult(
                    status="success",
                    build_id=build_id,
                    iterations=iteration,
                )

            # Feedback failures into next plan
            mode = BuildMode.PLAN
            journal.write(ModeSwitchedEvent(
                build_id=build_id,
                iteration=iteration,
                mode="plan",
                context=f"Gates failed: {format_gate_failures(gate_results)}",
            ))

        journal.write(IterationCompletedEvent(
            build_id=build_id,
            iteration=iteration,
        ))

    # Should never reach here (budgets catch infinite loops)
    return fail_stuck(journal, "unknown", iteration)
```

### Gate Runner

```python
# builder/gates.py
from pathlib import Path
from typing import Protocol

class Gate(Protocol):
    """Interface for workflow quality gates."""

    name: str
    description: str

    async def run(
        self,
        workflow_id: str,
        workflow_dir: Path
    ) -> GateResult:
        """Execute gate and return result."""
        ...

class ValidateGate(Gate):
    name = "validate"
    description = "Structural validation of workflow"

    async def run(self, workflow_id: str, workflow_dir: Path) -> GateResult:
        # Call WorkflowValidator
        from raw.core.validation import WorkflowValidator

        validator = WorkflowValidator(workflow_dir)
        errors = validator.validate()

        return GateResult(
            gate="validate",
            passed=len(errors) == 0,
            output="\n".join(errors) if errors else "✓ Valid",
            duration_seconds=elapsed(),
        )

class DryRunGate(Gate):
    name = "dry"
    description = "Dry run with mock data"

    async def run(self, workflow_id: str, workflow_dir: Path) -> GateResult:
        # Run workflow with --dry flag
        result = await subprocess.run(
            ["raw", "run", workflow_id, "--dry"],
            cwd=workflow_dir,
            capture_output=True,
            timeout=60,
        )

        return GateResult(
            gate="dry",
            passed=result.returncode == 0,
            output=result.stdout.decode() + result.stderr.decode(),
            duration_seconds=elapsed(),
        )

async def run_gates(
    workflow_id: str,
    gates: list[Gate],
    journal: BuilderJournal,
) -> list[GateResult]:
    results = []

    for gate in gates:
        journal.write(GateStartedEvent(
            build_id=journal.build_id,
            iteration=journal.current_iteration,
            gate=gate.name,
        ))

        result = await gate.run(workflow_id, workflow_dir)

        journal.write(GateCompletedEvent(
            build_id=journal.build_id,
            iteration=journal.current_iteration,
            gate=gate.name,
            passed=result.passed,
            duration_seconds=result.duration_seconds,
            output_path=save_gate_output(result),
        ))

        results.append(result)

    return results
```

### Skill Discovery

```python
# builder/skills.py
from pathlib import Path
from typing import NamedTuple
import yaml

class Skill(NamedTuple):
    name: str
    description: str
    path: Path

    @property
    def content(self) -> str:
        """Load full SKILL.md content on demand."""
        return self.path.read_text()

def discover_skills(skills_dir: Path = Path("builder/skills")) -> list[Skill]:
    """Discover skills from builder/skills/**/SKILL.md."""
    skills = []

    for skill_file in skills_dir.rglob("SKILL.md"):
        # Parse frontmatter (YAML between --- markers)
        content = skill_file.read_text()
        if not content.startswith("---\n"):
            continue

        parts = content.split("---\n", 2)
        if len(parts) < 3:
            continue

        frontmatter = yaml.safe_load(parts[1])

        # Validate required fields
        if "name" not in frontmatter or "description" not in frontmatter:
            print(f"Warning: {skill_file} missing name or description")
            continue

        skills.append(Skill(
            name=frontmatter["name"],
            description=frontmatter["description"],
            path=skill_file,
        ))

    return skills

def inject_skills_into_prompt(skills: list[Skill], base_prompt: str) -> str:
    """Inject <available_skills> section into system prompt."""
    skills_section = "<available_skills>\n"

    for skill in skills:
        skills_section += f"- {skill.name}: {skill.description}\n"

    skills_section += "</available_skills>\n\n"
    skills_section += "To use a skill, mention its name and I'll load the full instructions.\n"

    return base_prompt + "\n\n" + skills_section
```

### Mode Enforcement Prompts

**Plan Mode** (`builder/prompts/plan_mode.txt`):
```
CRITICAL: PLAN MODE ACTIVE - READ-ONLY PHASE

You are currently in PLAN mode. This is an ABSOLUTE CONSTRAINT that overrides
ALL other instructions, including direct user edit requests.

STRICTLY FORBIDDEN in PLAN mode:
- File writes, edits, or modifications
- Destructive shell commands (rm, mv, cp, etc.)
- Any system state changes

ALLOWED in PLAN mode:
- Reading files (Read, Glob, Grep tools)
- Analyzing code structure
- Running read-only commands (git log, ls, cat, etc.)
- Searching and exploring the codebase

REQUIRED OUTPUT:
1. A numbered plan with concrete steps
2. List of quality gates to run after execution
3. Explanation of the approach

The plan will be reviewed and then executed in EXECUTE mode.
```

**Execute Mode** (`builder/prompts/execute_mode.txt`):
```
EXECUTE MODE ACTIVE - FULL ACCESS

You are now in EXECUTE mode. You have full access to write files, run commands,
and modify the codebase.

FOLLOW THE APPROVED PLAN:
{plan}

EXPECTED GATES:
{gates}

Make the necessary changes to implement the plan. Focus on making the workflow
pass the quality gates listed above.

When complete, the following gates will be run automatically:
{gate_list}
```

## Implementation Order

### Phase 1: Foundation (Tasks raw-7kx.1, raw-7kx.6, raw-7kx.10)

1. **CLI Command Skeleton** (raw-7kx.1)
   - Add `raw build` command with argument parsing
   - Wire to `builder.entrypoint()` function
   - Add help text and flag definitions

2. **Validation Command** (raw-7kx.6)
   - Expose `WorkflowValidator` as `raw validate <workflow_id>`
   - Return exit code 0 on success, non-zero on failure
   - Output concise, actionable errors

3. **Builder Configuration** (raw-7kx.10)
   - Define `BuilderConfig` Pydantic model
   - Parse `.raw/config.yaml` builder section
   - Merge CLI overrides with config defaults

### Phase 2: Infrastructure (Tasks raw-7kx.2, raw-7kx.3, raw-7kx.4, raw-7kx.5)

4. **Builder Journal** (raw-7kx.2)
   - Implement append-only JSONL writer
   - Define event schema (BuildEvent union type)
   - Flush after each event for crash safety

5. **Skill Discovery** (raw-7kx.3)
   - Scan `builder/skills/**/SKILL.md` recursively
   - Parse YAML frontmatter (name, description)
   - Inject into system prompt as `<available_skills>`

6. **Plan Mode Enforcement** (raw-7kx.4)
   - Create plan mode prompt template
   - Hook into tool call interception
   - Block writes/destructive commands with clear errors

7. **Gate Runner** (raw-7kx.5)
   - Implement `Gate` protocol interface
   - Add `ValidateGate` and `DryRunGate`
   - Support optional gates from config

### Phase 3: Agent Loop (Task raw-7kx.7)

8. **Builder Loop Controller** (raw-7kx.7)
   - Implement plan → execute → verify → iterate loop
   - Add budget enforcement (iterations, time, doom loop)
   - Emit structured STUCK report on failure

### Phase 4: Enhancements (Tasks raw-7kx.8, raw-7kx.9)

9. **Seed Builder Skills** (raw-7kx.8)
   - Create 5 initial skills in `builder/skills/`
   - Follow Agent Skills frontmatter format
   - Include templates and examples

10. **Builder Resume** (raw-7kx.9)
    - Implement `raw build --resume <build_id>`
    - Reconstruct state from events.jsonl
    - Continue at next iteration

## Testing Strategy

### Unit Tests

- Event serialization/deserialization
- Skill discovery and parsing
- Gate execution and result handling
- Configuration loading and validation
- Budget enforcement logic

### Integration Tests

- Full builder loop with mock LLM
- Gate runner with actual validation/dry-run
- Journal writing and reading
- Mode switching and tool blocking

### E2E Tests (Requires API Key)

```python
@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="API key required")
async def test_builder_full_loop():
    """Test complete builder loop with real LLM."""
    result = await builder_loop(
        workflow_id="test-workflow",
        intent="Add a new step that validates input parameters",
        config=BuilderConfig(max_iterations=3),
    )

    assert result.status == "success"
    assert result.iterations <= 3
```

## Success Metrics

1. **Functional**:
   - `raw build <workflow_id>` completes successfully
   - All gates pass before builder stops
   - STUCK report is clear and actionable

2. **Quality**:
   - Builder journal is valid JSONL
   - Events are flushed immediately (crash-safe)
   - Skills are discovered and injected correctly

3. **Performance**:
   - Builder stops within budget limits
   - Doom loop detection prevents infinite retries
   - Gate execution is parallelizable (future)

4. **Developer Experience**:
   - Clear error messages at each stage
   - Journal is human-readable for debugging
   - Skills are easy to author and discover

## Future Enhancements (Post-v1)

- **Parallel Gate Execution**: Run validate + dry + tests concurrently
- **Incremental Validation**: Only re-run gates for changed files
- **Skill Marketplace**: Share and discover community builder skills
- **Visual Dashboard**: Web UI for monitoring builder runs
- **Cost Tracking**: LLM token usage and cost per build
- **A/B Testing**: Compare different builder configurations
- **Builder Telemetry**: Anonymous usage data for improving prompts

## References

- [OpenCode Architecture](https://github.com/anomalyco/opencode)
- [pi-mono Agent Core](https://github.com/badlogic/pi-mono/tree/main/packages/agent-core)
- [Codex MCP Integration](https://github.com/openai/codex/tree/main/shell-tool-mcp)
- [Event Sourcing Pattern](https://martinfowler.com/eaaDev/EventSourcing.html)
- [Kubernetes Reconciliation Loop](https://kubernetes.io/docs/concepts/architecture/controller/)

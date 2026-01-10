# Builder Guide

The RAW builder is an agentic system that iteratively develops workflows through plan → execute → verify cycles.

## Overview

The builder automates workflow development by:
1. **Planning** in read-only mode (analyzing requirements, designing changes)
2. **Executing** changes to workflow files and tools
3. **Verifying** with quality gates (validate, dry run, optional tests)
4. **Iterating** until all gates pass or budget exhausted

## Basic Usage

```bash
# Start a build
raw build my-workflow

# With custom budget
raw build my-workflow --max-iterations 10 --max-minutes 30
```

The builder will:
- Create a build directory at `.raw/builds/<build-id>/`
- Write an event journal to `events.jsonl`
- Save gate outputs to `logs/<gate>.log`
- Report final status (success, failed, or stuck)

## Resume Functionality

Builds can be resumed if interrupted:

```bash
# Resume specific build
raw build --resume build-20240110-123456-abc123

# Resume most recent build
raw build --last
```

Resume reconstructs state from the journal:
- Current iteration and mode (plan/execute)
- Previous failures and doom loop counter
- Time budget tracking

## Quality Gates

### Default Gates

Always run on every iteration:

1. **validate** - Structural validation
   - Checks PEP 723 metadata exists
   - Verifies BaseWorkflow subclass
   - Ensures run() method implemented
   - Validates imported tools exist

2. **dry** - Dry run with mocks
   - Executes workflow with mock data
   - Requires `dry_run.py` with mock functions
   - No real API calls or external dependencies

### Optional Gates

Configure in `.raw/config.yaml`:

```yaml
builder:
  gates:
    default:
      - validate
      - dry
    optional:
      pytest:
        command: "pytest test.py -v"
        timeout_seconds: 60
      ruff:
        command: "ruff check . && ruff format . --check"
        timeout_seconds: 30
      typecheck:
        command: "mypy run.py"
        timeout_seconds: 60
```

## Builder Configuration

Full configuration schema in `.raw/config.yaml`:

```yaml
builder:
  budgets:
    max_iterations: 10      # Max plan-execute cycles
    max_minutes: 30         # Max wall time
    doom_loop_threshold: 3  # Max repeated identical failures

  gates:
    default:
      - validate
      - dry
    optional: {}

  skills:
    discovery_paths:
      - builder/skills      # Where to find builder skills

  mode:
    plan_first: true        # Start in plan mode (vs execute)
```

## Builder Skills

The builder is guided by skills in `builder/skills/`:

- **plan-mode** - Structured plan format (Analysis/Approach/Steps/Gates)
- **tdd-loop** - Test-driven development cycle
- **quality-gates** - Understanding gate failures and fixes
- **mock-authoring** - Writing effective dry_run.py mocks
- **tool-authoring** - Creating reusable tools

Skills are automatically discovered and injected into the agent's context.

## Build Lifecycle

```
┌─────────────────────────────────────────────────────────┐
│ START: raw build my-workflow                            │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Build Started        │
              │ build-id generated   │
              │ Journal created      │
              └──────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Iteration N          │
              └──────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌────────────────┐              ┌────────────────┐
│ PLAN MODE      │              │ EXECUTE MODE   │
│ (Read-only)    │──────────────▶│ (Full access)  │
│                │              │                │
│ • Analyze      │              │ • Write code   │
│ • Design       │              │ • Edit files   │
│ • Create plan  │              │ • Add tools    │
└────────────────┘              └────────────────┘
                                        │
                                        ▼
                                ┌────────────────┐
                                │ VERIFY         │
                                │ Run gates      │
                                └────────────────┘
                                        │
                    ┌───────────────────┴────────────────┐
                    ▼                                    ▼
            ┌───────────────┐                   ┌───────────────┐
            │ All gates     │                   │ Some gates    │
            │ passed        │                   │ failed        │
            └───────────────┘                   └───────────────┘
                    │                                    │
                    ▼                                    ▼
            ┌───────────────┐               ┌────────────────────┐
            │ SUCCESS       │               │ Back to PLAN MODE  │
            │ Exit code: 0  │               │ with failure info  │
            └───────────────┘               └────────────────────┘
                                                        │
                                    ┌───────────────────┴────────────┐
                                    ▼                                ▼
                            ┌──────────────┐                ┌─────────────┐
                            │ Budget OK    │                │ Budget hit  │
                            │ Continue     │                │ STUCK       │
                            └──────────────┘                │ Exit: 2     │
                                                            └─────────────┘
```

## Exit Codes

- **0 (success)** - All gates passed
- **1 (failed)** - Execution error or critical failure
- **2 (stuck)** - Budget exhausted (max iterations, time, or doom loop)

## Journal Format

Each build creates `.raw/builds/<build-id>/events.jsonl` with one event per line:

```jsonl
{"event_type":"build.started","timestamp":1704931200.0,"build_id":"build-...","workflow_id":"my-workflow",...}
{"event_type":"iteration.started","timestamp":1704931201.0,"iteration":1,"mode":"plan",...}
{"event_type":"plan.updated","timestamp":1704931205.0,"iteration":1,"plan":"## Analysis\n...",...}
{"event_type":"mode.switched","timestamp":1704931206.0,"mode":"execute",...}
{"event_type":"gate.started","timestamp":1704931220.0,"gate":"validate",...}
{"event_type":"gate.completed","timestamp":1704931221.0,"gate":"validate","passed":true,...}
{"event_type":"build.completed","timestamp":1704931250.0,"total_iterations":3,...}
```

Events enable:
- Resume from any point
- Full build observability
- Debugging and replay

## Troubleshooting

### Build stuck in doom loop

**Symptom**: Same gate failures repeated 3+ times

**Causes**:
- Tests are too strict or incorrect
- Real bug in implementation
- Gate itself is broken

**Fix**:
1. Check `.raw/builds/<build-id>/logs/<gate>.log` for details
2. Fix the underlying issue manually
3. Resume build with `raw build --last`

### Build hits max iterations

**Symptom**: Build stops after N iterations without passing gates

**Causes**:
- Complex workflow requiring more iterations
- Gates are failing for fixable reasons

**Fix**:
1. Increase budget: `raw build --max-iterations 20`
2. Review gate logs to understand failures
3. Fix manually if needed, then resume

### Resume fails with "Cannot resume completed build"

**Symptom**: `raw build --last` fails because build already finished

**Fix**:
- Start a new build: `raw build <workflow-id>`
- Completed builds cannot be resumed

## Best Practices

1. **Start with validation** - Ensure workflow structure is correct before building
   ```bash
   raw show my-workflow --validate
   ```

2. **Use dry runs** - Test with mocks before real execution
   ```bash
   raw run my-workflow --dry
   ```

3. **Incremental development** - Build in small steps, verify often

4. **Monitor budget** - Set realistic iteration/time limits based on complexity

5. **Review journals** - Use event logs to understand build behavior
   ```bash
   cat .raw/builds/<build-id>/events.jsonl | jq .
   ```

6. **Configure optional gates** - Add pytest, ruff, typecheck for higher quality

## Integration with Claude Code

The builder is designed to be used by AI agents. When integrated with Claude Code:

1. Agent runs `raw build <workflow-id>`
2. Builder handles the plan-execute-verify loop
3. Agent receives final status (success/failed/stuck)
4. Agent reports outcome to user

Skills guide the agent on:
- How to structure plans
- How to write tests
- How to author mocks
- How to create reusable tools

This enables autonomous workflow development with human oversight.

# RAW: Two Layers (Builder + Runner)

RAW is designed as two coupled but separate layers, distinguishing the **creation** of code from its **execution**.

| Layer | Component | Role | Responsibility |
| :--- | :--- | :--- | :--- |
| **Layer 1** | **Builder** | Architect | Iterative workflow construction, validation, and self-correction. |
| **Layer 2** | **Runner** | Operator | Deterministic execution, safety, and operational observability. |

---

## Layer 1: Builder (Workflow Construction)

**Entry point:** `raw build <workflow-id>`

The Builder acts as an autonomous engineer. Its goal is to translate a high-level intent into functional, verified code.

### The Construction Loop
The builder runs an explicit **Plan → Execute → Verify** cycle:

1.  **Plan Mode:** Analyzes the current state and produces a numbered plan (read-only analysis).
2.  **Execute Mode:** Applies file changes according to the plan.
3.  **Verify:** Runs "Quality Gates" to validate the changes.
4.  **Iterate:** Failures are fed back into the next planning cycle until all gates pass or budgets are exhausted.

### Main Features
-   **Quality Gates:**
    -   *Default:* `validate` (structural checks), `dry` (simulated run).
    -   *Custom:* Project-specific shell commands defined in `.raw/config.yaml`.
-   **Budgets & Safety:**
    -   Limits on `max_iterations` and `max_minutes`.
    -   "Doom loop" detection to halt if the builder repeats the same failure.
-   **Skills (Guidance):**
    -   The builder learns from repo-local skills found in `builder/skills/**/SKILL.md`.
    -   These guide architectural decisions (e.g., "How to write a mock").
-   **Resume Capability:**
    -   Use `raw build --resume <build-id>` or `raw build --last` to pick up where a previous session left off.
    -   State is durable, stored in `.raw/builds/<build-id>/events.jsonl`.

> **Implementation Note:** The loop control, journaling, and gates are implemented, but the actual "agent" integrations for plan/execute steps are currently scaffolds (`src/raw/builder/loop.py`). These are the integration points for the LLM-backed engine.

---

## Layer 2: Runner (Workflow Execution)

**Entry point:** `raw run <workflow-id> [args...]`

The Runner is the runtime engine. It ensures that the workflows produced by the Builder execute reliably in production or local environments.

### Execution Model
-   **Deterministic Base:** Workflows are standard Python scripts. They run linearly by default.
-   **Agentic Opt-in:** "Agentic" capabilities (loops, reasoning) are library features (`raw_runtime.agentic`), not intrinsic to the runner itself.
-   **Delegation:** Execution is handled by the **engine runner** (`src/raw/engine/runner.py`), which manages process injection and isolation.

### Safety & Observability
-   **Dry-Run Mode:**
    -   `raw run <id> --dry --init`: Generates a `dry_run.py` template.
    -   `raw run <id> --dry`: Executes the workflow using mocks to verify logic without side effects.
-   **Event Stream:**
    -   Workflows emit structured events (steps, artifacts, approvals) via `raw_runtime`.
    -   These events drive the CLI output and any attached UI.

---

## Examples

### 1. Typical Development Loop
A session moving from intent (Builder) to execution (Runner):

```bash
raw init
raw create stock-report --intent "Fetch prices, compute indicators, write report"

# Layer 1: Construct the workflow
raw build stock-report

# Layer 2: Verify and Run
raw run stock-report --dry --init  # Setup mocks
raw run stock-report --dry         # Verify logic
raw run stock-report --ticker AAPL # Real execution
```

### 2. Minimal Workflow Structure
The code artifact produced by the Builder for the Runner:

```python
from pydantic import BaseModel, Field
from raw_runtime import BaseWorkflow, step

class Params(BaseModel):
    name: str = Field(..., description="Name to greet")

class Workflow(BaseWorkflow[Params]):
    @step("greet")
    def greet(self) -> dict:
        return {"message": f"Hello, {self.params.name}!"}

    def run(self) -> int:
        self.save("output.json", self.greet())
        return 0

if __name__ == "__main__":
    Workflow.main()
```

### 3. Configuring Builder Gates
Defining custom checks in `.raw/config.yaml`:

```yaml
builder:
  gates:
    default: [validate, dry]
    optional:
      pytest:
        command: "pytest -q"
        timeout_seconds: 300
```
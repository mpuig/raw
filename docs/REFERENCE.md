# RAW Reference

**Audience:** Users, agents, developers
**Type:** Reference

This document is the canonical reference for RAW’s core surfaces:

- CLI (`raw …`)
- Workflow and tool layout
- `raw_runtime` (execution/runtime primitives)
- `raw_ai` (LLM-powered steps; core feature)
- `raw.sdk` (programmatic construction)

---

## CLI (Core Commands)

Run `raw --help` for the full list. Common commands:

- `raw init` — initialize `.raw/` in the project
- `raw init --hooks` — also install Claude Code hooks/skills
- `raw create <name> --intent "..."` — create a workflow scaffold
- `raw create <name> --tool -d "..."` — create a reusable tool scaffold
- `raw search "query"` — search tools by description
- `raw list` / `raw list tools` — list workflows/tools
- `raw show <id-or-name>` — inspect a workflow/tool
- `raw run <workflow> [args...]` — run a workflow
- `raw run <workflow> --dry [args...]` — run with mocks (`dry_run.py`)
- `raw build <workflow>` — run the builder loop (plan → execute → verify)

---

## Project Layout

Typical structure:

```
project/
├── tools/                       # reusable libraries (imported by workflows)
│   └── <tool-name>/
│       ├── config.yaml
│       ├── tool.py
│       └── __init__.py
└── .raw/
    ├── config.yaml              # project + builder configuration
    └── workflows/
        └── <workflow-id>/
            ├── config.yaml
            ├── run.py
            ├── dry_run.py        # optional; for --dry runs
            ├── mocks/            # optional; mock data/helpers for dry runs
            └── runs/             # per-run artifacts (when isolated runs are enabled)
```

---

## Workflows

### `run.py`

Workflows are regular Python scripts (recommended pattern: `raw_runtime.BaseWorkflow`).

- Use **PEP 723** header for dependencies (so runs are reproducible).
- Use `BaseWorkflow.main()` for CLI entry and consistent logging.
- Save outputs to `results/` (or use `BaseWorkflow.save()`).

Minimal shape:

```python
from pydantic import BaseModel, Field
from raw_runtime import BaseWorkflow, step

class Params(BaseModel):
    name: str = Field(..., description="Name")

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

### `dry_run.py` (recommended)

Dry runs are for verification and iteration.

- `raw run <workflow> --dry` runs `dry_run.py`.
- `raw run <workflow> --dry --init` generates a template.
- Keep dry runs side-effect-free: no real network calls, no real credentials required.

---

## Tools (Reusable Libraries)

Tools are Python packages under `tools/` and should be reusable across workflows.

### Create a tool

```bash
raw create my_tool --tool -d "What this tool does"
```

### Install from git

```bash
raw install https://github.com/user/my-tool
raw install https://github.com/user/my-tool --ref v1.0.0
raw uninstall my_tool
```

### Use a tool from a workflow

```python
from tools.my_tool import fetch_data
```

RAW can snapshot tools into the run directory for reproducibility (`_tools/`).

---

## `raw_runtime` (Runtime API)

### Core primitives

- `BaseWorkflow[ParamsT]` — base class for workflows
- `@step("name")` — structured step timing + event emission
- `@retry(...)` — retry with backoff for flaky operations
- `@cache_step` / `cache_step(...)` — cache deterministic steps
- `WorkflowContext` — emits events and builds run manifests

See `src/raw_runtime/__init__.py:1` for the public surface.

### Common `BaseWorkflow` helpers

- `results_dir` — ensures `results/` exists
- `save(path, data)` — persist JSON/text artifacts under `results/`
- `success(...)`, `error(...)`, `complete(...)` — explicit completion signals (where supported)

### Human-in-the-loop

- `wait_for_approval(...)` / `wait_for_approval_async(...)`
- `wait_for_webhook(...)`

These emit approval events and block (or await) until approval arrives (interactive `raw run` or server mode).

### Events and observability

Workflows emit events such as:

- step lifecycle: `StepStartedEvent`, `StepCompletedEvent`, `StepFailedEvent`
- artifacts: `ArtifactCreatedEvent`
- workflow lifecycle: `WorkflowStartedEvent`, `WorkflowCompletedEvent`
- approvals: `ApprovalRequestedEvent`, `ApprovalReceivedEvent`

See `docs/ARCHITECTURE.md` for the full event-driven model (`raw run` vs `raw serve`).

---

## `raw_ai` (AI Steps — Core Feature)

Install AI dependencies:

```bash
uv add raw[ai]
```

### `@agent` (structured LLM calls)

`raw_ai.agent` turns a function/method into an LLM-powered step with structured output.

- docstring → system prompt
- function args → user message payload
- `result_type` (Pydantic model) → output schema
- optional `tools=[...]` → functions the model can call
- `retries` handles schema-validation failures

Example:

```python
from pydantic import BaseModel
from raw_ai import agent

class Summary(BaseModel):
    title: str
    bullets: list[str]

@agent(result_type=Summary, model="gpt-4o-mini")
def summarize(self, text: str) -> Summary:
    """Summarize the text into a title and bullets."""
    ...
```

### Tools for agents

Convert a plain Python function into an AI-callable tool definition:

```python
from raw_ai import to_ai_tool

tool_def = to_ai_tool(my_function)
```

### Models and environment variables

Set the relevant provider key for the model you choose:

- OpenAI models: `OPENAI_API_KEY`
- Anthropic models: `ANTHROPIC_API_KEY`
- Groq models: `GROQ_API_KEY`

Model selection is based on model name (e.g., `gpt-*` vs `claude-*`).

---

## `raw.sdk` (Programmatic Construction)

Use the SDK when you want to create workflows/tools from Python (e.g., agents generating workflows programmatically).

Common functions:

- `create_workflow(...)`, `list_workflows()`, `get_workflow(...)`
- `update_workflow(...)`, `delete_workflow(...)`
- `add_step(...)`

See `src/raw/sdk/` for implementations and types.

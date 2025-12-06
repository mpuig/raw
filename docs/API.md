# RAW Runtime API Reference

This document describes the `raw_runtime` module API for building RAW workflows.

## Installation

The `raw_runtime` module is included with RAW:

```bash
uv add raw
```

Or import it in your workflow scripts (PEP 723):

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["raw"]
# ///

from raw_runtime import step, retry, WorkflowContext
from raw_runtime.decorators import cache_step
```

---

## Decorators

### @step

Track step execution with timing, results, and error recording.

```python
from raw_runtime import step

@step("fetch_data")
def fetch_data(self):
    """Fetch data from API."""
    return {"data_points": 100}
```

**Parameters:**
- `name` (str): Step name for tracking and display

**Behavior:**
- Records step timing and results
- Integrates with `BaseWorkflow` for automatic tracking
- Enables retry and cache decorators

**Output:**
```
► [fetch_data] Starting...
✓ [fetch_data] Completed (0.25s)
```

---

### @retry

Add retry logic with configurable backoff strategies.

```python
from raw_runtime import step, retry

@step("api_call")
@retry(retries=3, backoff="exponential")
def api_call(self):
    """Call external API with retry."""
    return requests.get(url).json()
```

**Parameters:**
- `retries` (int, default=3): Maximum retry attempts
- `backoff` (str, default="exponential"): Strategy - "exponential", "linear", or "fixed"
- `retry_on` (tuple, default=(Exception,)): Exception types to retry on
- `base_delay` (float, default=1.0): Base delay in seconds

**Backoff Strategies:**
- `"exponential"`: delay = base_delay * 2^attempt (1s, 2s, 4s, 8s...)
- `"linear"`: delay = base_delay * (attempt + 1) (1s, 2s, 3s, 4s...)
- `"fixed"`: delay = base_delay (1s, 1s, 1s...)

**Example with specific exceptions:**
```python
@retry(retries=5, retry_on=(ConnectionError, TimeoutError), base_delay=2.0)
def fetch_with_timeout(self):
    return requests.get(url, timeout=10).json()
```

---

### @cache_step

Cache expensive computation results based on function arguments.

```python
from raw_runtime import step
from raw_runtime.decorators import cache_step

@step("calculate")
@cache_step
def calculate(self, data):
    """Expensive calculation - cached on subsequent calls."""
    return expensive_operation(data)
```

**Behavior:**
- Generates cache key from function name and argument hash
- Stores results in `.raw/cache/` directory (JSON format)
- Returns cached result if available, skips execution
- Prints `⚡ [cached] step_name` when using cached result

**Cache Location:**
```
.raw/cache/<step_name>_<args_hash>.json
```

**Note:** Only works when `WorkflowContext` is active with a cache directory.

---

## Combining Decorators

Decorators can be combined for resilient, tracked, cached steps:

```python
from raw_runtime import step, retry
from raw_runtime.decorators import cache_step

@step("fetch_and_process")
@retry(retries=3, backoff="exponential")
@cache_step
def fetch_and_process(self, ticker: str):
    """
    - Tracked by @step
    - Retries on failure via @retry
    - Results cached via @cache_step
    """
    data = yfinance.download(ticker)
    return process(data)
```

**Order matters:** `@step` should be outermost, then `@retry`, then `@cache_step`.

### @agent (LLM-Powered Steps)

Turn a workflow method into an LLM-powered step using PydanticAI. Requires `raw[ai]` extra.

```bash
uv add raw[ai]  # Installs pydantic-ai
```

```python
from pydantic import BaseModel
from raw_ai import agent

class SentimentResult(BaseModel):
    score: float  # -1 to 1
    label: str    # positive, negative, neutral
    reasoning: str

class MyWorkflow(BaseWorkflow):
    @agent(result_type=SentimentResult, model="gpt-4o-mini")
    def analyze(self, text: str) -> SentimentResult:
        """You are a sentiment analyst. Analyze the given text."""
        ...
```

**How it works:**
- **Docstring → System prompt**: The method's docstring becomes the LLM's instructions
- **Arguments → User message**: Method arguments are formatted as the user input
- **result_type → Structured output**: The Pydantic model defines the output schema

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `result_type` | `type[BaseModel]` | Required | Pydantic model for structured output |
| `model` | `str` | `"gpt-4o-mini"` | Model name |
| `tools` | `list[Callable]` | `None` | Functions the agent can call |
| `retries` | `int` | `3` | Retries on validation failure |
| `temperature` | `float` | `None` | Sampling temperature (0.0-2.0) |

**Supported models:**
- OpenAI: `gpt-4o`, `gpt-4o-mini`, `o1-preview` (requires `OPENAI_API_KEY`)
- Anthropic: `claude-3-5-sonnet-latest` (requires `ANTHROPIC_API_KEY`)
- Groq: `llama-3.1-70b-versatile` (requires `GROQ_API_KEY`)

See [AI_AGENTS.md](AI_AGENTS.md) for full documentation.

---

## WorkflowContext

Manages workflow execution state, step results, and artifacts.

### Creating a Context

```python
from raw_runtime import WorkflowContext

context = WorkflowContext(
    workflow_id="20251206-my-workflow-abc123",
    workflow_name="My Workflow",
    workflow_version="1.0.0",
    workflow_dir="/path/to/.raw/workflows/my-workflow",
)
```

### Using as Context Manager

```python
with WorkflowContext(...) as ctx:
    # Steps executed here are tracked
    result = my_step()

# Manifest automatically saved on exit
```

### Methods

#### add_step_result(result: StepResult)

Record a step execution result.

```python
from raw_runtime import StepResult, StepStatus

result = StepResult(
    name="fetch_data",
    status=StepStatus.SUCCESS,
    started_at=datetime.now(timezone.utc),
    ended_at=datetime.now(timezone.utc),
    duration_seconds=0.25,
    result={"data_points": 100},
)
context.add_step_result(result)
```

#### add_artifact(artifact: Artifact)

Register an output artifact.

```python
from raw_runtime import Artifact

artifact = Artifact(
    name="report",
    path="results/report.pdf",
    mime_type="application/pdf",
    size_bytes=12345,
)
context.add_artifact(artifact)
```

#### build_manifest() -> Manifest

Generate the execution manifest.

```python
manifest = context.build_manifest()
print(manifest.model_dump_json(indent=2))
```

#### finalize()

Save the manifest to disk. Called automatically when using context manager.

```python
context.finalize()
# Saves to: workflow_dir/.raw/manifest.json
```

### Global Context Access

```python
from raw_runtime import get_workflow_context, set_workflow_context

# Set context for current execution
set_workflow_context(context)

# Get current context (may be None)
ctx = get_workflow_context()
```

---

## Models

All models use Pydantic for validation and serialization.

### StepResult

Records execution result of a single step.

```python
from raw_runtime import StepResult, StepStatus

result = StepResult(
    name="fetch_data",
    status=StepStatus.SUCCESS,  # or FAILED, SKIPPED
    started_at=datetime.now(timezone.utc),
    ended_at=datetime.now(timezone.utc),
    duration_seconds=0.25,
    result={"key": "value"},  # Optional - success result
    error="Error message",     # Optional - failure message
    retries=0,                 # Number of retries attempted
)
```

### StepStatus

Enum for step execution status.

```python
from raw_runtime import StepStatus

StepStatus.SUCCESS  # Step completed successfully
StepStatus.FAILED   # Step failed with error
StepStatus.SKIPPED  # Step was skipped (e.g., cached)
```

### Artifact

Represents an output file produced by the workflow.

```python
from raw_runtime import Artifact

artifact = Artifact(
    name="chart",
    path="results/chart.png",
    mime_type="image/png",
    size_bytes=54321,
    created_at=datetime.now(timezone.utc),  # Optional
)
```

### Manifest

Complete execution record for a workflow run.

```python
from raw_runtime import Manifest

manifest = Manifest(
    workflow=WorkflowInfo(...),
    run=RunInfo(...),
    steps=[StepResult(...), ...],
    artifacts=[Artifact(...), ...],
    environment=EnvironmentInfo(...),
    logs=LogsInfo(...),
)

# Serialize to JSON
json_str = manifest.model_dump_json(indent=2)

# Load from JSON
manifest = Manifest.model_validate_json(json_str)
```

### WorkflowInfo

Workflow metadata.

```python
from raw_runtime import WorkflowInfo

info = WorkflowInfo(
    id="20251206-my-workflow-abc123",
    name="My Workflow",
    version="1.0.0",
)
```

### RunInfo

Execution run metadata.

```python
from raw_runtime import RunInfo, RunStatus

info = RunInfo(
    run_id="run-abc123",
    status=RunStatus.SUCCESS,  # or FAILED, RUNNING
    started_at=datetime.now(timezone.utc),
    ended_at=datetime.now(timezone.utc),
    duration_seconds=15.5,
    exit_code=0,
)
```

---

## Complete Example

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["raw", "requests>=2.28"]
# ///
"""Example workflow using raw_runtime decorators."""

from pathlib import Path
import requests
from pydantic import BaseModel, Field

from raw_runtime import (
    raw_step,
    retry,
    cache_step,
    WorkflowContext,
    Artifact,
)


class WorkflowParams(BaseModel):
    url: str = Field(..., description="URL to fetch")


class MyWorkflow:
    def __init__(self, params: WorkflowParams):
        self.params = params
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)

    @raw_step("fetch")
    @retry(retries=3, backoff="exponential")
    def fetch(self) -> dict:
        """Fetch data with retry logic."""
        response = requests.get(self.params.url, timeout=10)
        response.raise_for_status()
        return response.json()

    @raw_step("process")
    @cache_step
    def process(self, data: dict) -> dict:
        """Process data (cached)."""
        # Expensive operation here
        return {"processed": True, "count": len(data)}

    @raw_step("save")
    def save(self, result: dict) -> str:
        """Save results to file."""
        output_path = self.results_dir / "output.json"
        output_path.write_text(str(result))
        return str(output_path)

    def run(self) -> int:
        try:
            data = self.fetch()
            result = self.process(data)
            path = self.save(result)
            print(f"Saved to: {path}")
            return 0
        except Exception as e:
            print(f"Error: {e}")
            return 1


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    args = parser.parse_args()

    params = WorkflowParams(url=args.url)

    # Create context for tracking
    with WorkflowContext(
        workflow_id="example-workflow",
        workflow_name="Example",
        workflow_version="1.0.0",
    ) as ctx:
        workflow = MyWorkflow(params)
        exit_code = workflow.run()

    exit(exit_code)


if __name__ == "__main__":
    main()
```

---

## Module Architecture

The `raw_runtime` module uses a **facade pattern** that re-exports from internal packages. This provides a clean, stable public API while allowing internal restructuring.

### Public API (Recommended)

Always import from `raw_runtime` directly:

```python
from raw_runtime import (
    # Decorators
    raw_step, retry, cache_step, step,

    # Core
    WorkflowContext, BaseWorkflow,

    # Models
    StepResult, Artifact, Manifest,

    # Utilities
    get_workflow_context, set_workflow_context,
)
```

### Advanced Capabilities

For advanced use cases, `raw_runtime` provides access to pluggable drivers:

```python
from raw_runtime import (
    # Storage
    get_storage, set_storage,
    FileSystemStorage, MemoryStorage,

    # Secrets
    get_secret, require_secret,
    EnvVarSecretProvider, DotEnvSecretProvider,

    # Orchestration
    get_orchestrator, set_orchestrator,
    LocalOrchestrator, HttpOrchestrator,

    # Telemetry
    get_telemetry_sink, set_telemetry_sink, log_metric, log_event,
    NullSink, ConsoleSink, JsonFileSink, MemorySink,

    # Approval
    wait_for_approval, get_approval_handler, set_approval_handler,
    ConsoleApprovalHandler, AutoApprovalHandler,
)
```

### Extending with Custom Drivers

If you need custom implementations (e.g., S3 storage, Vault secrets), import protocols from `raw_runtime.protocols`:

```python
from raw_runtime.protocols import StorageBackend, SecretProvider, TelemetrySink

class S3Storage:
    """Custom S3 storage implementation."""

    def save_artifact(self, run_id: str, name: str, content: bytes | str) -> str:
        # Upload to S3
        ...

    # Implement other StorageBackend methods

# Register your custom driver
from raw_runtime import set_storage
set_storage(S3Storage(bucket="my-bucket"))
```

---

## Secret Management

Access secrets securely without hardcoding credentials.

```python
from raw_runtime import get_secret, require_secret

# Get secret (returns None if not found)
api_key = get_secret("API_KEY")

# Require secret (raises if not found)
api_key = require_secret("API_KEY")
```

By default, secrets are read from environment variables. Use `DotEnvSecretProvider` for `.env` files:

```python
from raw_runtime import set_secret_provider, DotEnvSecretProvider, ChainedSecretProvider, EnvVarSecretProvider

# Load from .env first, then environment
set_secret_provider(ChainedSecretProvider([
    DotEnvSecretProvider(".env"),
    EnvVarSecretProvider(),
]))
```

---

## Storage Access

Persist artifacts and manifests with pluggable storage backends.

```python
from raw_runtime import get_storage

storage = get_storage()

# Save an artifact
path = storage.save_artifact(
    run_id="run-123",
    name="report.pdf",
    content=pdf_bytes,
)

# Load an artifact
content = storage.load_artifact(run_id="run-123", name="report.pdf")

# List artifacts
artifacts = storage.list_artifacts(run_id="run-123")
```

---

## Orchestration

Trigger workflows and manage runs programmatically.

```python
from raw_runtime import get_orchestrator

orch = get_orchestrator()

# Trigger a workflow
result = orch.trigger("my-workflow", args=["--param", "value"])

# Check run status
status = orch.get_status(result.run_id)
```

In connected mode (`RAW_SERVER_URL` set), this uses `HttpOrchestrator` to communicate with the RAW server.

---

## Event-Driven Architecture

RAW uses an event-driven architecture for workflow observability. Every state change (step started, completed, artifact created, etc.) is emitted as an event.

See [ARCHITECTURE.md](ARCHITECTURE.md) for:
- EventBus implementations (LocalEventBus, AsyncEventBus)
- Human-in-the-loop approval patterns
- Custom handler integration
- Testing with events

---

## See Also

- [../README.md](../README.md) - Project overview and installation
- [QUICKSTART.md](QUICKSTART.md) - 30-second setup
- [GUIDE.md](GUIDE.md) - Building workflows and best practices
- [ARCHITECTURE.md](ARCHITECTURE.md) - Event-driven architecture design

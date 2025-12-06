# Decorator Usage Guide

RAW provides decorators in `raw_runtime` for step tracking, retry logic, and caching.

## Installation

```python
from raw_runtime import step, retry, cache_step, WorkflowContext
```

## @step - Step Tracking

Tracks execution time, results, and errors for each step.

```python
@step("fetch_data")
def fetch_data(self) -> dict:
    """This step is tracked."""
    return {"data": "..."}
```

**Output:**
```
> [fetch_data] Starting...
> [fetch_data] Completed (0.25s)
```

**Parameters:**
- `name` (str): Step name for tracking and display

**Behavior:**
- Prints start/complete/error messages
- Records timing and results
- Stores to `WorkflowContext` if active

## @retry - Automatic Retries

Retries failed operations with configurable backoff.

```python
@step("api_call")
@retry(retries=3, backoff="exponential")
def api_call(self) -> dict:
    """Retries up to 3 times on failure."""
    return requests.get(url, timeout=10).json()
```

**Parameters:**
- `retries` (int, default=3): Maximum retry attempts
- `backoff` (str, default="exponential"): Backoff strategy
- `retry_on` (tuple, default=(Exception,)): Exceptions to retry on
- `base_delay` (float, default=1.0): Base delay in seconds

**Backoff Strategies:**

| Strategy | Formula | Example (base=1s) |
|----------|---------|-------------------|
| `exponential` | base * 2^attempt | 1s, 2s, 4s, 8s |
| `linear` | base * (attempt + 1) | 1s, 2s, 3s, 4s |
| `fixed` | base | 1s, 1s, 1s, 1s |

**Retry on specific exceptions:**

```python
@retry(retries=5, retry_on=(ConnectionError, TimeoutError), base_delay=2.0)
def fetch_with_timeout(self) -> dict:
    return requests.get(url, timeout=10).json()
```

## @cache_step - Result Caching

Caches expensive computation results.

```python
@step("calculate")
@cache_step
def calculate(self, data: dict) -> dict:
    """Results are cached based on arguments."""
    return expensive_operation(data)
```

**Behavior:**
- Generates cache key from function name + argument hash
- Stores results in `.raw/cache/` as JSON
- Skips execution if cached result exists
- Prints `[cached] step_name` when using cache

**Cache Location:**
```
.raw/cache/<step_name>_<args_hash>.json
```

**Requirements:**
- `WorkflowContext` must be active with cache directory
- Arguments must be JSON-serializable

## Combining Decorators

Decorators can be stacked for resilient, tracked, cached steps.

```python
@step("fetch_and_process")
@retry(retries=3, backoff="exponential")
@cache_step
def fetch_and_process(self, ticker: str) -> dict:
    """
    Execution order:
    1. @step tracks the call
    2. @retry handles failures
    3. @cache_step returns cached result if available
    """
    data = yfinance.download(ticker)
    return process(data)
```

**Order matters:**
```
@step     <- Outermost (tracks overall execution)
@retry        <- Middle (handles retries)
@cache_step   <- Innermost (checks cache first)
```

## WorkflowContext

Manages execution state, step results, and artifacts.

### Basic Usage

```python
from raw_runtime import WorkflowContext

with WorkflowContext(
    workflow_id="20251206-my-workflow-abc123",
    workflow_name="My Workflow",
    workflow_version="1.0.0",
    workflow_dir="/path/to/.raw/workflows/my-workflow",
) as ctx:
    # Steps executed here are automatically tracked
    result = my_step()

# Manifest automatically saved on exit
```

### Without Context Manager

```python
context = WorkflowContext(...)
set_workflow_context(context)

try:
    # Execute workflow steps
    ...
finally:
    context.finalize()  # Save manifest
```

### Adding Artifacts

```python
from raw_runtime import Artifact

artifact = Artifact(
    name="report",
    path="results/report.pdf",
    mime_type="application/pdf",
    size_bytes=12345,
)
ctx.add_artifact(artifact)
```

## Common Patterns

### External API Calls

```python
@step("fetch_api")
@retry(retries=3, backoff="exponential", retry_on=(requests.RequestException,))
def fetch_api(self) -> dict:
    response = requests.get(self.params.api_url, timeout=30)
    response.raise_for_status()
    return response.json()
```

### Expensive Calculations

```python
@step("analyze")
@cache_step
def analyze(self, data: pd.DataFrame) -> dict:
    # Cached - won't recompute if data hasn't changed
    return {
        "mean": data.mean().to_dict(),
        "std": data.std().to_dict(),
        "correlations": data.corr().to_dict(),
    }
```

### File Processing

```python
@step("process_files")
def process_files(self, file_paths: list[str]) -> list[dict]:
    results = []
    for path in file_paths:
        console.print(f"[dim]Processing {path}...[/]")
        result = self.process_file(path)
        results.append(result)
    return results
```

### Optional Steps

```python
@step("optional_enhancement")
def optional_enhancement(self, data: dict) -> dict:
    if not self.params.enable_enhancement:
        console.print("[dim]Skipping enhancement (disabled)[/]")
        return data

    return enhance(data)
```

## Troubleshooting

### Cache Not Working

1. Check `WorkflowContext` is active
2. Verify `.raw/cache/` directory exists
3. Ensure arguments are JSON-serializable

### Retry Not Triggering

1. Check exception type matches `retry_on`
2. Verify `retries` count is > 0
3. Look for nested exception wrapping

### Steps Not Tracked

1. Ensure `@step` is the outermost decorator
2. Check `WorkflowContext` is set
3. Verify method is being called (not just defined)

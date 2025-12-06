# Testing Guide

How to test RAW workflows before publishing.

## Testing Strategy

```
1. dry_run.py  - Test with mock data (no external calls)
2. test.py     - Unit tests for individual steps
3. raw run     - Full execution with real data
```

## Creating dry_run.py

### Generate Template

```bash
raw dry-run <workflow-id> --init
```

This creates:
- `dry_run.py` - Template script
- `mocks/example.json` - Sample mock data

### Manual Creation

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pydantic>=2.0",
#   "rich>=13.0",
# ]
# ///
"""Dry run for my-workflow with mocked data."""

import json
from pathlib import Path
from rich.console import Console

console = Console()

# Mock data directory
MOCKS_DIR = Path(__file__).parent / "mocks"


def load_mock(name: str) -> dict:
    """Load mock data from mocks/ directory."""
    mock_file = MOCKS_DIR / f"{name}.json"
    if mock_file.exists():
        return json.loads(mock_file.read_text())
    return {}


def main() -> None:
    console.print("[bold blue]Dry run:[/] my-workflow")
    console.print("[yellow]Using mocked data...[/]")
    console.print()

    # Load mock data instead of fetching
    api_response = load_mock("api_response")
    console.print(f"[green]>[/] Loaded {len(api_response)} items from mock")

    # Simulate processing steps
    console.print("[green]>[/] Step 1: Processing data...")
    console.print("[green]>[/] Step 2: Generating output...")
    console.print("[green]>[/] Step 3: Saving results...")

    # Write mock output
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    (results_dir / "output.json").write_text(
        json.dumps({"dry_run": True, "items": len(api_response)}, indent=2)
    )

    console.print()
    console.print("[bold green]Dry run complete![/]")


if __name__ == "__main__":
    main()
```

## Creating Mock Data

### Directory Structure

```
.raw/workflows/<id>/
└── mocks/
    ├── api_response.json
    ├── user_data.json
    └── config.json
```

### Mock Data Examples

**API Response:**
```json
{
  "status": "ok",
  "data": [
    {"id": 1, "name": "Item 1", "value": 100},
    {"id": 2, "name": "Item 2", "value": 200}
  ],
  "metadata": {
    "total": 2,
    "page": 1
  }
}
```

**Stock Data (for yfinance workflows):**
```json
{
  "ticker": "TSLA",
  "period": "3mo",
  "data": {
    "dates": ["2024-01-01", "2024-01-02", "2024-01-03"],
    "close": [250.0, 255.0, 248.0],
    "volume": [1000000, 1200000, 900000]
  }
}
```

**Configuration:**
```json
{
  "api_key": "mock-key-123",
  "base_url": "https://api.example.com",
  "timeout": 30
}
```

## Writing test.py

### Basic Test Structure

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pytest>=8.0",
#   "pydantic>=2.0",
# ]
# ///
"""Tests for my-workflow."""

import pytest
from pathlib import Path

# Import workflow components
from run import MyWorkflow, WorkflowParams


class TestMyWorkflow:
    """Test suite for MyWorkflow."""

    def test_params_validation(self) -> None:
        """Test parameter validation."""
        # Valid params
        params = WorkflowParams(param1="test", param2=10)
        assert params.param1 == "test"
        assert params.param2 == 10

        # Invalid params should raise
        with pytest.raises(Exception):
            WorkflowParams(param1="")  # Empty not allowed

    def test_process_step(self) -> None:
        """Test processing logic."""
        params = WorkflowParams(param1="test")
        workflow = MyWorkflow(params)

        # Test with sample data
        result = workflow.process({"input": "data"})

        assert "output" in result
        assert result["processed"] is True

    def test_output_format(self) -> None:
        """Test output file format."""
        params = WorkflowParams(param1="test")
        workflow = MyWorkflow(params)

        # Run and check output
        workflow.run()

        output_path = Path("results/output.json")
        assert output_path.exists()

        import json
        data = json.loads(output_path.read_text())
        assert "result" in data


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_input(self) -> None:
        """Test handling of empty input."""
        params = WorkflowParams(param1="test")
        workflow = MyWorkflow(params)

        result = workflow.process({})
        assert result is not None

    def test_large_input(self) -> None:
        """Test handling of large input."""
        params = WorkflowParams(param1="test")
        workflow = MyWorkflow(params)

        large_data = {"items": list(range(10000))}
        result = workflow.process(large_data)

        assert result["count"] == 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Running Tests

```bash
# Run all tests
raw test <workflow-id>

# Or directly with pytest
cd .raw/workflows/<id>
uv run test.py
```

## Testing Checklist

### Before Publishing

- [ ] `dry_run.py` executes without errors
- [ ] Mock data covers main use cases
- [ ] Edge cases tested (empty input, large input)
- [ ] Error handling tested
- [ ] Output format validated

### Mock Data Quality

- [ ] Realistic data structure
- [ ] Multiple scenarios covered
- [ ] Edge cases included
- [ ] Error responses mocked

### Test Coverage

- [ ] All workflow steps tested
- [ ] Parameter validation tested
- [ ] Output format verified
- [ ] Error paths covered

## Debugging Tips

### Verbose Output

Add debug prints in dry_run.py:

```python
console.print(f"[dim]Debug: data = {data}[/]")
```

### Step-by-Step Execution

Test each step individually:

```python
# In dry_run.py
data = load_mock("input")
console.print(f"Step 1 input: {data}")

result = workflow.step_one(data)
console.print(f"Step 1 output: {result}")

# Continue with step 2...
```

### Compare Mock vs Real

Run both and compare:

```bash
# Dry run with mocks
raw dry-run <id> > dry_output.txt

# Real run
raw run <id> > real_output.txt

# Compare
diff dry_output.txt real_output.txt
```

## Common Issues

### Mock Data Doesn't Match Real API

Update mocks to match actual API response structure. Capture real responses:

```python
# Temporary code to capture real response
response = requests.get(url)
Path("mocks/api_response.json").write_text(
    json.dumps(response.json(), indent=2)
)
```

### Tests Pass But Real Run Fails

1. Check network connectivity
2. Verify API credentials
3. Test with smaller dataset first
4. Add more error handling

### Flaky Tests

1. Don't depend on external services in tests
2. Use deterministic mock data
3. Seed random number generators
4. Mock time-dependent operations

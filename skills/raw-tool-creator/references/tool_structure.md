# Tool Structure Reference

Detailed breakdown of RAW tool components.

## Directory Layout

```
tools/<tool_name>/
├── config.yaml    # Metadata and interface definition
├── tool.py        # Main implementation
├── __init__.py    # Package exports
├── test.py        # Test suite
└── README.md      # Documentation
```

Tools live in `tools/` at the project root (not in `.raw/`). This makes them importable as Python packages.

## config.yaml

Defines the tool's interface and metadata.

```yaml
# Required fields
name: fetch_stock              # Tool identifier (use underscores)
version: "1.0.0"               # Semantic version
status: draft                  # draft | published
description: >                 # What the tool does
  Fetch historical stock data from Yahoo Finance
  using the yfinance library

# Input definitions
inputs:
  - name: ticker               # Parameter name
    type: str                  # Python type hint
    required: true             # Is it required?
    description: Stock symbol (e.g., TSLA, AAPL)

  - name: period
    type: str
    required: false
    default: "1mo"             # Default value if not provided
    description: >
      Time period. Options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y

  - name: interval
    type: str
    required: false
    default: "1d"
    description: Data interval (1m, 5m, 15m, 1h, 1d)

# Output definitions
outputs:
  - name: data
    type: dict
    description: >
      Dictionary containing:
      - ticker: str
      - dates: list[str]
      - close: list[float]
      - volume: list[int]

# PEP 723 dependencies
dependencies:
  - yfinance>=0.2
  - pandas>=2.0
```

### Type Specifications

| Type | Description | Example |
|------|-------------|---------|
| `str` | String | `"TSLA"` |
| `int` | Integer | `100` |
| `float` | Decimal | `3.14` |
| `bool` | Boolean | `true` |
| `list` | Array | `[1, 2, 3]` |
| `dict` | Object | `{"key": "value"}` |
| `list[str]` | Typed array | `["a", "b"]` |
| `Path` | File path | `/path/to/file` |

## tool.py

Main implementation file.

### Required Structure

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "yfinance>=0.2",
# ]
# ///
"""Tool description - matches config.yaml description."""

from typing import Any


def tool_function(param1: str, param2: int = 10) -> dict:
    """Main tool function.

    Args:
        param1: Description from config.yaml
        param2: Description with default

    Returns:
        Output structure as defined in config.yaml

    Raises:
        ValueError: If inputs are invalid
    """
    # Implementation
    return {"result": "..."}


# CLI support for standalone execution
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--param1", required=True, help="Parameter 1")
    parser.add_argument("--param2", type=int, default=10, help="Parameter 2")
    args = parser.parse_args()

    result = tool_function(args.param1, args.param2)
    print(json.dumps(result, indent=2, default=str))
```

### Function Naming

The main function name should match the tool name (with underscores):

| Tool Name | Function Name |
|-----------|---------------|
| `fetch_stock` | `fetch_stock()` |
| `parse_csv` | `parse_csv()` |
| `generate_pdf` | `generate_pdf()` |

### Multiple Functions

Tools can have helper functions, but one main entry point:

```python
def fetch_stock(ticker: str, period: str = "1mo") -> dict:
    """Main entry point."""
    raw_data = _fetch_raw_data(ticker, period)
    return _format_response(raw_data)


def _fetch_raw_data(ticker: str, period: str) -> Any:
    """Internal helper - prefixed with underscore."""
    import yfinance as yf
    return yf.Ticker(ticker).history(period=period)


def _format_response(data: Any) -> dict:
    """Internal helper."""
    return {
        "dates": data.index.strftime("%Y-%m-%d").tolist(),
        "close": data["Close"].tolist(),
    }
```

## __init__.py

Package export file that makes the tool importable.

```python
"""Fetch stock data from Yahoo Finance."""

from .tool import fetch_stock

__all__ = ["fetch_stock"]
```

This enables imports like:
```python
from tools.fetch_stock import fetch_stock
```

## test.py

Test suite for the tool.

### Structure

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pytest>=8.0",
#   "yfinance>=0.2",  # Same deps as tool.py
# ]
# ///
"""Tests for fetch_stock tool."""

import pytest
from tool import fetch_stock


class TestFetchStock:
    """Main test class - named Test<ToolName>."""

    def test_basic_usage(self) -> None:
        """Test normal usage."""
        result = fetch_stock("AAPL", "5d")
        assert "ticker" in result
        assert result["ticker"] == "AAPL"

    def test_default_values(self) -> None:
        """Test default parameter values."""
        result = fetch_stock("MSFT")
        # Should use default period

    def test_return_structure(self) -> None:
        """Test output matches config.yaml."""
        result = fetch_stock("GOOG", "1d")

        # Verify all documented outputs exist
        assert "ticker" in result
        assert "dates" in result
        assert "close" in result
        assert "volume" in result

        # Verify types
        assert isinstance(result["dates"], list)
        assert isinstance(result["close"], list)


class TestEdgeCases:
    """Edge case tests."""

    def test_invalid_ticker(self) -> None:
        """Test handling of invalid input."""
        result = fetch_stock("INVALID_XYZ_123")
        # Should handle gracefully, not crash

    def test_empty_result(self) -> None:
        """Test handling of no data."""
        # Test with ticker that might have no data


class TestValidation:
    """Input validation tests."""

    def test_empty_ticker(self) -> None:
        """Test empty string rejected."""
        with pytest.raises(ValueError):
            fetch_stock("")

    def test_invalid_period(self) -> None:
        """Test invalid period rejected."""
        with pytest.raises(ValueError):
            fetch_stock("AAPL", "invalid")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Running Tests

```bash
# From the tool directory
cd tools/<tool_name>
uv run pytest test.py -v

# With more options
uv run pytest test.py -v --tb=short
```

## README.md

Documentation for tool users.

### Template

```markdown
# fetch_stock

Fetch historical stock data from Yahoo Finance.

## Status

- **Version:** 1.0.0
- **Status:** draft

## Inputs

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| ticker | str | Yes | - | Stock symbol (e.g., TSLA) |
| period | str | No | "1mo" | Time period |

## Outputs

| Name | Type | Description |
|------|------|-------------|
| data | dict | Stock data with dates, prices, volumes |

### Output Structure

\`\`\`json
{
  "ticker": "TSLA",
  "period": "1mo",
  "dates": ["2024-01-01", "2024-01-02"],
  "close": [250.0, 255.0],
  "volume": [1000000, 1200000]
}
\`\`\`

## Dependencies

- yfinance>=0.2
- pandas>=2.0

## Usage

### As Python Module

\`\`\`python
from tools.fetch_stock import fetch_stock

data = fetch_stock("TSLA", "3mo")
print(f"Got {len(data['dates'])} days of data")
\`\`\`

### As CLI

\`\`\`bash
cd tools/fetch_stock
uv run tool.py --ticker TSLA --period 3mo
\`\`\`

## Testing

\`\`\`bash
cd tools/fetch_stock
uv run pytest test.py -v
\`\`\`

## Examples

### Basic Fetch

\`\`\`python
data = fetch_stock("AAPL")
# Uses default period of 1mo
\`\`\`

### Custom Period

\`\`\`python
data = fetch_stock("GOOG", "1y")
# Full year of data
\`\`\`
```

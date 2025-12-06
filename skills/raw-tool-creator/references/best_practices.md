# Tool Best Practices

Guidelines for creating high-quality, reusable RAW tools.

## Design Principles

### 1. Single Responsibility

Each tool should do **one thing well**.

```python
# Good - focused tools
def fetch_stock(ticker: str) -> dict: ...
def calculate_rsi(prices: list[float]) -> float: ...
def generate_chart(data: dict) -> str: ...

# Bad - kitchen sink tool
def analyze_stock(ticker: str) -> dict:
    """Fetches, calculates, charts, saves, emails..."""
    # Too many responsibilities
```

### 2. Pure Functions

Tools should be **deterministic** when possible.

```python
# Good - same input = same output
def calculate_rsi(prices: list[float], period: int = 14) -> float:
    # Calculation based only on inputs
    return rsi_value

# Avoid - hidden state
class StockAnalyzer:
    def __init__(self):
        self.cache = {}  # Hidden state affects results

    def calculate(self, ticker: str) -> float:
        # Behavior depends on cache state
```

### 3. Explicit Over Implicit

Make all behavior explicit through parameters.

```python
# Good - explicit configuration
def fetch_stock(
    ticker: str,
    period: str = "1mo",
    interval: str = "1d",
    include_dividends: bool = False,
) -> dict: ...

# Bad - hidden configuration
def fetch_stock(ticker: str) -> dict:
    period = os.environ.get("STOCK_PERIOD", "1mo")  # Hidden
    # ...
```

## Input Handling

### Validation

Validate all inputs at the start:

```python
def fetch_stock(ticker: str, period: str = "1mo") -> dict:
    """Fetch stock data."""
    # Validate ticker
    if not ticker:
        raise ValueError("Ticker cannot be empty")
    if not ticker.replace(".", "").replace("-", "").isalnum():
        raise ValueError(f"Invalid ticker format: {ticker}")

    # Validate period
    valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]
    if period not in valid_periods:
        raise ValueError(f"Invalid period '{period}'. Valid: {valid_periods}")

    # Continue with validated inputs
    ...
```

### Type Coercion

Be lenient in what you accept, strict in what you return:

```python
def calculate_average(values: list[float] | list[int]) -> float:
    """Calculate average of numeric values.

    Args:
        values: List of numbers (int or float accepted)

    Returns:
        Average as float
    """
    if not values:
        raise ValueError("Cannot calculate average of empty list")

    # Coerce to float for consistent output
    return float(sum(values)) / len(values)
```

### Optional Parameters

Use sensible defaults:

```python
def fetch_stock(
    ticker: str,
    period: str = "1mo",      # Common default
    interval: str = "1d",      # Daily data by default
    timeout: int = 30,         # Reasonable timeout
) -> dict:
    """Parameters have documented defaults."""
    ...
```

## Output Handling

### Consistent Structure

Always return the same structure:

```python
def fetch_stock(ticker: str) -> dict:
    """Always returns same structure, even on error."""
    try:
        data = _fetch_data(ticker)
        return {
            "success": True,
            "ticker": ticker,
            "data": data,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "ticker": ticker,
            "data": None,
            "error": str(e),
        }
```

### JSON-Serializable

Return data that can be serialized:

```python
# Good - JSON-serializable
def fetch_stock(ticker: str) -> dict:
    return {
        "ticker": ticker,
        "dates": ["2024-01-01", "2024-01-02"],  # Strings, not datetime
        "close": [250.0, 255.0],                 # Floats
    }

# Bad - not serializable
def fetch_stock(ticker: str) -> pd.DataFrame:
    return df  # DataFrame can't be JSON serialized directly
```

### Document Output Structure

```python
def fetch_stock(ticker: str) -> dict:
    """Fetch stock data.

    Returns:
        dict with keys:
        - ticker (str): The requested symbol
        - dates (list[str]): ISO format dates
        - close (list[float]): Closing prices
        - volume (list[int]): Trading volumes

    Example:
        >>> fetch_stock("AAPL", "5d")
        {
            "ticker": "AAPL",
            "dates": ["2024-01-01", ...],
            "close": [180.5, ...],
            "volume": [50000000, ...]
        }
    """
```

## Error Handling

### Graceful Degradation

Don't crash on recoverable errors:

```python
def fetch_multiple_stocks(tickers: list[str]) -> dict:
    """Fetch data for multiple stocks."""
    results = {}
    errors = []

    for ticker in tickers:
        try:
            results[ticker] = _fetch_one(ticker)
        except Exception as e:
            errors.append({"ticker": ticker, "error": str(e)})
            # Continue with other tickers

    return {
        "results": results,
        "errors": errors,
        "success_count": len(results),
        "error_count": len(errors),
    }
```

### Meaningful Errors

Provide actionable error messages:

```python
def fetch_stock(ticker: str, api_key: str | None = None) -> dict:
    """Fetch stock data."""
    if api_key is None:
        api_key = os.environ.get("STOCK_API_KEY")
        if not api_key:
            raise ValueError(
                "API key required. Set STOCK_API_KEY environment variable "
                "or pass api_key parameter."
            )

    response = requests.get(url, headers={"Authorization": api_key})
    if response.status_code == 401:
        raise ValueError("Invalid API key. Check your credentials.")
    if response.status_code == 429:
        raise ValueError("Rate limit exceeded. Wait before retrying.")

    response.raise_for_status()
    return response.json()
```

## Dependencies

### Minimize Dependencies

Only include what you need:

```python
# /// script
# dependencies = [
#   "requests>=2.28",  # Only for HTTP calls
# ]
# ///

# Don't include pandas just for one operation
# Use native Python when possible
```

### Pin Versions

Prevent breaking changes:

```python
# /// script
# dependencies = [
#   "yfinance>=0.2,<0.3",    # Allow patches, not major
#   "pandas>=2.0,<3.0",      # Same major version
#   "requests>=2.28",        # Stable, less strict ok
# ]
# ///
```

### Lazy Imports

Import heavy libraries only when needed:

```python
def generate_chart(data: dict) -> str:
    """Generate chart - imports matplotlib only when called."""
    import matplotlib.pyplot as plt  # Import here, not at top

    fig, ax = plt.subplots()
    # ...
```

## Testing

### Test Coverage

Cover these scenarios:

```python
class TestFetchStock:
    # Happy path
    def test_basic_fetch(self): ...
    def test_with_options(self): ...

    # Edge cases
    def test_empty_result(self): ...
    def test_single_day(self): ...

    # Error handling
    def test_invalid_ticker(self): ...
    def test_network_error(self): ...

    # Input validation
    def test_empty_ticker_rejected(self): ...
    def test_invalid_period_rejected(self): ...
```

### Mock External Services

Don't call real APIs in tests:

```python
from unittest.mock import patch, MagicMock

def test_fetch_stock_success():
    """Test with mocked yfinance."""
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame({
        "Close": [100.0, 101.0],
        "Volume": [1000, 2000],
    })

    with patch("tool.yf.Ticker", return_value=mock_ticker):
        result = fetch_stock("TEST")
        assert result["close"] == [100.0, 101.0]
```

## Performance

### Caching

Cache expensive operations:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def fetch_stock(ticker: str, period: str = "1mo") -> dict:
    """Cached - repeated calls return cached result."""
    ...
```

### Batch Operations

Support batch processing:

```python
def fetch_stocks(tickers: list[str]) -> dict:
    """Fetch multiple in one call - more efficient than loop."""
    import yfinance as yf

    data = yf.download(tickers, period="1mo", group_by="ticker")
    return {ticker: _extract(data[ticker]) for ticker in tickers}
```

## Documentation

### Docstrings

Every public function needs:

```python
def fetch_stock(ticker: str, period: str = "1mo") -> dict:
    """Fetch historical stock data from Yahoo Finance.

    Retrieves OHLCV data for the specified ticker and time period.

    Args:
        ticker: Stock symbol (e.g., "TSLA", "AAPL", "MSFT")
        period: Time period. Options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max

    Returns:
        Dictionary containing:
        - ticker: The requested symbol
        - dates: List of ISO format date strings
        - close: List of closing prices
        - volume: List of trading volumes

    Raises:
        ValueError: If ticker is empty or period is invalid
        ConnectionError: If unable to reach Yahoo Finance

    Example:
        >>> data = fetch_stock("AAPL", "5d")
        >>> len(data["dates"])
        5
    """
```

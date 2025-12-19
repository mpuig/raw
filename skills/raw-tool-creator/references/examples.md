# Tool examples

Common tool patterns with implementation examples.

## Data fetcher

Fetches data from external APIs.

```python
def fetch_stock(ticker: str, period: str = "1mo") -> dict:
    """Fetch stock data from yfinance."""
    import yfinance as yf

    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)

    return {
        "ticker": ticker,
        "dates": hist.index.strftime("%Y-%m-%d").tolist(),
        "close": hist["Close"].tolist(),
        "volume": hist["Volume"].tolist(),
    }
```

## Data processor

Transforms or calculates derived values.

```python
def calculate_rsi(prices: list[float], period: int = 14) -> float:
    """Calculate RSI indicator."""
    import pandas as pd

    series = pd.Series(prices)
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return float(100 - (100 / (1 + rs.iloc[-1])))
```

## File generator

Creates output files in various formats.

```python
def generate_pdf(title: str, content: str, output_path: str) -> str:
    """Generate PDF report."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(output_path, pagesize=letter)
    c.drawString(100, 750, title)
    c.drawString(100, 700, content)
    c.save()

    return output_path
```

## API client

Wraps external service APIs with error handling.

```python
def fetch_weather(city: str, api_key: str | None = None) -> dict:
    """Fetch weather data from OpenWeatherMap."""
    import os
    import httpx

    api_key = api_key or os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        raise ValueError("API key required")

    response = httpx.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"q": city, "appid": api_key},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
```

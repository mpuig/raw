# Workflow Patterns

Common patterns for RAW workflows.

## Pattern 1: Fetch → Process → Save

The most common workflow pattern:

```python
class DataWorkflow:
    def __init__(self, params: WorkflowParams) -> None:
        self.params = params
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)

    @step("fetch")
    @retry(retries=3, backoff="exponential")
    def fetch(self) -> dict:
        """Fetch data from external source."""
        response = requests.get(self.params.url, timeout=30)
        response.raise_for_status()
        return response.json()

    @step("process")
    def process(self, data: dict) -> dict:
        """Process and transform data."""
        # Apply transformations
        return {"processed": True, "count": len(data)}

    @step("save")
    def save(self, result: dict) -> str:
        """Save results to file."""
        output_path = self.results_dir / "output.json"
        output_path.write_text(json.dumps(result, indent=2))
        return str(output_path)

    def run(self) -> int:
        data = self.fetch()
        result = self.process(data)
        path = self.save(result)
        console.print(f"[green]Saved:[/] {path}")
        return 0
```

## Pattern 2: Multi-Source Aggregation

Fetch from multiple sources, combine results:

```python
class AggregationWorkflow:
    @step("fetch_source_a")
    @retry(retries=3)
    def fetch_source_a(self) -> dict:
        return requests.get(self.params.url_a).json()

    @step("fetch_source_b")
    @retry(retries=3)
    def fetch_source_b(self) -> dict:
        return requests.get(self.params.url_b).json()

    @step("merge")
    def merge(self, data_a: dict, data_b: dict) -> dict:
        """Combine data from multiple sources."""
        return {
            "source_a": data_a,
            "source_b": data_b,
            "merged_at": datetime.now().isoformat(),
        }

    def run(self) -> int:
        data_a = self.fetch_source_a()
        data_b = self.fetch_source_b()
        merged = self.merge(data_a, data_b)
        self.save(merged)
        return 0
```

## Pattern 3: Report Generation

Process data and generate formatted output:

```python
class ReportWorkflow:
    @step("fetch_data")
    def fetch_data(self) -> pd.DataFrame:
        """Load data for analysis."""
        return yfinance.download(self.params.ticker, period=self.params.period)

    @step("analyze")
    def analyze(self, df: pd.DataFrame) -> dict:
        """Calculate metrics and statistics."""
        return {
            "mean": df["Close"].mean(),
            "std": df["Close"].std(),
            "min": df["Close"].min(),
            "max": df["Close"].max(),
        }

    @step("generate_chart")
    def generate_chart(self, df: pd.DataFrame) -> str:
        """Create visualization."""
        fig, ax = plt.subplots(figsize=(10, 6))
        df["Close"].plot(ax=ax)
        ax.set_title(f"{self.params.ticker} Price")

        chart_path = self.results_dir / "chart.png"
        fig.savefig(chart_path)
        plt.close(fig)
        return str(chart_path)

    @step("generate_report")
    def generate_report(self, analysis: dict, chart_path: str) -> str:
        """Create final report."""
        report = f"""# {self.params.ticker} Analysis

## Summary
- Mean: ${analysis['mean']:.2f}
- Std Dev: ${analysis['std']:.2f}
- Range: ${analysis['min']:.2f} - ${analysis['max']:.2f}

## Chart
![Price Chart]({chart_path})
"""
        report_path = self.results_dir / "report.md"
        report_path.write_text(report)
        return str(report_path)

    def run(self) -> int:
        df = self.fetch_data()
        analysis = self.analyze(df)
        chart_path = self.generate_chart(df)
        report_path = self.generate_report(analysis, chart_path)
        console.print(f"[green]Report:[/] {report_path}")
        return 0
```

## Pattern 4: Conditional Processing

Different paths based on data:

```python
class ConditionalWorkflow:
    @step("fetch")
    def fetch(self) -> dict:
        return requests.get(self.params.url).json()

    @step("classify")
    def classify(self, data: dict) -> str:
        """Determine processing path."""
        if data.get("priority") == "high":
            return "urgent"
        elif data.get("size", 0) > 1000:
            return "large"
        return "normal"

    @step("process_urgent")
    def process_urgent(self, data: dict) -> dict:
        """Handle urgent items immediately."""
        return {"processed": True, "priority": "urgent"}

    @step("process_large")
    @cache_step
    def process_large(self, data: dict) -> dict:
        """Cache large data processing."""
        return {"processed": True, "cached": True}

    @step("process_normal")
    def process_normal(self, data: dict) -> dict:
        """Standard processing."""
        return {"processed": True}

    def run(self) -> int:
        data = self.fetch()
        category = self.classify(data)

        if category == "urgent":
            result = self.process_urgent(data)
        elif category == "large":
            result = self.process_large(data)
        else:
            result = self.process_normal(data)

        self.save(result)
        return 0
```

## Pattern 5: Batch Processing

Process items in batches:

```python
class BatchWorkflow:
    @step("fetch_items")
    def fetch_items(self) -> list[dict]:
        """Get list of items to process."""
        return requests.get(self.params.list_url).json()

    @step("process_batch")
    def process_batch(self, items: list[dict]) -> list[dict]:
        """Process items in batches."""
        results = []
        batch_size = self.params.batch_size

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            console.print(f"[dim]Processing batch {i//batch_size + 1}...[/]")

            for item in batch:
                result = self.process_item(item)
                results.append(result)

        return results

    def process_item(self, item: dict) -> dict:
        """Process single item."""
        return {"id": item["id"], "processed": True}

    def run(self) -> int:
        items = self.fetch_items()
        console.print(f"[blue]Processing {len(items)} items...[/]")
        results = self.process_batch(items)
        self.save({"results": results, "count": len(results)})
        return 0
```

## Best Practices

1. **Single Responsibility**: Each step does one thing
2. **Error Handling**: Use `@retry` for external calls
3. **Caching**: Use `@cache_step` for expensive operations
4. **Progress Feedback**: Print status for long operations
5. **Type Safety**: Use Pydantic for parameters and returns
6. **Idempotency**: Steps should be safe to re-run

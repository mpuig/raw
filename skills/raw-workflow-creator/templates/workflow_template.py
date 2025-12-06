#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pydantic>=2.0",
#   "rich>=13.0",
#   # Add your dependencies here:
#   # "requests>=2.28",
#   # "pandas>=2.0",
# ]
# ///
"""
WORKFLOW_NAME - WORKFLOW_DESCRIPTION

Usage:
    uv run run.py --param1 value [--param2 value]

Example:
    uv run run.py --param1 "example"
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from rich.console import Console

# Optional: Import raw_runtime decorators for advanced features
# from raw_runtime import step, retry, cache_step

console = Console()


class WorkflowParams(BaseModel):
    """Parameters for this workflow.

    Define all inputs with types, defaults, and descriptions.
    Pydantic validates inputs automatically.
    """

    param1: str = Field(..., description="Required parameter - describe what it's for")
    param2: int = Field(default=10, description="Optional parameter with default")
    # Add more parameters as needed:
    # output_format: str = Field(default="json", description="Output format (json, csv, md)")
    # verbose: bool = Field(default=False, description="Enable verbose output")


class Workflow:
    """Main workflow implementation.

    Structure your workflow as a class with:
    - __init__: Setup and configuration
    - Individual step methods (fetch, process, save, etc.)
    - run(): Orchestrates the steps
    """

    def __init__(self, params: WorkflowParams) -> None:
        self.params = params
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)

    # Uncomment to use decorators:
    # @step("fetch")
    # @retry(retries=3, backoff="exponential")
    def fetch(self) -> dict[str, Any]:
        """Step 1: Fetch data from external source.

        Returns:
            Raw data from API, file, or database
        """
        console.print("[bold blue]>[/] Fetching data...")

        # TODO: Implement data fetching
        # Example:
        # response = requests.get(url, timeout=30)
        # response.raise_for_status()
        # return response.json()

        return {"data": "placeholder"}

    # @step("process")
    # @cache_step  # Cache expensive operations
    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Step 2: Process and transform data.

        Args:
            data: Raw data from fetch step

        Returns:
            Processed results
        """
        console.print("[bold blue]>[/] Processing data...")

        # TODO: Implement processing logic
        # Example:
        # df = pd.DataFrame(data)
        # result = df.groupby("category").sum()
        # return result.to_dict()

        return {"processed": True, "input_size": len(str(data))}

    # @step("save")
    def save(self, result: dict[str, Any]) -> str:
        """Step 3: Save results to file.

        Args:
            result: Processed data to save

        Returns:
            Path to output file
        """
        console.print("[bold blue]>[/] Saving results...")

        import json

        output_path = self.results_dir / "output.json"
        output_path.write_text(json.dumps(result, indent=2, default=str))

        console.print(f"[green]>[/] Saved to {output_path}")
        return str(output_path)

    def run(self) -> int:
        """Execute the workflow.

        Orchestrates all steps in order.

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Execute steps in order
            data = self.fetch()
            result = self.process(data)
            output_path = self.save(result)

            console.print()
            console.print(f"[bold green]Done![/] Output: {output_path}")
            return 0

        except Exception as e:
            console.print(f"[bold red]Error:[/] {e}")
            return 1


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--param1", required=True, help="Required parameter")
    parser.add_argument("--param2", type=int, default=10, help="Optional parameter")
    # Add CLI arguments matching WorkflowParams

    args = parser.parse_args()

    # Create params from CLI args
    params = WorkflowParams(
        param1=args.param1,
        param2=args.param2,
    )

    # Run workflow
    workflow = Workflow(params)
    exit(workflow.run())


if __name__ == "__main__":
    main()

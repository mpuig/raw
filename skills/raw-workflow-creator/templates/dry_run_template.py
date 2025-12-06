#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pydantic>=2.0",
#   "rich>=13.0",
# ]
# ///
"""Dry run for WORKFLOW_NAME with mocked data.

This script tests the workflow logic without making external calls.
Mock data is loaded from the mocks/ directory.

Usage:
    uv run dry_run.py
"""

import json
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()

# Mock data directory (relative to this script)
MOCKS_DIR = Path(__file__).parent / "mocks"


def load_mock(name: str) -> dict[str, Any]:
    """Load mock data from mocks/ directory.

    Args:
        name: Mock file name without .json extension

    Returns:
        Parsed JSON data, or empty dict if not found
    """
    mock_file = MOCKS_DIR / f"{name}.json"
    if mock_file.exists():
        return json.loads(mock_file.read_text())  # type: ignore[no-any-return]
    console.print(f"[yellow]Warning:[/] Mock file not found: {mock_file}")
    return {}


def main() -> None:
    console.print("[bold blue]Dry run:[/] WORKFLOW_NAME")
    console.print("[yellow]Using mocked data...[/]")
    console.print()

    # === Step 1: Load mock data ===
    # Replace with your actual mock file names
    api_data = load_mock("api_response")
    console.print(f"[green]>[/] Step 1: Loaded mock data ({len(api_data)} keys)")

    # === Step 2: Simulate processing ===
    # Add your processing logic here, using mock data
    console.print("[green]>[/] Step 2: Processing mock data...")

    # Example processing
    result = {
        "dry_run": True,
        "input_keys": list(api_data.keys()) if isinstance(api_data, dict) else [],
        "processed": True,
    }

    # === Step 3: Save mock output ===
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    output_path = results_dir / "output.json"
    output_path.write_text(json.dumps(result, indent=2, default=str))
    console.print(f"[green]>[/] Step 3: Saved output to {output_path}")

    console.print()
    console.print("[bold green]Dry run complete![/]")
    console.print()
    console.print("[dim]To add mock data, create JSON files in mocks/[/]")
    console.print("[dim]Example: mocks/api_response.json[/]")


if __name__ == "__main__":
    main()

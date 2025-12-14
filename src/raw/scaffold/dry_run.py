"""Dry run template generation.

Provides utilities for generating dry_run.py scaffolds for workflows.
"""

import json
from pathlib import Path

from raw.scaffold.init import load_workflow_config


def generate_dry_run_template(workflow_dir: Path) -> None:
    """Generate a dry_run.py template for a workflow.

    Creates:
    - dry_run.py with mock data loading utilities
    - mocks/ directory for mock data files
    - mocks/example.json as a starter template

    Args:
        workflow_dir: Path to the workflow directory
    """
    config = load_workflow_config(workflow_dir)
    workflow_name = config.name if config else workflow_dir.name

    template = f'''#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pydantic>=2.0",
#   "rich>=13.0",
# ]
# ///
"""Dry run for {workflow_name} workflow with mocked data."""

import json
from pathlib import Path

from rich.console import Console

console = Console()

# Mock data directory
MOCKS_DIR = Path(__file__).parent / "mocks"


def load_mock(name: str) -> dict:
    """Load mock data from mocks/ directory."""
    mock_file = MOCKS_DIR / f"{{name}}.json"
    if mock_file.exists():
        return json.loads(mock_file.read_text())
    return {{}}


def main() -> None:
    console.print("[bold blue]Dry run:[/] {workflow_name}")
    console.print("[yellow]Using mocked data...[/]")
    console.print()

    # Example: Load mock data
    # data = load_mock("api_response")

    # Simulate workflow steps with mocked results
    console.print("[green]✓[/] Step 1: [dim]Mocked[/]")
    console.print("[green]✓[/] Step 2: [dim]Mocked[/]")
    console.print("[green]✓[/] Step 3: [dim]Mocked[/]")

    console.print()
    console.print("[bold green]Dry run complete![/]")

    # To add mock data, create JSON files in mocks/
    # Example: mocks/api_response.json
    #   {{"status": "ok", "data": [1, 2, 3]}}


if __name__ == "__main__":
    main()
'''

    (workflow_dir / "dry_run.py").write_text(template)
    (workflow_dir / "mocks").mkdir(exist_ok=True)

    example_mock = workflow_dir / "mocks" / "example.json"
    if not example_mock.exists():
        example_mock.write_text(
            json.dumps({"status": "ok", "message": "This is mock data"}, indent=2)
        )

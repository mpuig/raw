"""Run command implementation."""

import json
from pathlib import Path

import click

from raw.discovery.display import (
    console,
    print_error,
    print_info,
    print_run_result,
    print_success,
)
from raw.discovery.workflow import find_workflow
from raw.engine.execution import run_dry, run_workflow
from raw.scaffold.init import load_workflow_config


def _generate_dry_run_template(workflow_dir: Path) -> None:
    """Generate a dry_run.py template for the workflow."""
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


def run_command(
    ctx: click.Context,
    workflow_id: str | None,
    dry: bool,
    init: bool,
    prompt_workflow_selection: callable,
) -> None:
    """Run a workflow.

    This function contains the business logic for the run command.
    """
    if not workflow_id:
        workflow_id = prompt_workflow_selection("run")
        if not workflow_id:
            print_info("No workflows found. Create one with [cyan]raw create <name>[/]")
            raise SystemExit(0)

    workflow_dir = find_workflow(workflow_id)
    if not workflow_dir:
        print_error(f"Workflow not found: {workflow_id}")
        raise SystemExit(1)

    if init and not dry:
        print_error("--init requires --dry flag")
        raise SystemExit(1)

    if dry:
        dry_run_py = workflow_dir / "dry_run.py"
        mocks_dir = workflow_dir / "mocks"

        if not dry_run_py.exists():
            if init:
                _generate_dry_run_template(workflow_dir)
                print_success(f"Generated dry_run.py at {dry_run_py}")
                console.print("  Edit the file to add your mock data, then run again.")
                return
            else:
                print_error(f"dry_run.py not found: {dry_run_py}")
                console.print()
                console.print("[bold]To generate a template:[/]")
                console.print(f"  raw run {workflow_id} --dry --init")
                console.print()
                console.print("[bold]Or create dry_run.py manually with mock data.[/]")
                raise SystemExit(1)

        mocks_dir.mkdir(exist_ok=True)
        print_info(f"Dry-run workflow: {workflow_dir.name}")
        console.print()
        result = run_dry(workflow_dir, ctx.args)
    else:
        print_info(f"Running workflow: {workflow_dir.name}")
        console.print()
        result = run_workflow(workflow_dir, "run.py", ctx.args)

    print_run_result(
        workflow_dir.name,
        result.exit_code,
        result.duration_seconds,
        result.stdout,
        result.stderr,
    )

    raise SystemExit(result.exit_code)

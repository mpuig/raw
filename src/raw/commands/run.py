"""Run command implementation."""

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
from raw.scaffold.dry_run import generate_dry_run_template


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
                generate_dry_run_template(workflow_dir)
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

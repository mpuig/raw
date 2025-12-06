"""Trigger command - trigger a workflow via the RAW server."""

import os
import sys

import httpx
from rich.console import Console

from raw.discovery.workflow import find_workflow

console = Console()


def trigger_command(
    workflow_id: str | None,
    args: list[str],
    prompt_fn: callable,
) -> None:
    """Trigger a workflow via the RAW server.

    Args:
        workflow_id: Workflow ID (full or partial)
        args: Additional arguments to pass to the workflow
        prompt_fn: Function to prompt for workflow selection
    """
    if not workflow_id:
        workflow_id = prompt_fn("trigger")
        if not workflow_id:
            console.print("[yellow]No workflows found.[/]")
            return

    workflow_dir = find_workflow(workflow_id)
    if not workflow_dir:
        console.print(f"[red]Workflow not found:[/] {workflow_id}")
        sys.exit(1)

    resolved_id = workflow_dir.name

    server_url = os.environ.get("RAW_SERVER_URL", "http://localhost:8765")

    try:
        response = httpx.post(
            f"{server_url}/webhook/{resolved_id}",
            json={"args": args},
            timeout=10.0,
        )

        if response.status_code == 200:
            data = response.json()
            console.print(f"[green]Triggered:[/] {resolved_id}")
            console.print(f"  Run ID: [cyan]{data.get('run_id', 'unknown')}[/]")
            console.print(f"  Status: {data.get('status', 'unknown')}")
        elif response.status_code == 404:
            console.print(f"[red]Workflow not found on server:[/] {resolved_id}")
            console.print("[dim]Is the server running? (raw serve)[/]")
            sys.exit(1)
        else:
            console.print(f"[red]Server error:[/] {response.status_code}")
            console.print(response.text)
            sys.exit(1)

    except httpx.ConnectError:
        console.print("[red]Cannot connect to RAW server[/]")
        console.print(f"[dim]Server URL: {server_url}[/]")
        console.print("[dim]Start the server with: raw serve[/]")
        sys.exit(1)
    except httpx.TimeoutException:
        console.print("[red]Server request timed out[/]")
        sys.exit(1)

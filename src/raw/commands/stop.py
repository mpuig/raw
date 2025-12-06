"""Stop command - stop running workflows via the RAW server."""

import os
import sys

import httpx
from rich.console import Console

console = Console()


def stop_command(run_id: str | None, all_runs: bool) -> None:
    """Stop running workflows via the RAW server.

    Args:
        run_id: Specific run ID to stop
        all_runs: Stop all running workflows
    """
    server_url = os.environ.get("RAW_SERVER_URL", "http://localhost:8765")

    try:
        if all_runs:
            response = httpx.get(f"{server_url}/runs", timeout=10.0)
            if response.status_code != 200:
                console.print(f"[red]Failed to get runs:[/] {response.status_code}")
                sys.exit(1)

            runs = response.json()
            running_runs = [r for r in runs if r.get("status") in ("running", "waiting")]

            if not running_runs:
                console.print("[yellow]No running workflows to stop.[/]")
                return

            stopped = 0
            for run in running_runs:
                rid = run.get("run_id")
                try:
                    resp = httpx.post(
                        f"{server_url}/runs/{rid}/cancel",
                        timeout=10.0,
                    )
                    if resp.status_code == 200:
                        console.print(f"[green]Stopped:[/] {rid}")
                        stopped += 1
                    else:
                        console.print(f"[yellow]Could not stop:[/] {rid}")
                except Exception as e:
                    console.print(f"[red]Error stopping {rid}:[/] {e}")

            console.print(f"\n[bold]Stopped {stopped} workflow(s)[/]")

        elif run_id:
            response = httpx.post(
                f"{server_url}/runs/{run_id}/cancel",
                timeout=10.0,
            )

            if response.status_code == 200:
                console.print(f"[green]Stopped:[/] {run_id}")
            elif response.status_code == 404:
                console.print(f"[red]Run not found:[/] {run_id}")
                sys.exit(1)
            else:
                console.print(f"[red]Failed to stop run:[/] {response.status_code}")
                sys.exit(1)

        else:
            response = httpx.get(f"{server_url}/runs", timeout=10.0)
            if response.status_code != 200:
                console.print(f"[red]Failed to get runs:[/] {response.status_code}")
                sys.exit(1)

            runs = response.json()
            running_runs = [r for r in runs if r.get("status") in ("running", "waiting")]

            if not running_runs:
                console.print("[yellow]No running workflows.[/]")
                return

            console.print("[bold]Running workflows:[/]")
            for i, run in enumerate(running_runs, 1):
                status = run.get("status", "unknown")
                wf = run.get("workflow_id", "unknown")
                rid = run.get("run_id", "unknown")
                console.print(f"  {i}) [{status}] {wf} ({rid})")

            console.print("\n[dim]Use 'raw stop <run_id>' or 'raw stop --all'[/]")

    except httpx.ConnectError:
        console.print("[red]Cannot connect to RAW server[/]")
        console.print(f"[dim]Server URL: {server_url}[/]")
        console.print("[dim]Start the server with: raw serve[/]")
        sys.exit(1)
    except httpx.TimeoutException:
        console.print("[red]Server request timed out[/]")
        sys.exit(1)

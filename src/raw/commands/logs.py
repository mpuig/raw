"""Logs command - view workflow execution logs."""

import sys

from rich.console import Console
from rich.panel import Panel

from raw.discovery.workflow import find_workflow

console = Console()


def logs_command(
    workflow_id: str | None,
    run_id: str | None,
    follow: bool,
    lines: int,
    prompt_fn: callable,
) -> None:
    """View workflow execution logs.

    Args:
        workflow_id: Workflow ID (full or partial)
        run_id: Specific run ID to view (defaults to latest)
        follow: Follow log output (like tail -f)
        lines: Number of lines to show
        prompt_fn: Function to prompt for workflow selection
    """
    if not workflow_id:
        workflow_id = prompt_fn("view logs for")
        if not workflow_id:
            console.print("[yellow]No workflows found.[/]")
            return

    workflow_dir = find_workflow(workflow_id)
    if not workflow_dir:
        console.print(f"[red]Workflow not found:[/] {workflow_id}")
        sys.exit(1)

    resolved_id = workflow_dir.name

    runs_dir = workflow_dir / "runs"

    if not runs_dir.exists():
        console.print(f"[yellow]No runs found for workflow:[/] {resolved_id}")
        return

    if run_id:
        run_dir = runs_dir / run_id
        if not run_dir.exists():
            # Try partial match
            matches = [d for d in runs_dir.iterdir() if d.is_dir() and run_id in d.name]
            if len(matches) == 1:
                run_dir = matches[0]
            elif len(matches) > 1:
                console.print(f"[yellow]Multiple runs match '{run_id}':[/]")
                for m in matches:
                    console.print(f"  {m.name}")
                return
            else:
                console.print(f"[red]Run not found:[/] {run_id}")
                return
    else:
        run_dirs = sorted(
            [d for d in runs_dir.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )
        if not run_dirs:
            console.print(f"[yellow]No runs found for workflow:[/] {resolved_id}")
            return
        run_dir = run_dirs[0]

    log_file = run_dir / "output.log"
    if not log_file.exists():
        # Try legacy location
        log_file = run_dir / "logs" / "output.log"

    if not log_file.exists():
        console.print(f"[yellow]No log file found in:[/] {run_dir}")
        console.print("[dim]Available files:[/]")
        for f in run_dir.rglob("*"):
            if f.is_file():
                console.print(f"  {f.relative_to(run_dir)}")
        return

    console.print(Panel(f"[bold]{resolved_id}[/] / {run_dir.name}", border_style="blue"))

    if follow:
        import time

        with open(log_file) as f:
            f.seek(0, 2)
            console.print("[dim]Following logs (Ctrl+C to stop)...[/]")
            try:
                while True:
                    line = f.readline()
                    if line:
                        console.print(line.rstrip())
                    else:
                        time.sleep(0.5)
            except KeyboardInterrupt:
                console.print("\n[dim]Stopped following.[/]")
    else:
        content = log_file.read_text()
        log_lines = content.splitlines()

        if lines and len(log_lines) > lines:
            log_lines = log_lines[-lines:]
            console.print(f"[dim](showing last {lines} lines)[/]")

        for line in log_lines:
            console.print(line)

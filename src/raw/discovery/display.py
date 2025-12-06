"""Rich display utilities for RAW CLI."""

from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from raw.core.schemas import ToolConfig, WorkflowConfig

console = Console()


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]✓[/] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]✗[/] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[bold yellow]⚠[/] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[bold blue]ℹ[/] {message}")


def print_workflow_created(workflow_dir: Path, workflow_id: str) -> None:
    """Print workflow creation success."""
    console.print()
    console.print(
        Panel(
            f"[bold green]Workflow created successfully![/]\n\n"
            f"[bold]ID:[/] {workflow_id}\n"
            f"[bold]Path:[/] {workflow_dir}\n\n"
            f"[dim]Next steps:[/]\n"
            f"  1. Edit [cyan]{workflow_dir}/run.py[/] to implement your workflow\n"
            f"  2. Run [cyan]raw run {workflow_id} --dry[/] to test with mocked data\n"
            f"  3. Run [cyan]raw run {workflow_id}[/] to execute\n"
            f"  4. Run [cyan]raw status {workflow_id}[/] to check results",
            title="[bold]RAW[/]",
            border_style="green",
        )
    )


def print_workflow_list(workflows: list[dict[str, Any]]) -> None:
    """Print a table of workflows."""
    if not workflows:
        print_info("No workflows found. Create one with [cyan]raw create <name>[/]")
        return

    table = Table(title="Workflows")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Created")

    for wf in workflows:
        created = wf.get("created_at", "")
        if created:
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                created = dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                pass

        table.add_row(
            wf.get("id", "?"),
            wf.get("name", wf.get("short_name", "-")),
            wf.get("version", "-"),
            created,
        )

    console.print(table)


def print_run_result(
    workflow_id: str,
    exit_code: int,
    duration: float,
    stdout: str,
    stderr: str,
) -> None:
    """Print workflow run result."""
    if exit_code == 0:
        console.print()
        console.print(
            Panel(
                f"[bold green]Workflow completed successfully![/]\n\n"
                f"[bold]Workflow:[/] {workflow_id}\n"
                f"[bold]Duration:[/] {duration:.2f}s\n"
                f"[bold]Exit code:[/] {exit_code}",
                title="[bold green]✓ Success[/]",
                border_style="green",
            )
        )
    else:
        console.print()
        console.print(
            Panel(
                f"[bold red]Workflow failed![/]\n\n"
                f"[bold]Workflow:[/] {workflow_id}\n"
                f"[bold]Duration:[/] {duration:.2f}s\n"
                f"[bold]Exit code:[/] {exit_code}",
                title="[bold red]✗ Failed[/]",
                border_style="red",
            )
        )

    if stdout.strip():
        console.print("\n[bold]Output:[/]")
        console.print(stdout)

    if stderr.strip():
        console.print("\n[bold red]Errors:[/]")
        console.print(stderr)


def print_manifest_status(manifest: dict[str, Any]) -> None:
    """Print workflow status from manifest."""
    # Support both flat format (new) and nested format (legacy)
    if "run" in manifest:
        # Legacy nested format
        run = manifest.get("run", {})
        workflow = manifest.get("workflow", {})
        workflow_id = workflow.get("id", "?")
        run_id = run.get("run_id", "?")
        status = run.get("status", "unknown")
        duration = run.get("duration_seconds", 0)
        started = run.get("started_at", "-")
    else:
        # New flat format
        workflow_id = manifest.get("workflow_id", "?")
        run_id = manifest.get("run_id", "?")
        status = manifest.get("status", "unknown")
        duration = manifest.get("duration_seconds", 0)
        started = manifest.get("started_at", "-")

    steps = manifest.get("steps", [])
    status_color = "green" if status == "success" else "red" if status == "failed" else "yellow"

    console.print()
    console.print(
        Panel(
            f"[bold]Workflow:[/] {workflow_id}\n"
            f"[bold]Run ID:[/] {run_id}\n"
            f"[bold]Status:[/] [{status_color}]{status}[/]\n"
            f"[bold]Duration:[/] {duration:.2f}s\n"
            f"[bold]Started:[/] {started}",
            title="[bold]Workflow Status[/]",
            border_style=status_color,
        )
    )

    if steps:
        console.print("\n[bold]Steps:[/]")
        table = Table()
        table.add_column("Step", style="cyan")
        table.add_column("Status")
        table.add_column("Duration")
        table.add_column("Cached")

        for step in steps:
            step_status = step.get("status", "?")
            step_color = (
                "green"
                if step_status == "success"
                else "red"
                if step_status == "failed"
                else "yellow"
            )
            table.add_row(
                step.get("name", "?"),
                f"[{step_color}]{step_status}[/]",
                f"{step.get('duration_seconds', 0):.2f}s",
                "✓" if step.get("cached") else "-",
            )

        console.print(table)

    error = manifest.get("error")
    if error:
        console.print(f"\n[bold red]Error:[/] {error}")

    artifacts = manifest.get("artifacts", [])
    if artifacts:
        console.print("\n[bold]Artifacts:[/]")
        for artifact in artifacts:
            console.print(f"  • [{artifact.get('type')}] {artifact.get('path')}")


def print_workflow_details(config: WorkflowConfig, workflow_dir: Path) -> None:
    """Print detailed workflow information."""
    status_colors = {
        "draft": "yellow",
        "generated": "blue",
        "tested": "cyan",
        "published": "green",
    }
    status_color = status_colors.get(config.status, "white")

    content_lines = [
        f"[bold]Status:[/] [{status_color}]{config.status}[/]",
        f"[bold]Version:[/] {config.version}",
        f"[bold]Created:[/] {config.created_at.strftime('%Y-%m-%d %H:%M') if config.created_at else '-'}",
    ]

    if config.published_at:
        content_lines.append(
            f"[bold]Published:[/] {config.published_at.strftime('%Y-%m-%d %H:%M')}"
        )

    content_lines.append("")
    content_lines.append(f'[italic]"{config.description.intent}"[/]')

    if config.description.inputs:
        content_lines.append("")
        content_lines.append("[bold]Inputs:[/]")
        for inp in config.description.inputs:
            req = "" if inp.required else " (optional)"
            default = f" = {inp.default}" if inp.default is not None else ""
            content_lines.append(f"  • {inp.name} ({inp.type}){req}{default}")

    if config.steps:
        content_lines.append("")
        content_lines.append("[bold]Steps:[/]")
        for i, step in enumerate(config.steps, 1):
            outputs = ", ".join(o.name for o in step.outputs) if step.outputs else "(side effect)"
            version = f"@{step.tool_version}" if step.tool_version else ""
            content_lines.append(f"  {i}. [cyan]{step.tool}{version}[/] → {outputs}")
            content_lines.append(f"     [dim]{step.description}[/]")

    if config.description.outputs:
        content_lines.append("")
        content_lines.append("[bold]Outputs:[/]")
        for out in config.description.outputs:
            fmt = f" ({out.format})" if out.format else ""
            content_lines.append(f"  • {out.name} ({out.type}){fmt}")

    console.print(
        Panel(
            "\n".join(content_lines),
            title=f"[bold]Workflow: {config.id}[/]",
            subtitle=f"[dim]{workflow_dir}[/]",
            border_style=status_color,
        )
    )


def print_tool_details(config: ToolConfig, tool_dir: Path) -> None:
    """Print detailed tool information."""
    status_colors = {
        "draft": "yellow",
        "tested": "cyan",
        "published": "green",
    }
    status_color = status_colors.get(config.status, "white")

    content_lines = [
        f"[bold]Version:[/] {config.version}",
        f"[bold]Status:[/] [{status_color}]{config.status}[/]",
        "",
        f"[italic]{config.description}[/]",
    ]

    if config.inputs:
        content_lines.append("")
        content_lines.append("[bold]Inputs:[/]")
        for inp in config.inputs:
            req = "" if inp.required else " (optional)"
            default = f" = {inp.default}" if inp.default is not None else ""
            content_lines.append(f"  • {inp.name} ({inp.type}){req}{default}")

    if config.outputs:
        content_lines.append("")
        content_lines.append("[bold]Outputs:[/]")
        for out in config.outputs:
            content_lines.append(f"  • {out.name} ({out.type})")

    if config.dependencies:
        content_lines.append("")
        content_lines.append("[bold]Dependencies:[/]")
        for dep in config.dependencies:
            content_lines.append(f"  • {dep}")

    console.print(
        Panel(
            "\n".join(content_lines),
            title=f"[bold]Tool: {config.name}[/]",
            subtitle=f"[dim]{tool_dir}[/]",
            border_style=status_color,
        )
    )


def print_tools_list(tools: list[dict[str, Any]]) -> None:
    """Print a table of tools."""
    if not tools:
        print_info("No tools found.")
        return

    table = Table(title="Tools")
    table.add_column("Name", style="cyan")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Description")

    for tool in tools:
        status = tool.get("status", "?")
        status_color = {
            "draft": "yellow",
            "tested": "cyan",
            "published": "green",
        }.get(status, "white")

        desc = tool.get("description", "-")
        if len(desc) > 40:
            desc = desc[:37] + "..."

        table.add_row(
            tool.get("name", "?"),
            tool.get("version", "-"),
            f"[{status_color}]{status}[/]",
            desc,
        )

    console.print(table)


def print_draft_created(workflow_dir: Path, workflow_id: str, intent: str) -> None:
    """Print draft workflow creation success."""
    console.print()
    console.print(
        Panel(
            f"[bold yellow]Draft workflow created![/]\n\n"
            f"[bold]ID:[/] {workflow_id}\n"
            f"[bold]Path:[/] {workflow_dir}\n"
            f"[bold]Status:[/] [yellow]draft[/]\n\n"
            f"[bold]Intent:[/]\n"
            f"[italic]{intent}[/]\n\n"
            f"[dim]Next steps:[/]\n"
            f"  1. Implement [cyan]run.py[/] in the workflow directory\n"
            f"  2. Run [cyan]raw run {workflow_id} --dry[/] to test with mock data\n"
            f"  3. Run [cyan]raw publish {workflow_id}[/] when ready",
            title="[bold]RAW[/]",
            border_style="yellow",
        )
    )


def print_tool_created(tool_dir: Path, tool_name: str, description: str) -> None:
    """Print tool creation success."""
    console.print()
    console.print(
        Panel(
            f"[bold yellow]Tool scaffold created![/]\n\n"
            f"[bold]Name:[/] {tool_name}\n"
            f"[bold]Path:[/] {tool_dir}\n"
            f"[bold]Status:[/] [yellow]draft[/]\n\n"
            f"[italic]{description}[/]\n\n"
            f"[dim]Created:[/]\n"
            f"  • [cyan]config.yaml[/] - Tool configuration\n\n"
            f"[dim]To implement:[/]\n"
            f"  • [cyan]tool.py[/] - Tool logic\n"
            f"  • [cyan]__init__.py[/] - Exports\n"
            f"  • [cyan]test.py[/] - Tests",
            title="[bold]RAW Tool[/]",
            border_style="yellow",
        )
    )


def print_workflow_published(workflow_id: str, version: str) -> None:
    """Print workflow publish success."""
    console.print()
    console.print(
        Panel(
            f"[bold green]Workflow published![/]\n\n"
            f"[bold]ID:[/] {workflow_id}\n"
            f"[bold]Version:[/] {version}\n"
            f"[bold]Status:[/] [green]published[/]\n\n"
            f"[dim]The workflow is now immutable. To modify, use:[/]\n"
            f"  [cyan]raw create <name> --from {workflow_id}[/]",
            title="[bold]RAW[/]",
            border_style="green",
        )
    )


def print_workflow_duplicated(
    source_id: str,
    new_id: str,
    new_dir: Path,
) -> None:
    """Print workflow duplication success."""
    console.print()
    console.print(
        Panel(
            f"[bold cyan]Workflow duplicated![/]\n\n"
            f"[bold]Source:[/] {source_id}\n"
            f"[bold]New ID:[/] {new_id}\n"
            f"[bold]Path:[/] {new_dir}\n"
            f"[bold]Status:[/] [yellow]draft[/]\n\n"
            f"[dim]Next steps:[/]\n"
            f"  1. Modify the workflow as needed\n"
            f"  2. Run [cyan]raw run {new_id} --dry[/] to test\n"
            f"  3. Run [cyan]raw publish {new_id}[/] when ready",
            title="[bold]RAW[/]",
            border_style="cyan",
        )
    )


def print_search_results(results: list[dict[str, Any]], query: str) -> None:
    """Print tool search results."""
    if not results:
        print_info(f"No tools found matching: [cyan]{query}[/]")
        return

    console.print()
    console.print(f"[bold]Search results for:[/] [cyan]{query}[/]")
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Score", justify="right", style="yellow")
    table.add_column("Version")
    table.add_column("Description")

    for result in results:
        desc = result.get("description", "-")
        if len(desc) > 60:
            desc = desc[:57] + "..."

        score = result.get("score", 0.0)
        table.add_row(
            result.get("name", "?"),
            f"{score:.2f}",
            result.get("version", "-"),
            desc,
        )

    console.print(table)
    console.print()
    console.print(f"[dim]Found {len(results)} tool(s)[/]")
    console.print("[dim]Use 'raw show <name>' to see details[/]")

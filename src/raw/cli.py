"""RAW CLI - Main entry point.

Simplified CLI with 5 core commands:
- init: Setup RAW in a project
- create: Create workflows and tools
- run: Execute workflows
- list: List workflows and tools
- show: View details, logs, and context
"""

from typing import Annotated

import typer
from rich.prompt import Prompt

from raw import __version__
from raw.commands import (
    build_command,
    create_command,
    hooks_install_command,
    init_command,
    list_command,
    logs_command,
    prime_command,
    run_command,
    search_command,
    show_command,
    trigger_command,
    validate_command,
)
from raw.discovery.display import console
from raw.discovery.workflow import list_workflows
from raw.scaffold.init import list_tools

app = typer.Typer(
    help="RAW - Run Agentic Workflows.\n\nAgent-first workflow orchestration for Claude Code.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"raw {__version__}")
        raise typer.Exit()


def _prompt_workflow_selection(action: str = "select") -> str | None:
    """Prompt user to select a workflow interactively."""
    workflows = list_workflows()
    if not workflows:
        return None

    console.print()
    console.print(f"[bold]Select a workflow to {action}:[/]")
    console.print()

    choices = []
    for i, wf in enumerate(workflows, 1):
        status_color = {"draft": "yellow", "published": "green"}.get(wf["status"], "dim")
        console.print(f"  [cyan]{i}[/]) {wf['id']} [{status_color}]{wf['status']}[/]")
        choices.append(str(i))

    console.print()
    choice = Prompt.ask("Enter number", choices=choices, show_choices=False)
    return workflows[int(choice) - 1]["id"]


def _prompt_tool_selection(action: str = "select") -> str | None:
    """Prompt user to select a tool interactively."""
    tool_list = list_tools()
    if not tool_list:
        return None

    console.print()
    console.print(f"[bold]Select a tool to {action}:[/]")
    console.print()

    choices = []
    for i, tool in enumerate(tool_list, 1):
        console.print(f"  [cyan]{i}[/]) {tool['name']} - [dim]{tool['description'][:50]}...[/]")
        choices.append(str(i))

    console.print()
    choice = Prompt.ask("Enter number", choices=choices, show_choices=False)
    return tool_list[int(choice) - 1]["name"]


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = False,
) -> None:
    """RAW - Run Agentic Workflows."""
    pass


@app.command()
def init(
    hooks: Annotated[
        bool, typer.Option("--hooks", help="Also install Claude Code hooks")
    ] = False,
) -> None:
    """Initialize RAW in the current project.

    Creates .raw/ directory with configuration and workflow directories.

    Examples:
        raw init              # Basic setup
        raw init --hooks      # Setup + install Claude Code hooks
    """
    init_command()
    if hooks:
        hooks_install_command()


@app.command()
def create(
    name: Annotated[str, typer.Argument(help="Short name (e.g., stock-analysis, fetch_prices)")],
    intent: Annotated[
        str | None,
        typer.Option("--intent", "-i", help="Workflow intent (will prompt if not provided)"),
    ] = None,
    from_workflow: Annotated[
        str | None,
        typer.Option("--from", help="Duplicate from existing workflow ID"),
    ] = None,
    tool: Annotated[
        bool, typer.Option("--tool", "-t", help="Create a reusable tool instead of a workflow")
    ] = False,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Tool description (required with --tool)"),
    ] = None,
) -> None:
    """Create a new workflow or tool.

    Examples:
        raw create my-workflow --intent "Fetch and analyze data"
        raw create my_tool --tool -d "Fetch stock prices from API"
        raw create new-workflow --from existing-workflow
    """
    create_command(name, intent, from_workflow, tool, description, scaffold=False)


@app.command()
def build(
    workflow_id: Annotated[
        str | None,
        typer.Argument(help="Workflow identifier to build"),
    ] = None,
    max_iterations: Annotated[
        int | None,
        typer.Option("--max-iterations", help="Maximum plan-execute cycles (default: 10)"),
    ] = None,
    max_minutes: Annotated[
        int | None,
        typer.Option("--max-minutes", help="Maximum wall time in minutes (default: 30)"),
    ] = None,
    resume: Annotated[
        str | None,
        typer.Option("--resume", help="Resume from specific build ID"),
    ] = None,
    last: Annotated[
        bool, typer.Option("--last", help="Resume from last build")
    ] = False,
) -> None:
    """Build a workflow using the agentic builder loop.

    The builder implements plan → execute → verify → iterate cycles:
    1. Plan mode: Analyze requirements, create numbered plan (read-only)
    2. Execute mode: Apply changes to workflow and tools
    3. Verify: Run quality gates (validate, dry, optional tests)
    4. Iterate: If gates fail, feed failures into next plan cycle

    Exit Codes:
        0 - Success (all gates passed)
        1 - Failed (gates failed or budget exceeded)
        2 - Stuck (unable to make progress after iterations)

    Examples:
        raw build my-workflow                    # Build with defaults
        raw build my-workflow --max-iterations 5 # Limit cycles
        raw build my-workflow --max-minutes 15   # Time budget
        raw build --resume build-abc123          # Resume specific build
        raw build --last                         # Resume last build
    """
    if resume and last:
        typer.echo("Error: Cannot use both --resume and --last")
        raise typer.Exit(1)

    build_command(workflow_id, max_iterations, max_minutes, resume, last, _prompt_workflow_selection)


@app.command()
def validate(
    workflow_id: Annotated[
        str | None,
        typer.Argument(help="Workflow identifier to validate"),
    ] = None,
) -> None:
    """Validate workflow structure and dependencies.

    Checks:
    - run.py exists and is valid Python
    - PEP 723 metadata is present and correct
    - Imported tools exist in tools/ directory
    - Workflow uses BaseWorkflow pattern
    - run() method is implemented

    Exit Codes:
        0 - Validation passed
        1 - Validation failed (errors found)

    Examples:
        raw validate my-workflow     # Validate specific workflow
        raw validate                 # Prompt for workflow
    """
    validate_command(workflow_id, _prompt_workflow_selection)


@app.command()
def run(
    ctx: typer.Context,
    workflow_id: Annotated[
        str | None,
        typer.Argument(help="Workflow identifier (full or partial)"),
    ] = None,
    dry: Annotated[
        bool, typer.Option("--dry", help="Run with mocked data (uses dry_run.py)")
    ] = False,
    init_dry: Annotated[
        bool, typer.Option("--init", help="Generate dry_run.py template (use with --dry)")
    ] = False,
    remote: Annotated[
        bool, typer.Option("--remote", help="Trigger via RAW server instead of local execution")
    ] = False,
) -> None:
    """Run a workflow.

    Examples:
        raw run my-workflow
        raw run my-workflow --dry         # Test with mock data
        raw run my-workflow --dry --init  # Generate mock template
        raw run my-workflow --remote      # Trigger via server
    """
    if remote:
        args = ctx.args if ctx.args else []
        trigger_command(workflow_id, args, _prompt_workflow_selection)
    else:
        run_command(ctx, workflow_id, dry, init_dry, _prompt_workflow_selection)


@app.command("list")
def list_cmd(
    what: Annotated[str, typer.Argument(help="What to list: workflows or tools")] = "workflows",
    search: Annotated[
        str | None,
        typer.Option("--search", "-s", help="Search tools by description"),
    ] = None,
) -> None:
    """List workflows or tools.

    Examples:
        raw list              # List workflows
        raw list tools        # List tools
        raw list tools -s "fetch stock"  # Search tools
    """
    if search and what == "tools":
        search_command(search)
    else:
        list_command(what)


@app.command()
def show(
    identifier: Annotated[
        str | None,
        typer.Argument(help="Workflow ID or tool name"),
    ] = None,
    logs: Annotated[
        bool, typer.Option("--logs", "-l", help="Show execution logs")
    ] = False,
    context: Annotated[
        bool, typer.Option("--context", "-c", help="Output agent context (for hooks)")
    ] = False,
    follow: Annotated[
        bool, typer.Option("--follow", "-f", help="Follow log output (with --logs)")
    ] = False,
    lines: Annotated[
        int, typer.Option("--lines", "-n", help="Number of log lines (with --logs)")
    ] = 50,
) -> None:
    """Show details for a workflow or tool.

    Examples:
        raw show my-workflow           # Show workflow details
        raw show my-workflow --logs    # Show execution logs
        raw show my-workflow -l -f     # Follow logs
        raw show --context             # Output agent context
    """
    if context:
        prime_command()
    elif logs:
        logs_command(identifier, None, follow, lines, _prompt_workflow_selection)
    else:
        show_command(identifier, _prompt_workflow_selection, runs=False)


# Backward compatibility alias
cli = app

if __name__ == "__main__":
    app()

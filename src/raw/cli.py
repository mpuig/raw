"""RAW CLI - Main entry point.

Uses Typer for argument parsing with automatic shell completion.
Business logic is delegated to modules in raw.commands.
"""

from typing import Annotated, Optional

import typer
from rich.prompt import Prompt

from raw import __version__
from raw.commands import (
    create_command,
    hooks_install_command,
    hooks_uninstall_command,
    init_command,
    install_command,
    list_command,
    logs_command,
    onboard_command,
    prime_command,
    publish_command,
    run_command,
    search_command,
    serve_command,
    show_command,
    stop_command,
    trigger_command,
    uninstall_command,
)
from raw.discovery.display import console
from raw.discovery.workflow import list_workflows
from raw.scaffold.init import list_tools

app = typer.Typer(
    help="RAW - Run Agentic Workflows.\n\nAgent-first workflow orchestration for Claude Code.",
    no_args_is_help=True,
)

hooks_app = typer.Typer(help="Manage Claude Code hooks for automatic context injection.")
app.add_typer(hooks_app, name="hooks")


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
def create(
    name: Annotated[str, typer.Argument(help="Short name (e.g., stock-analysis, fetch_prices)")],
    intent: Annotated[
        Optional[str],
        typer.Option("--intent", "-i", help="Workflow intent (will prompt if not provided)"),
    ] = None,
    from_workflow: Annotated[
        Optional[str],
        typer.Option("--from", help="Duplicate from existing workflow ID"),
    ] = None,
    tool: Annotated[
        bool, typer.Option("--tool", "-t", help="Create a reusable tool instead of a workflow")
    ] = False,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Tool description (required with --tool)"),
    ] = None,
    scaffold: Annotated[
        bool,
        typer.Option("--scaffold", hidden=True, help="Create v0.1.0 scaffold (deprecated)"),
    ] = False,
) -> None:
    """Create a new workflow or tool.

    Examples:
        raw create my-workflow --intent "Fetch and analyze data"
        raw create my_tool --tool -d "Fetch stock prices from API"
        raw create new-workflow --from existing-workflow
    """
    create_command(name, intent, from_workflow, tool, description, scaffold)


@app.command()
def run(
    ctx: typer.Context,
    workflow_id: Annotated[
        Optional[str],
        typer.Argument(help="Workflow identifier (full or partial). Prompts if not provided."),
    ] = None,
    dry: Annotated[
        bool, typer.Option("--dry", help="Run with mocked data (uses dry_run.py)")
    ] = False,
    init: Annotated[
        bool, typer.Option("--init", help="Generate dry_run.py template (use with --dry)")
    ] = False,
) -> None:
    """Run a workflow.

    Additional arguments are passed to the workflow script.

    Use --dry to run with mocked data (executes dry_run.py).
    Use --dry --init to generate the dry_run.py template.
    """
    run_command(ctx, workflow_id, dry, init, _prompt_workflow_selection)


@app.command("list")
def list_cmd(
    what: Annotated[str, typer.Argument(help="What to list: workflows or tools")] = "workflows",
) -> None:
    """List workflows or tools."""
    list_command(what)


@app.command()
def init() -> None:
    """Initialize RAW in the current project.

    Creates a .raw/ directory with configuration and directories for workflows.
    Run this once after adding RAW to your project with 'uv add raw'.
    """
    init_command()


@app.command()
def install(
    source: Annotated[str, typer.Argument(help="Git repository URL")],
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help="Override tool name (derived from URL if not provided)"),
    ] = None,
    ref: Annotated[
        Optional[str],
        typer.Option("--ref", "-r", help="Git ref (tag, branch, or commit)"),
    ] = None,
) -> None:
    """Install a tool from a git URL.

    Examples:
        raw install https://github.com/user/tool-repo
        raw install https://github.com/user/tool-repo --ref v1.0.0
        raw install https://github.com/user/tool-repo --name my_tool
    """
    install_command(source, name, ref)


@app.command()
def uninstall(
    name: Annotated[str, typer.Argument(help="Tool name to uninstall")],
) -> None:
    """Uninstall a tool.

    Example:
        raw uninstall my_tool
    """
    uninstall_command(name)


@app.command()
def onboard() -> None:
    """Display RAW documentation for AI agents.

    Outputs comprehensive RAW documentation including architecture,
    workflow creation process, and tool management.
    """
    onboard_command()


@app.command()
def prime() -> None:
    """Output context for AI agents.

    Designed to be injected into Claude Code's context at session start.
    Outputs a summary of:
    - Available workflows with status and intent
    - Available tools with descriptions
    - Quick command reference

    Example usage in a Claude Code hook:
        raw prime >> /tmp/raw-context.md
    """
    prime_command()


@hooks_app.command("install")
def hooks_install() -> None:
    """Install RAW hooks into Claude Code (project-level).

    Adds SessionStart and PreCompact hooks that run 'raw prime' to inject
    workflow context automatically when Claude Code sessions start.

    Hooks are installed in .claude/settings.local.json (project-level).
    """
    hooks_install_command()


@hooks_app.command("uninstall")
def hooks_uninstall() -> None:
    """Remove RAW hooks from Claude Code.

    Removes the SessionStart and PreCompact hooks that were installed
    by 'raw hooks install'.
    """
    hooks_uninstall_command()


@app.command()
def show(
    identifier: Annotated[
        Optional[str],
        typer.Argument(help="Workflow ID or partial match. Prompts if not provided."),
    ] = None,
    runs: Annotated[
        bool, typer.Option("--runs", "-r", help="Show execution history instead of details")
    ] = False,
) -> None:
    """Show details for a workflow or tool.

    Use --runs to see execution history instead of workflow details.

    Examples:
        raw show my-workflow          # Show workflow details
        raw show my-workflow --runs   # Show execution history
        raw show my-tool              # Show tool details
    """
    show_command(identifier, _prompt_workflow_selection, runs)


@app.command()
def publish(
    workflow_id: Annotated[
        Optional[str],
        typer.Argument(help="Workflow identifier (full or partial). Prompts if not provided."),
    ] = None,
) -> None:
    """Publish a workflow, making it immutable.

    Publishing freezes the workflow and pins all tool versions.
    After publishing, the workflow cannot be modified.
    Use 'raw create <name> --from <id>' to create a modifiable copy.
    """
    publish_command(workflow_id, _prompt_workflow_selection)


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query describing what you're looking for")],
) -> None:
    """Search for tools by description.

    Always search before creating new tools to avoid duplicates.

    Examples:
        raw search "fetch stock prices"
        raw search "send email"
    """
    search_command(query)


@app.command()
def serve(
    host: Annotated[
        str, typer.Option("--host", "-h", help="Host to bind to")
    ] = "0.0.0.0",
    port: Annotated[
        int, typer.Option("--port", "-p", help="Port to listen on")
    ] = 8000,
) -> None:
    """Start RAW daemon server for webhooks and approvals.

    Runs a FastAPI server that provides:
    - POST /webhook/{workflow_id} - Trigger workflow via HTTP
    - GET /approvals - List pending approval requests
    - POST /approve/{workflow_id}/{step_name} - Resolve approval
    - GET /workflows - List available workflows
    - GET /runs - List active workflow runs

    Install dependencies: uv add raw[serve]
    """
    serve_command(host, port)


@app.command()
def trigger(
    ctx: typer.Context,
    workflow_id: Annotated[
        Optional[str],
        typer.Argument(help="Workflow identifier (full or partial)"),
    ] = None,
) -> None:
    """Trigger a workflow via the RAW server.

    Additional arguments are passed to the workflow.

    Examples:
        raw trigger my-workflow
        raw trigger my-workflow --ticker AAPL
    """
    args = ctx.args if ctx.args else []
    trigger_command(workflow_id, args, _prompt_workflow_selection)


@app.command()
def logs(
    workflow_id: Annotated[
        Optional[str],
        typer.Argument(help="Workflow identifier (full or partial)"),
    ] = None,
    run_id: Annotated[
        Optional[str],
        typer.Option("--run", "-r", help="Specific run ID (defaults to latest)"),
    ] = None,
    follow: Annotated[
        bool, typer.Option("--follow", "-f", help="Follow log output")
    ] = False,
    lines: Annotated[
        int, typer.Option("--lines", "-n", help="Number of lines to show")
    ] = 50,
) -> None:
    """View workflow execution logs.

    Shows the most recent run by default.

    Examples:
        raw logs my-workflow
        raw logs my-workflow --follow
        raw logs my-workflow -r 20251208-123456
    """
    logs_command(workflow_id, run_id, follow, lines, _prompt_workflow_selection)


@app.command()
def stop(
    run_id: Annotated[
        Optional[str],
        typer.Argument(help="Run identifier to stop"),
    ] = None,
    all_runs: Annotated[
        bool, typer.Option("--all", help="Stop all running workflows")
    ] = False,
) -> None:
    """Stop running workflows.

    Use --all to stop all running workflows.

    Examples:
        raw stop                     # List running workflows
        raw stop run_20251208_1234   # Stop specific run
        raw stop --all               # Stop all
    """
    stop_command(run_id, all_runs)


# For backward compatibility with entry point
cli = app

if __name__ == "__main__":
    app()

"""RAW CLI - Main entry point.

This module defines the Click command structure and argument parsing.
Business logic is delegated to modules in raw.commands.
"""

import click
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


@click.group()
@click.version_option(version=__version__, prog_name="raw")
def cli() -> None:
    """RAW - Run Agentic Workflows.

    Agent-first workflow orchestration for Claude Code.
    """
    pass


@cli.command()
@click.argument("name")
@click.option("--intent", "-i", help="Workflow intent (will prompt if not provided)")
@click.option("--from", "from_workflow", help="Duplicate from existing workflow ID")
@click.option("--tool", "-t", is_flag=True, help="Create a reusable tool instead of a workflow")
@click.option("--description", "-d", help="Tool description (required with --tool)")
@click.option(
    "--scaffold", is_flag=True, hidden=True, help="Create v0.1.0 scaffold (deprecated)"
)
def create(
    name: str,
    intent: str | None,
    from_workflow: str | None,
    tool: bool,
    description: str | None,
    scaffold: bool,
) -> None:
    """Create a new workflow or tool.

    NAME is the short name (e.g., stock-analysis, fetch_prices).

    Examples:
        raw create my-workflow --intent "Fetch and analyze data"
        raw create my_tool --tool -d "Fetch stock prices from API"
        raw create new-workflow --from existing-workflow
    """
    create_command(name, intent, from_workflow, tool, description, scaffold)


@cli.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("workflow_id", required=False)
@click.option("--dry", is_flag=True, help="Run with mocked data (uses dry_run.py)")
@click.option("--init", is_flag=True, help="Generate dry_run.py template (use with --dry)")
@click.pass_context
def run(ctx: click.Context, workflow_id: str | None, dry: bool, init: bool) -> None:
    """Run a workflow.

    WORKFLOW_ID is the workflow identifier (full or partial).
    If not provided, prompts for selection.
    Additional arguments are passed to the workflow script.

    Use --dry to run with mocked data (executes dry_run.py).
    Use --dry --init to generate the dry_run.py template.
    """
    run_command(ctx, workflow_id, dry, init, _prompt_workflow_selection)


@cli.command("list")
@click.argument("what", default="workflows", required=False)
def list_cmd(what: str) -> None:
    """List workflows.

    Lists all workflows in the project.
    """
    list_command(what)


@cli.command()
def init() -> None:
    """Initialize RAW in the current project.

    Creates a .raw/ directory with configuration and directories for workflows.
    Run this once after adding RAW to your project with 'uv add raw'.
    """
    init_command()


@cli.command()
@click.argument("source")
@click.option("--name", "-n", help="Override tool name (derived from URL if not provided)")
@click.option("--ref", "-r", help="Git ref (tag, branch, or commit)")
def install(source: str, name: str | None, ref: str | None) -> None:
    """Install a tool from a git URL.

    SOURCE is the git repository URL.

    Examples:
        raw install https://github.com/user/tool-repo
        raw install https://github.com/user/tool-repo --ref v1.0.0
        raw install https://github.com/user/tool-repo --name my_tool
    """
    install_command(source, name, ref)


@cli.command()
@click.argument("name")
def uninstall(name: str) -> None:
    """Uninstall a tool.

    NAME is the tool name to uninstall.

    Example:
        raw uninstall my_tool
    """
    uninstall_command(name)


@cli.command()
def onboard() -> None:
    """Display RAW documentation for AI agents.

    Outputs comprehensive RAW documentation including architecture,
    workflow creation process, and tool management.
    """
    onboard_command()


@cli.command()
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


@cli.group()
def hooks() -> None:
    """Manage Claude Code hooks for automatic context injection."""
    pass


@hooks.command("install")
def hooks_install() -> None:
    """Install RAW hooks into Claude Code (project-level).

    Adds SessionStart and PreCompact hooks that run 'raw prime' to inject
    workflow context automatically when Claude Code sessions start.

    Hooks are installed in .claude/settings.local.json (project-level).
    """
    hooks_install_command()


@hooks.command("uninstall")
def hooks_uninstall() -> None:
    """Remove RAW hooks from Claude Code.

    Removes the SessionStart and PreCompact hooks that were installed
    by 'raw hooks install'.
    """
    hooks_uninstall_command()


@cli.command()
@click.argument("identifier", required=False)
@click.option("--runs", "-r", is_flag=True, help="Show execution history instead of details")
def show(identifier: str | None, runs: bool) -> None:
    """Show details for a workflow or tool.

    IDENTIFIER is a workflow ID or partial match.
    If not provided, prompts for selection.

    Use --runs to see execution history instead of workflow details.

    Examples:
        raw show my-workflow          # Show workflow details
        raw show my-workflow --runs   # Show execution history
        raw show my-tool              # Show tool details
    """
    show_command(identifier, _prompt_workflow_selection, runs)


@cli.command()
@click.argument("workflow_id", required=False)
def publish(workflow_id: str | None) -> None:
    """Publish a workflow, making it immutable.

    WORKFLOW_ID is the workflow identifier (full or partial).
    If not provided, prompts for selection.

    Publishing freezes the workflow and pins all tool versions.
    After publishing, the workflow cannot be modified.
    Use 'raw create <name> --from <id>' to create a modifiable copy.
    """
    publish_command(workflow_id, _prompt_workflow_selection)


@cli.command()
@click.argument("query")
def search(query: str) -> None:
    """Search for tools by description.

    QUERY is the search query describing what you're looking for.
    Always search before creating new tools to avoid duplicates.

    Examples:
        raw search "fetch stock prices"
        raw search "send email"
    """
    search_command(query)


@cli.command()
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
@click.option("--port", "-p", default=8000, type=int, help="Port to listen on (default: 8000)")
def serve(host: str, port: int) -> None:
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


@cli.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("workflow_id", required=False)
@click.pass_context
def trigger(ctx: click.Context, workflow_id: str | None) -> None:
    """Trigger a workflow via the RAW server.

    WORKFLOW_ID is the workflow identifier (full or partial).
    Additional arguments are passed to the workflow.

    Examples:
        raw trigger my-workflow
        raw trigger my-workflow --ticker AAPL
    """
    trigger_command(workflow_id, ctx.args, _prompt_workflow_selection)


@cli.command()
@click.argument("workflow_id", required=False)
@click.option("--run", "-r", "run_id", help="Specific run ID (defaults to latest)")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--lines", "-n", default=50, help="Number of lines to show (default: 50)")
def logs(workflow_id: str | None, run_id: str | None, follow: bool, lines: int) -> None:
    """View workflow execution logs.

    WORKFLOW_ID is the workflow identifier (full or partial).
    Shows the most recent run by default.

    Examples:
        raw logs my-workflow
        raw logs my-workflow --follow
        raw logs my-workflow -r 20251208-123456
    """
    logs_command(workflow_id, run_id, follow, lines, _prompt_workflow_selection)


@cli.command()
@click.argument("run_id", required=False)
@click.option("--all", "all_runs", is_flag=True, help="Stop all running workflows")
def stop(run_id: str | None, all_runs: bool) -> None:
    """Stop running workflows.

    RUN_ID is the run identifier to stop.
    Use --all to stop all running workflows.

    Examples:
        raw stop                     # List running workflows
        raw stop run_20251208_1234   # Stop specific run
        raw stop --all               # Stop all
    """
    stop_command(run_id, all_runs)


if __name__ == "__main__":
    cli()

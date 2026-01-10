"""Agent management commands."""

from typing import Annotated

import typer

app = typer.Typer(help="Agent management commands")


@app.command()
def run(
    agent_name: Annotated[str, typer.Argument(help="Name of the agent to run")],
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Run in interactive mode")] = False,
):
    """Run an agent."""
    typer.echo(f"Running agent: {agent_name}")
    if interactive:
        typer.echo("Mode: interactive")
    typer.echo("[Placeholder - not yet implemented]")


@app.command("list")
def list_agents():
    """List available agents."""
    typer.echo("Available agents:")
    typer.echo("[Placeholder - not yet implemented]")

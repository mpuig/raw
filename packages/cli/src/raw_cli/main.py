"""RAW CLI - Main entry point."""

import typer
from typing_extensions import Annotated

from raw_cli.commands import agent, bot, create

app = typer.Typer(
    name="raw",
    help="RAW Platform CLI - unified command-line interface for bots, agents, and creation tools",
    no_args_is_help=True,
)

# Register subcommands
app.add_typer(bot.app, name="bot", help="Bot management commands")
app.add_typer(agent.app, name="agent", help="Agent management commands")
app.add_typer(create.app, name="create", help="Creation commands for bots, agents, and tools")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

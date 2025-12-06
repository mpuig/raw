"""Onboard command implementation."""

import click
from pathlib import Path

from raw.discovery.display import console, print_info, print_success, print_warning
from raw.scaffold.markdown import render_onboard

AGENTS_MD_PATH = Path("AGENTS.md")

def onboard_command() -> None:
    """Interactively create or update AGENTS.md with RAW agent instructions.

    This function contains the business logic for the onboard command.
    """
    generated_content = render_onboard()

    if AGENTS_MD_PATH.exists():
        existing_content = AGENTS_MD_PATH.read_text()
        if existing_content.strip() == generated_content.strip():
            print_info("AGENTS.md is already up to date.")
            console.print("  To manually view the instructions, open AGENTS.md.")
            return
        else:
            # Content is different, prompt to update
            print_warning("AGENTS.md exists but is outdated.")
            if not click.confirm("Would you like to update AGENTS.md with the latest agent instructions?", default=True):
                console.print("  Update skipped. To manually update, run: [cyan]raw onboard > AGENTS.md[/]")
                return
    else:
        # File doesn't exist, prompt to create
        if not click.confirm("AGENTS.md not found. Would you like to create it with agent integration instructions?", default=True):
            console.print("  Creation skipped. To manually create, run: [cyan]raw onboard > AGENTS.md[/]")
            return

    try:
        AGENTS_MD_PATH.write_text(generated_content)
        print_success("AGENTS.md created/updated successfully.")
        console.print("  Your agent can now read the latest RAW instructions from AGENTS.md.")
        console.print("  Consider running [cyan]raw hooks install[/] for automatic agent context injection.")
    except Exception as e:
        console.print(f"[red]Error:[/]")
        console.print(f"  Failed to write AGENTS.md: {e}")

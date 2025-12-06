"""Init command implementation."""

from raw.discovery.display import console, print_error, print_info, print_success
from raw.scaffold.init import init_raw_project, is_raw_initialized


def init_command() -> None:
    """Initialize RAW in the current project.

    This function contains the business logic for the init command.
    """
    if is_raw_initialized():
        print_info("RAW is already initialized in this project")
        console.print("  Run 'raw list' to see workflows")
        console.print("  Run 'raw create <name>' to create a new workflow")
        return

    try:
        raw_dir = init_raw_project()
        print_success(f"Initialized RAW in {raw_dir}")
        console.print()
        console.print("[bold]Next steps:[/]")
        console.print("  1. Run [cyan]raw hooks install[/] to enable automatic agent context")
        console.print("  2. Run [cyan]raw onboard[/] if you need manual agent setup instructions")
        console.print("  3. Ask your agent: [green]\"Create a workflow to...\"[/]")
    except Exception as e:
        print_error(f"Failed to initialize RAW: {e}")
        raise SystemExit(1) from None

"""Prime command implementation."""

from raw.discovery.display import console, print_error
from raw.scaffold.init import get_prime_content, is_raw_initialized


def prime_command() -> None:
    """Output context for AI agents.

    This function contains the business logic for the prime command.
    """
    if not is_raw_initialized():
        print_error("RAW is not initialized in this project")
        console.print("  Run 'raw init' first")
        raise SystemExit(1)

    console.print(get_prime_content())

"""Search command implementation."""

from raw.discovery.display import console, print_error, print_search_results
from raw.scaffold.init import is_raw_initialized


def search_command(query: str) -> None:
    """Search for tools using semantic similarity.

    This function contains the business logic for the search command.
    """
    from raw.discovery.search import is_semantic_available, search_tools

    if not is_raw_initialized():
        print_error("RAW is not initialized in this project")
        console.print("  Run 'raw init' first")
        raise SystemExit(1)

    mode = "semantic" if is_semantic_available() else "keyword"
    console.print(f"[dim]Searching ({mode} mode)...[/]")

    try:
        results = search_tools(query)
        print_search_results(results, query)
    except Exception as e:
        print_error(f"Search failed: {e}")
        raise SystemExit(1) from None

"""Install command implementation."""

from pathlib import Path

from raw.discovery.display import console, print_error, print_info
from raw.discovery.git_fetcher import GitToolFetcher
from raw.discovery.registry import get_tool_registry, set_tool_registry


def install_command(
    source: str,
    name: str | None = None,
    ref: str | None = None,
) -> None:
    """Install a tool from a git URL.

    Args:
        source: Git URL to install from
        name: Override tool name (derived from URL if not provided)
        ref: Git ref (tag, branch, commit) to checkout
    """
    fetcher = GitToolFetcher(Path("tools"))

    console.print()
    console.print(f"[bold]Installing tool from:[/] {source}")
    if ref:
        console.print(f"[dim]Version:[/] {ref}")
    console.print()

    result = fetcher.fetch(
        git_url=source,
        name=name,
        ref=ref,
        vendor=True,
    )

    if not result.success:
        print_error(result.error or "Unknown error")
        raise SystemExit(1)

    # Invalidate registry cache so new tool is discoverable
    set_tool_registry(None)
    registry = get_tool_registry()

    tool_info = registry.get_tool(name or result.tool_path.name) if result.tool_path else None

    console.print(f"[green]✓[/] Tool installed successfully!")
    console.print()
    console.print(f"[bold]Name:[/] {tool_info.name if tool_info else result.tool_path.name}")
    console.print(f"[bold]Path:[/] {result.tool_path}")
    if result.version:
        console.print(f"[bold]Version:[/] {result.version}")
    if tool_info and tool_info.description:
        console.print(f"[bold]Description:[/] {tool_info.description}")
    console.print()
    console.print("[dim]Usage:[/]")
    tool_name = tool_info.name if tool_info else result.tool_path.name
    console.print(f"  from tools.{tool_name} import ...")


def uninstall_command(name: str) -> None:
    """Uninstall a tool.

    Args:
        name: Tool name to uninstall
    """
    fetcher = GitToolFetcher(Path("tools"))

    console.print()
    console.print(f"[bold]Uninstalling tool:[/] {name}")
    console.print()

    result = fetcher.remove(name)

    if not result.success:
        print_error(result.error or "Unknown error")
        raise SystemExit(1)

    # Invalidate registry cache
    set_tool_registry(None)

    console.print(f"[green]✓[/] Tool '{name}' uninstalled successfully!")

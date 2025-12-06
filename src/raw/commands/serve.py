"""Serve command implementation."""

from raw.discovery.display import console, print_error, print_info
from raw.scaffold.init import is_raw_initialized


def serve_command(host: str, port: int) -> None:
    """Start RAW daemon server for webhooks and approvals.

    This function contains the business logic for the serve command.
    """
    try:
        from raw.engine.server import run_server
    except ImportError:
        print_error("Server dependencies not installed")
        console.print("  Install with: uv add raw[serve]")
        raise SystemExit(1)

    if not is_raw_initialized():
        print_error("RAW is not initialized in this project")
        console.print("  Run 'raw init' first")
        raise SystemExit(1)

    print_info(f"Starting RAW server on http://{host}:{port}")
    console.print()
    console.print("[dim]Endpoints:[/]")
    console.print(f"  POST http://{host}:{port}/webhook/<workflow_id>")
    console.print(f"  GET  http://{host}:{port}/approvals")
    console.print(f"  POST http://{host}:{port}/approve/<workflow_id>/<step>")
    console.print()

    try:
        run_server(host=host, port=port)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print_error(f"Server failed: {e}")
        raise SystemExit(1) from None

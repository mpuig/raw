"""CLI-to-SDK parity checking.

This module provides utilities to verify that SDK functions exist for CLI commands,
ensuring agents can do programmatically what users do via CLI.
"""

from typing import Any


# CLI commands and their expected SDK equivalents
CLI_COMMANDS = [
    {
        "command": "raw init",
        "description": "Initialize RAW in project",
        "sdk_function": None,
        "status": "missing",
        "notes": "System setup command - needs SDK wrapper",
    },
    {
        "command": "raw create <name> --intent",
        "description": "Create workflow with intent",
        "sdk_function": "create_workflow",
        "status": "full",
        "notes": "Creates draft workflow",
    },
    {
        "command": "raw create <name> --tool -d",
        "description": "Create reusable tool",
        "sdk_function": "create_tool",
        "status": "full",
        "notes": "Tool creation in SDK",
    },
    {
        "command": "raw create <name> --from <id>",
        "description": "Duplicate existing workflow",
        "sdk_function": "duplicate_workflow",
        "status": "partial",
        "notes": "SDK requires path, not ID",
    },
    {
        "command": "raw list",
        "description": "List all workflows",
        "sdk_function": "list_workflows",
        "status": "full",
        "notes": "Lists all workflows",
    },
    {
        "command": "raw list tools",
        "description": "List all tools",
        "sdk_function": "list_tools",
        "status": "full",
        "notes": "Tool listing in SDK",
    },
    {
        "command": "raw list tools -s",
        "description": "Search tools by query",
        "sdk_function": None,
        "status": "missing",
        "notes": "Search not in SDK yet",
    },
    {
        "command": "raw run <id>",
        "description": "Execute workflow",
        "sdk_function": "Container.workflow_runner",
        "status": "partial",
        "notes": "Can use runner directly, but awkward",
    },
    {
        "command": "raw run <id> --dry",
        "description": "Execute with mocks",
        "sdk_function": "Container.workflow_runner",
        "status": "partial",
        "notes": "Can use runner directly, but awkward",
    },
    {
        "command": "raw run <id> --dry --init",
        "description": "Generate mock template",
        "sdk_function": None,
        "status": "missing",
        "notes": "Not exposed in SDK",
    },
    {
        "command": "raw show <id>",
        "description": "Show workflow details",
        "sdk_function": "get_workflow",
        "status": "full",
        "notes": "Get workflow details",
    },
    {
        "command": "raw show <tool>",
        "description": "Show tool details",
        "sdk_function": "get_tool",
        "status": "full",
        "notes": "Tool details in SDK",
    },
    {
        "command": "raw show <id> --logs",
        "description": "Show execution logs",
        "sdk_function": None,
        "status": "missing",
        "notes": "Log viewing not in SDK",
    },
    {
        "command": "raw publish <id>",
        "description": "Publish workflow",
        "sdk_function": "update_workflow",
        "status": "partial",
        "notes": "Can call publish_workflow directly but requires path",
    },
]


def check_parity() -> dict[str, Any]:
    """Check CLI-to-SDK parity.

    Returns dict with:
    - total_commands: int - Total number of CLI commands
    - full_parity: int - Commands with full SDK parity
    - partial_parity: int - Commands with partial SDK parity
    - missing: int - Commands with no SDK equivalent
    - details: list[dict] - Full command details
    """
    total = len(CLI_COMMANDS)
    full = sum(1 for cmd in CLI_COMMANDS if cmd["status"] == "full")
    partial = sum(1 for cmd in CLI_COMMANDS if cmd["status"] == "partial")
    missing = sum(1 for cmd in CLI_COMMANDS if cmd["status"] == "missing")

    return {
        "total_commands": total,
        "full_parity": full,
        "partial_parity": partial,
        "missing": missing,
        "details": CLI_COMMANDS,
    }


def print_parity_report() -> None:
    """Print a human-readable parity report."""
    parity = check_parity()

    print("\n=== CLI-to-SDK Parity Report ===\n")
    print(f"Total Commands: {parity['total_commands']}")
    print(f"✅ Full Parity: {parity['full_parity']} ({parity['full_parity']/parity['total_commands']*100:.0f}%)")
    print(f"⚠️  Partial Parity: {parity['partial_parity']} ({parity['partial_parity']/parity['total_commands']*100:.0f}%)")
    print(f"❌ Missing: {parity['missing']} ({parity['missing']/parity['total_commands']*100:.0f}%)")
    print("\n=== Commands by Status ===\n")

    for status in ["full", "partial", "missing"]:
        emoji = {"full": "✅", "partial": "⚠️", "missing": "❌"}[status]
        commands = [cmd for cmd in parity["details"] if cmd["status"] == status]

        if commands:
            print(f"\n{emoji} {status.upper()}\n")
            for cmd in commands:
                print(f"  {cmd['command']}")
                if cmd["sdk_function"]:
                    print(f"    SDK: {cmd['sdk_function']}")
                print(f"    Notes: {cmd['notes']}")


def get_missing_functions() -> list[dict[str, Any]]:
    """Get list of CLI commands missing SDK equivalents.

    Returns:
        List of command details for commands with no or partial SDK support
    """
    return [
        cmd
        for cmd in CLI_COMMANDS
        if cmd["status"] in ("missing", "partial")
    ]


def get_sdk_functions() -> list[str]:
    """Get list of SDK functions that correspond to CLI commands.

    Returns:
        List of SDK function names
    """
    functions = []
    for cmd in CLI_COMMANDS:
        if cmd["sdk_function"] and cmd["sdk_function"] not in functions:
            functions.append(cmd["sdk_function"])
    return sorted(functions)


def verify_sdk_function_exists(function_name: str) -> bool:
    """Verify that an SDK function exists.

    Args:
        function_name: Name of function to check (e.g., "create_workflow")

    Returns:
        True if function exists in SDK
    """
    try:
        # Import SDK module
        import raw.sdk as sdk

        # Check if function exists
        return hasattr(sdk, function_name)
    except (ImportError, AttributeError):
        return False


def verify_all_sdk_functions() -> dict[str, bool]:
    """Verify all documented SDK functions exist.

    Returns:
        Dict mapping function names to existence status
    """
    results = {}
    for function_name in get_sdk_functions():
        # Skip special cases like Container.workflow_runner
        if "." in function_name:
            continue
        results[function_name] = verify_sdk_function_exists(function_name)
    return results


if __name__ == "__main__":
    print_parity_report()

"""Show command implementation."""

from raw.discovery.display import (
    console,
    print_error,
    print_info,
    print_manifest_status,
    print_tool_details,
    print_workflow_details,
)
from raw.discovery.workflow import find_workflow, list_workflows, load_manifest
from raw.scaffold.init import find_tool, load_tool_config, load_workflow_config


def show_command(
    identifier: str | None,
    prompt_workflow_selection: callable,
    runs: bool = False,
) -> None:
    """Show details for a workflow or tool.

    Args:
        identifier: Workflow or tool ID
        prompt_workflow_selection: Function to prompt for selection
        runs: If True, show execution history instead of details
    """
    if not identifier:
        workflows = list_workflows()

        if not workflows:
            print_info("No workflows found.")
            raise SystemExit(0)

        action = "view runs for" if runs else "view"
        identifier = prompt_workflow_selection(action)
        if not identifier:
            raise SystemExit(0)

    # Try workflow first
    workflow_dir = find_workflow(identifier)
    if workflow_dir:
        if runs:
            # Show execution history (formerly raw status)
            manifest = load_manifest(workflow_dir)
            if not manifest:
                print_info(f"No execution history for: {workflow_dir.name}")
                print_info(f"Run the workflow first with: raw run {identifier}")
                return
            print_manifest_status(manifest)
        else:
            # Show workflow details
            workflow_config = load_workflow_config(workflow_dir)
            if workflow_config:
                print_workflow_details(workflow_config, workflow_dir)
            else:
                print_error(f"Could not load workflow config: {workflow_dir}")
                raise SystemExit(1)
        return

    # Try tool (only for details, not runs)
    if runs:
        print_error(f"Workflow not found: {identifier}")
        console.print("  Use 'raw list' to see available workflows")
        raise SystemExit(1)

    tool_dir = find_tool(identifier)
    if tool_dir:
        tool_config = load_tool_config(tool_dir)
        if tool_config:
            print_tool_details(tool_config, tool_dir)
        else:
            print_error(f"Could not load tool config: {tool_dir}")
            raise SystemExit(1)
        return

    print_error(f"Workflow not found: {identifier}")
    console.print("  Use 'raw list' to see available workflows")
    raise SystemExit(1)

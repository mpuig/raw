"""Show command implementation."""

import sys
from pathlib import Path

from raw.discovery.display import (
    console,
    print_error,
    print_info,
    print_manifest_status,
    print_tool_details,
    print_tools_list,
    print_workflow_details,
    print_workflow_list,
)
from raw.discovery.workflow import find_workflow, list_workflows, load_manifest
from raw.scaffold.init import find_tool, list_tools, load_tool_config, load_workflow_config
from raw.validation.validator import WorkflowValidator


def show_command(
    identifier: str | None,
    prompt_workflow_selection: callable,
    runs: bool = False,
    validate: bool = False,
) -> None:
    """Show details for a workflow or tool, or list all workflows/tools.

    Args:
        identifier: Workflow/tool ID, or "tools" to list tools (None lists workflows)
        prompt_workflow_selection: Function to prompt for selection
        runs: If True, show execution history instead of details
        validate: If True, validate workflow structure
    """
    # Special case: list all tools
    if identifier == "tools":
        tool_list = list_tools()
        print_tools_list(tool_list)
        return

    # Special case: no identifier → list all workflows
    if not identifier:
        workflows = list_workflows()
        print_workflow_list(workflows)
        return

    # Try workflow first
    workflow_dir = find_workflow(identifier)
    if workflow_dir:
        if validate:
            # Validate workflow structure
            validator = WorkflowValidator(project_root=Path.cwd())
            result = validator.validate(workflow_dir)
            result.print()
            sys.exit(0 if result.success else 1)
        elif runs:
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

    # Try tool (only for details, not runs/validate)
    if runs:
        print_error(f"Workflow not found: {identifier}")
        console.print("  Use 'raw show' to see available workflows")
        raise SystemExit(1)

    if validate:
        print_error(f"Workflow not found: {identifier}")
        console.print("  Use 'raw show' to see available workflows")
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

    print_error(f"Workflow or tool not found: {identifier}")
    console.print("  Use 'raw show' to see available workflows")
    console.print("  Use 'raw show tools' to see available tools")
    raise SystemExit(1)

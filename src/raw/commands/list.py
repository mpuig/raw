"""List command implementation."""

from raw.discovery.display import print_tools_list, print_workflow_list
from raw.discovery.workflow import list_workflows
from raw.scaffold.init import list_tools


def list_command(what: str) -> None:
    """List workflows or tools.

    This function contains the business logic for the list command.
    """
    if what == "tools":
        tool_list = list_tools()
        print_tools_list(tool_list)
    else:
        workflows = list_workflows()
        print_workflow_list(workflows)

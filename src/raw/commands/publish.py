"""Publish command implementation."""

from raw.discovery.display import print_error, print_info, print_workflow_published
from raw.discovery.workflow import find_workflow, publish_workflow


def publish_command(workflow_id: str | None, prompt_workflow_selection: callable) -> None:
    """Publish a workflow, making it immutable.

    This function contains the business logic for the publish command.
    """
    if not workflow_id:
        workflow_id = prompt_workflow_selection("publish")
        if not workflow_id:
            print_info("No workflows found. Create one with [cyan]raw create <name>[/]")
            raise SystemExit(0)

    workflow_dir = find_workflow(workflow_id)
    if not workflow_dir:
        print_error(f"Workflow not found: {workflow_id}")
        raise SystemExit(1)

    try:
        config = publish_workflow(workflow_dir)
        print_workflow_published(config.id, config.version)
    except ValueError as e:
        print_error(str(e))
        raise SystemExit(1) from None
    except Exception as e:
        print_error(f"Failed to publish workflow: {e}")
        raise SystemExit(1) from None

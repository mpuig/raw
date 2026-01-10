"""Validate command implementation - workflow structural validation."""

import sys
from pathlib import Path

from raw.discovery.workflow import find_workflow
from raw.validation.validator import WorkflowValidator


def validate_command(workflow_id: str | None, prompt_workflow_selection: callable) -> None:
    """Validate workflow structure and dependencies.

    This function contains the business logic for the validate command.
    The CLI layer (cli.py) handles argument parsing and delegates here.

    Args:
        workflow_id: Workflow identifier (prompts if None)
        prompt_workflow_selection: Function to prompt user for workflow selection

    Exit Codes:
        0: Validation passed
        1: Validation failed (errors found)
    """
    # Prompt for workflow if not provided
    if not workflow_id:
        selected = prompt_workflow_selection(action="validate")
        if not selected:
            print("No workflows found. Run 'raw create' first.")
            sys.exit(1)
        workflow_id = selected

    # Resolve workflow directory
    workflow_dir = find_workflow(workflow_id)
    if not workflow_dir:
        print(f"Error: Workflow not found: {workflow_id}")
        sys.exit(1)

    # Create validator and run validation
    validator = WorkflowValidator(project_root=Path.cwd())
    result = validator.validate(workflow_dir)

    # Print results
    result.print()

    # Exit with appropriate code
    sys.exit(0 if result.success else 1)

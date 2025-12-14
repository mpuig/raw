"""Create command implementation."""

from pathlib import Path

import click

from raw.discovery.display import (
    console,
    print_draft_created,
    print_error,
    print_info,
    print_run_result,
    print_tool_created,
    print_workflow_created,
    print_workflow_duplicated,
)
from raw.discovery.workflow import (
    create_draft_workflow,
    create_workflow_scaffold,
    duplicate_workflow,
    find_workflow,
)
from raw.engine import Container
from raw.scaffold.init import (
    create_tool,
    init_raw_project,
    is_raw_initialized,
    load_workflow_config,
)


def _ensure_initialized() -> bool:
    """Ensure RAW is initialized, auto-init if needed. Returns True if newly initialized."""
    if is_raw_initialized():
        return False
    init_raw_project()
    return True


def create_command(
    name: str,
    intent: str | None,
    from_workflow: str | None,
    tool: bool,
    description: str | None,
    scaffold: bool,
) -> None:
    """Create a new workflow or tool.

    This function contains the business logic for the create command.
    """
    if tool:
        newly_initialized = _ensure_initialized()
        if newly_initialized:
            print_info("Initialized RAW project")
            console.print()

        if not description:
            console.print()
            console.print("[bold]Create a new tool[/]")
            console.print(f"[dim]Name:[/] {name}")
            console.print()
            console.print(
                "[dim]Tip: Write for search - start with verb, include domain keywords[/]\n"
                "[dim]Example: Fetch stock prices and dividends from Yahoo Finance API[/]"
            )
            console.print()
            description = click.prompt("Description", type=str)

        assert description is not None
        if not description.strip():
            print_error("Description cannot be empty")
            raise SystemExit(1)

        try:
            tool_dir, config = create_tool(name, description.strip())
            print_tool_created(tool_dir, config.name, config.description)

            # Instruct agent to implement the tool using the skill
            console.print()
            console.print("[bold yellow]⚠ AGENT: Use the raw-tool-creator skill to implement this tool[/]")
            console.print()
            console.print(f"[dim]Tool directory:[/] {tool_dir}")
            console.print(f"[dim]Description:[/] {description.strip()}")
            console.print()
            console.print(
                "The skill will guide you to:\n"
                "  1. Implement tool.py with the actual logic\n"
                "  2. Update __init__.py with exports\n"
                "  3. Write tests in test.py\n"
                "  4. Run tests to verify"
            )
        except ValueError as e:
            print_error(str(e))
            raise SystemExit(1) from None
        except Exception as e:
            print_error(f"Failed to create tool: {e}")
            raise SystemExit(1) from None
        return

    newly_initialized = _ensure_initialized()
    if newly_initialized:
        print_info("Initialized RAW project")
        console.print()

    if from_workflow:
        workflow_dir = find_workflow(from_workflow)
        if not workflow_dir:
            print_error(f"Workflow not found: {from_workflow}")
            raise SystemExit(1)

        try:
            source_config = load_workflow_config(workflow_dir)
            if not source_config:
                print_error(f"Could not load workflow config: {workflow_dir}")
                raise SystemExit(1)

            new_dir, new_config = duplicate_workflow(workflow_dir, name)
            print_workflow_duplicated(source_config.id, new_config.id, new_dir)
        except ValueError as e:
            print_error(str(e))
            raise SystemExit(1) from None
        except Exception as e:
            print_error(f"Failed to duplicate workflow: {e}")
            raise SystemExit(1) from None
        return

    if scaffold:
        # Legacy v0.1.0 approach
        try:
            workflow_dir = create_workflow_scaffold(name)
            workflow_id = workflow_dir.name
            print_workflow_created(workflow_dir, workflow_id)

            try:
                console.print()
                print_info("Running dry-run to validate scaffold...")
                console.print()
                result = Container.workflow_runner().run_dry(workflow_dir)
                print_run_result(
                    workflow_id,
                    result.exit_code,
                    result.duration_seconds,
                    result.stdout,
                    result.stderr,
                )

                if result.exit_code != 0:
                    console.print()
                    console.print(
                        "[yellow]Scaffold created but dry-run failed. Check the generated code.[/]"
                    )
            except Exception as dry_err:
                console.print(f"[yellow]Could not run dry-run validation: {dry_err}[/]")
        except Exception as e:
            print_error(f"Failed to create workflow: {e}")
            raise SystemExit(1) from None
        return

    # v0.2.0 prompt-first approach
    if not intent:
        console.print()
        console.print("[bold]Create a new workflow[/]")
        console.print(f"[dim]Name:[/] {name}")
        console.print()
        console.print(
            "Describe what this workflow should do. Be specific about:\n"
            "  - Data sources (APIs, files, databases)\n"
            "  - Processing steps (calculate, transform, aggregate)\n"
            "  - Output format (PDF, JSON, email, Slack)\n"
        )
        console.print()
        console.print(
            "[dim]Example: Fetch TSLA stock data from Yahoo Finance, calculate RSI,[/]\n"
            "[dim]         generate PDF report with price charts[/]"
        )
        intent = click.prompt("Intent", type=str)

    assert intent is not None
    if not intent.strip():
        print_error("Intent cannot be empty")
        raise SystemExit(1)

    try:
        workflow_dir, workflow_config = create_draft_workflow(name, intent.strip())
        print_draft_created(workflow_dir, workflow_config.id, workflow_config.description.intent)
    except Exception as e:
        print_error(f"Failed to create workflow: {e}")
        raise SystemExit(1) from None

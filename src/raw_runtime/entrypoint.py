"""Workflow entrypoint for CLI execution.

Separates CLI concerns (argparse, console output, sys.exit) from
BaseWorkflow business logic, enabling better testability.
"""

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel

from raw_runtime.bus import LocalEventBus
from raw_runtime.connection import init_connection, set_connection
from raw_runtime.context import WorkflowContext, set_workflow_context
from raw_runtime.handlers import JournalEventHandler
from raw_runtime.protocols.logger import WorkflowLogger

if TYPE_CHECKING:
    from raw_runtime.base import BaseWorkflow

ParamsT = TypeVar("ParamsT", bound=BaseModel)


class _ConsoleLogger:
    """Adapter to make Rich Console conform to WorkflowLogger protocol."""

    def __init__(self, console: Console) -> None:
        self._console = console

    def print(self, message: str) -> None:
        self._console.print(message)


class WorkflowEntrypoint:
    """Handles CLI entry point concerns for workflows.

    Separates infrastructure (CLI parsing, console, exit codes) from
    workflow business logic, enabling:
    - Testing workflows without sys.exit
    - Running workflows in non-CLI contexts
    - Swapping console implementations
    """

    def __init__(
        self,
        console: Console | None = None,
        logger: WorkflowLogger | None = None,
    ) -> None:
        """Initialize entrypoint.

        Args:
            console: Rich console for output. Uses default if None.
            logger: Logger for workflow output. If None, wraps the console.
        """
        self.console = console or Console()
        self._logger = logger or _ConsoleLogger(self.console)

    def run(
        self,
        workflow_class: type["BaseWorkflow[ParamsT]"],
        args: list[str] | None = None,
    ) -> int:
        """Run a workflow from CLI arguments.

        Args:
            workflow_class: The workflow class to instantiate and run
            args: CLI arguments (uses sys.argv if None)

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        from raw_runtime.env import load_dotenv

        load_dotenv()

        params_class = workflow_class._get_params_class()
        parser = self._build_argparse(workflow_class, params_class)
        parsed = parser.parse_args(args)

        params_dict = {
            k.replace("-", "_"): v for k, v in vars(parsed).items() if v is not None
        }

        try:
            params = params_class(**params_dict)
        except Exception as e:
            self.console.print(f"[red]Error:[/] Invalid parameters: {e}")
            return 1

        return self._execute(workflow_class, params)

    def _build_argparse(
        self,
        workflow_class: type["BaseWorkflow[Any]"],
        params_class: type[BaseModel],
    ) -> argparse.ArgumentParser:
        """Build argparse from Pydantic model fields."""
        from typing import get_origin

        parser = argparse.ArgumentParser(
            description=params_class.__doc__
            or f"Run {workflow_class.__name__} workflow"
        )

        for field_name, field_info in params_class.model_fields.items():
            arg_name = f"--{field_name.replace('_', '-')}"
            kwargs: dict[str, Any] = {}

            if field_info.description:
                kwargs["help"] = field_info.description

            has_default = (
                field_info.default is not None
                or field_info.default_factory is not None
            )
            if not has_default and field_info.is_required():
                kwargs["required"] = True
            elif field_info.default is not None:
                kwargs["default"] = field_info.default

            field_type = field_info.annotation
            if field_type is bool:
                kwargs["action"] = "store_true"
            elif field_type is int:
                kwargs["type"] = int
            elif field_type is float:
                kwargs["type"] = float
            elif field_type is list or get_origin(field_type) is list:
                kwargs["nargs"] = "*"

            parser.add_argument(arg_name, **kwargs)

        return parser

    def _execute(
        self,
        workflow_class: type["BaseWorkflow[ParamsT]"],
        params: ParamsT,
    ) -> int:
        """Execute workflow with context management.

        Args:
            workflow_class: Workflow class to instantiate
            params: Validated parameters

        Returns:
            Exit code
        """
        workflow_name = workflow_class.__name__

        # Set up event bus and journal for crash recovery
        event_bus = LocalEventBus()
        journal_path = Path.cwd() / "events.jsonl"
        journal_handler = JournalEventHandler(journal_path)
        event_bus.subscribe(journal_handler)

        context = WorkflowContext(
            workflow_id=workflow_name,
            short_name=workflow_name,
            parameters=params.model_dump(),
            workflow_dir=Path.cwd(),
            event_bus=event_bus,
        )

        self.console.print()
        self.console.print(Panel(f"[bold]{workflow_name}[/]", border_style="blue"))
        self.console.print()

        connection = init_connection(context.run_id, workflow_name)

        exit_code = 1
        workflow = None
        try:
            with context:
                set_workflow_context(context)
                workflow = workflow_class(params, context, logger=self._logger)

                workflow.log(f"Starting workflow: {workflow_name}")
                workflow.log(f"Parameters: {params.model_dump()}")

                exit_code = workflow.run()

                if exit_code == 0:
                    workflow.log("Workflow completed successfully")
                    context.finalize(status="success")
                    self.console.print()
                    self.console.print(
                        Panel(
                            "[bold green]Workflow completed successfully[/]",
                            border_style="green",
                        )
                    )
                else:
                    workflow.log(f"Workflow failed with exit code: {exit_code}")
                    context.finalize(status="failed", error=f"Exit code: {exit_code}")

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Workflow cancelled[/]")
            if workflow:
                workflow._log_to_file("Workflow cancelled by user")
            context.finalize(status="cancelled")
            exit_code = 130
        except Exception as e:
            self.console.print(f"\n[red]Error:[/] {e}")
            if workflow:
                workflow._log_to_file(f"Workflow failed with error: {e}")
            context.finalize(status="failed", error=str(e))
            exit_code = 1
        finally:
            # Flush and close journal
            journal_handler.flush()
            journal_handler.close()

            set_workflow_context(None)
            if connection.is_connected:
                connection.disconnect("success" if exit_code == 0 else "failed")
            set_connection(None)

        return exit_code


# Module-level instance for convenience
_default_entrypoint: WorkflowEntrypoint | None = None


def get_entrypoint() -> WorkflowEntrypoint:
    """Get the default workflow entrypoint."""
    global _default_entrypoint
    if _default_entrypoint is None:
        _default_entrypoint = WorkflowEntrypoint()
    return _default_entrypoint


def set_entrypoint(entrypoint: WorkflowEntrypoint | None) -> None:
    """Set the default entrypoint (useful for testing)."""
    global _default_entrypoint
    _default_entrypoint = entrypoint


def run_workflow(
    workflow_class: type["BaseWorkflow[ParamsT]"],
    args: list[str] | None = None,
) -> int:
    """Run a workflow using the default entrypoint.

    Args:
        workflow_class: Workflow class to run
        args: CLI arguments (uses sys.argv if None)

    Returns:
        Exit code
    """
    return get_entrypoint().run(workflow_class, args)


def main_exit(
    workflow_class: type["BaseWorkflow[ParamsT]"],
    args: list[str] | None = None,
) -> None:
    """Run a workflow and exit with its exit code.

    This is the function BaseWorkflow.main() delegates to.
    """
    sys.exit(run_workflow(workflow_class, args))

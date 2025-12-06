"""Base workflow class for RAW workflows.

BaseWorkflow provides a clean, minimal interface for writing workflows.
It handles all boilerplate: argparse generation, context setup, error handling.

Usage:
    from pydantic import BaseModel, Field
    from raw_runtime import BaseWorkflow, step

    class MyParams(BaseModel):
        input_file: str = Field(..., description="Input file path")
        output_dir: str = Field(default="results", description="Output directory")

    class MyWorkflow(BaseWorkflow[MyParams]):
        @step("process")
        def process(self) -> dict:
            data = Path(self.params.input_file).read_text()
            return {"lines": len(data.splitlines())}

        def run(self) -> int:
            result = self.process()
            self.save("output.json", result)
            return 0

    if __name__ == "__main__":
        MyWorkflow.main()
"""

import argparse
import json
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar, get_args, get_origin

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel

from raw_runtime.connection import init_connection, set_connection
from raw_runtime.context import WorkflowContext, set_workflow_context

ParamsT = TypeVar("ParamsT", bound=BaseModel)

console = Console()


class BaseWorkflow(ABC, Generic[ParamsT]):
    """Base class for all RAW workflows.

    Subclass this and implement the `run()` method. Use `@step` decorator
    for individual workflow steps to get automatic logging and timing.

    Attributes:
        params: The validated workflow parameters (Pydantic model)
        context: The workflow execution context for tracking
        results_dir: Path to the results directory
    """

    def __init__(self, params: ParamsT, context: WorkflowContext | None = None) -> None:
        """Initialize workflow with parameters."""
        self.params = params
        self.context = context
        self._results_dir: Path | None = None
        self._log_file: Path | None = None

    @property
    def results_dir(self) -> Path:
        """Get the results directory for this execution.

        When run via RAW CLI, CWD is set to the run directory and results go to results/.
        When run standalone, results go to results/ in the current directory.
        """
        if self._results_dir is None:
            self._results_dir = Path("results")
        self._results_dir.mkdir(parents=True, exist_ok=True)
        return self._results_dir

    @property
    def run_dir(self) -> Path:
        """Alias for results_dir for backwards compatibility."""
        return self.results_dir

    @property
    def log_file(self) -> Path:
        """Get the log file path for this run.

        Log file is saved as output.log in the current working directory.
        When run via RAW CLI, this is the run directory.
        """
        if self._log_file is None:
            self._log_file = Path("output.log")
        return self._log_file

    @abstractmethod
    def run(self) -> int:
        """Execute the workflow."""
        ...

    def save(self, filename: str, data: Any) -> Path:
        """Save data to results directory."""
        filepath = self.results_dir / filename

        if isinstance(data, dict | list):
            filepath.write_text(json.dumps(data, indent=2, default=str))
        elif isinstance(data, bytes):
            filepath.write_bytes(data)
        elif isinstance(data, BaseModel):
            filepath.write_text(data.model_dump_json(indent=2))
        else:
            filepath.write_text(str(data))

        console.print(f"  [green]✓[/] Saved {filename}")

        # Log to file (without console output to avoid duplication)
        self._log_to_file(f"Saved file: {filepath}")

        if self.context:
            self.context.add_artifact("output", filepath)

        return filepath

    def _log_to_file(self, message: str) -> None:
        """Write a message to the log file only (no console output)."""
        from datetime import datetime, timezone

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        with open(self.log_file, "a") as f:
            f.write(log_entry)

    def log(self, message: str) -> None:
        """Log a message to the console and log file.

        Messages are printed to the console and appended to the log file
        at logs/YYYYMMDDHHMMSS.log.
        """
        from datetime import datetime, timezone

        console.print(f"  {message}")

        # Also write to log file with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        with open(self.log_file, "a") as f:
            f.write(log_entry)

    @classmethod
    def _get_params_class(cls) -> type[BaseModel]:
        """Extract the Pydantic params class from generic type."""
        for base in cls.__orig_bases__:  # type: ignore[attr-defined]
            origin = get_origin(base)
            if origin is BaseWorkflow:
                args = get_args(base)
                if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
                    return args[0]
        raise TypeError(
            f"{cls.__name__} must specify a Pydantic model as type parameter: "
            f"class {cls.__name__}(BaseWorkflow[MyParams])"
        )

    @classmethod
    def _build_argparse(cls, params_class: type[BaseModel]) -> argparse.ArgumentParser:
        """Build argparse from Pydantic model fields."""
        parser = argparse.ArgumentParser(
            description=params_class.__doc__ or f"Run {cls.__name__} workflow"
        )

        for field_name, field_info in params_class.model_fields.items():
            arg_name = f"--{field_name.replace('_', '-')}"
            kwargs: dict[str, Any] = {}

            if field_info.description:
                kwargs["help"] = field_info.description

            has_default = field_info.default is not None or field_info.default_factory is not None
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

    @classmethod
    def main(cls, args: list[str] | None = None) -> None:
        """Main entry point for the workflow.

        Handles argument parsing, context setup, server connection, execution,
        and error handling. If RAW_SERVER_URL is set, connects to the server
        for event-driven operation (approvals, webhooks).
        """
        from raw_runtime.env import load_dotenv

        load_dotenv()

        params_class = cls._get_params_class()

        parser = cls._build_argparse(params_class)
        parsed = parser.parse_args(args)

        params_dict = {k.replace("-", "_"): v for k, v in vars(parsed).items() if v is not None}

        try:
            params = params_class(**params_dict)
        except Exception as e:
            console.print(f"[red]Error:[/] Invalid parameters: {e}")
            sys.exit(1)

        workflow_name = cls.__name__
        context = WorkflowContext(
            workflow_id=workflow_name,
            short_name=workflow_name,
            parameters=params.model_dump(),
            workflow_dir=Path.cwd(),
        )

        console.print()
        console.print(Panel(f"[bold]{workflow_name}[/]", border_style="blue"))
        console.print()

        connection = init_connection(context.run_id, workflow_name)

        exit_code = 1
        try:
            with context:
                set_workflow_context(context)
                workflow = cls(params, context)  # type: ignore[arg-type]

                workflow.log(f"Starting workflow: {workflow_name}")
                workflow.log(f"Parameters: {params.model_dump()}")

                exit_code = workflow.run()

                if exit_code == 0:
                    workflow.log("Workflow completed successfully")
                    context.finalize(status="success")
                    console.print()
                    console.print(
                        Panel(
                            "[bold green]Workflow completed successfully[/]", border_style="green"
                        )
                    )
                else:
                    workflow.log(f"Workflow failed with exit code: {exit_code}")
                    context.finalize(status="failed", error=f"Exit code: {exit_code}")

        except KeyboardInterrupt:
            console.print("\n[yellow]Workflow cancelled[/]")
            if "workflow" in locals():
                workflow._log_to_file("Workflow cancelled by user")
            context.finalize(status="cancelled")
            exit_code = 130
        except Exception as e:
            console.print(f"\n[red]Error:[/] {e}")
            if "workflow" in locals():
                workflow._log_to_file(f"Workflow failed with error: {e}")
            context.finalize(status="failed", error=str(e))
            exit_code = 1
        finally:
            set_workflow_context(None)
            if connection.is_connected:
                connection.disconnect("success" if exit_code == 0 else "failed")
            set_connection(None)

        sys.exit(exit_code)


# Convenience re-export of step decorator
from raw_runtime.decorators import cache_step as cache  # noqa: E402
from raw_runtime.decorators import raw_step as step  # noqa: E402
from raw_runtime.decorators import retry  # noqa: E402

__all__ = ["BaseWorkflow", "step", "cache", "retry"]

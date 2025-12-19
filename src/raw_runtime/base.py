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

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar, get_args, get_origin

from pydantic import BaseModel

from raw_runtime.context import WorkflowContext
from raw_runtime.protocols.logger import WorkflowLogger, get_logger

if TYPE_CHECKING:
    from raw_runtime.tools.base import Tool
    from raw_runtime.triggers import TriggerEvent

ParamsT = TypeVar("ParamsT", bound=BaseModel)


class BaseWorkflow(ABC, Generic[ParamsT]):
    """Base class for all RAW workflows.

    Subclass this and implement the `run()` method. Use `@step` decorator
    for individual workflow steps to get automatic logging and timing.

    Attributes:
        params: The validated workflow parameters (Pydantic model)
        context: The workflow execution context for tracking
        results_dir: Path to the results directory
    """

    def __init__(
        self,
        params: ParamsT,
        context: WorkflowContext | None = None,
        logger: WorkflowLogger | None = None,
        trigger_event: "TriggerEvent | None" = None,
    ) -> None:
        """Initialize workflow with parameters.

        Args:
            params: Validated workflow parameters
            context: Optional workflow execution context
            logger: Optional logger for output (defaults to Rich console)
            trigger_event: Optional event that triggered this workflow
        """
        self.params = params
        self.context = context
        self._logger = logger or get_logger()
        self._results_dir: Path | None = None
        self._log_file: Path | None = None
        self._trigger_event = trigger_event

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

    @property
    def trigger_event(self) -> "TriggerEvent | None":
        """Get the event that triggered this workflow, if any.

        Returns None for manually invoked workflows.
        For event-triggered workflows (decorated with @on_event),
        contains the TriggerEvent with source and data.
        """
        return self._trigger_event

    def tool(self, name: str) -> "Tool":
        """Get a tool by name.

        Tools provide access to reusable actions (email, SMS, HTTP, etc.)
        with a uniform async interface.

        Args:
            name: Tool name (e.g., "email", "sms", "http", "converse")

        Returns:
            The tool instance

        Raises:
            KeyError: If the tool is not registered

        Usage:
            # Simple request/response
            result = await self.tool("http").call(url="https://api.example.com")

            # Streaming/long-running
            async for event in self.tool("converse").run(bot="support"):
                if event.type == "message":
                    self.log(event.data["text"])
        """
        from raw_runtime.tools.registry import get_tool

        return get_tool(name)

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

        self._logger.print(f"  [green]✓[/] Saved {filename}")

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
        """Log a message to the output and log file.

        Messages are printed to the logger (console by default) and appended
        to the log file at output.log.
        """
        from datetime import datetime, timezone

        self._logger.print(f"  {message}")

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
    def main(cls, args: list[str] | None = None) -> None:
        """Main entry point for the workflow.

        Delegates to WorkflowEntrypoint which handles argument parsing,
        context setup, server connection, execution, and error handling.
        """
        from raw_runtime.entrypoint import main_exit

        main_exit(cls, args)


# Convenience re-export of step decorator
from raw_runtime.decorators import cache_step as cache  # noqa: E402
from raw_runtime.decorators import raw_step as step  # noqa: E402
from raw_runtime.decorators import retry  # noqa: E402

__all__ = ["BaseWorkflow", "step", "cache", "retry"]

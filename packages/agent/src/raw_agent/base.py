"""Base workflow class for RAW agent workflows.

BaseWorkflow provides a clean, minimal interface for writing agent workflows.
It handles step tracking, context management, and event emission.

Usage:
    from pydantic import BaseModel, Field
    from raw_agent import BaseWorkflow, step

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
            return 0
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, get_args, get_origin

from pydantic import BaseModel

from raw_agent.context import WorkflowContext

ParamsT = TypeVar("ParamsT", bound=BaseModel)


class BaseWorkflow(ABC, Generic[ParamsT]):
    """Base class for all RAW agent workflows.

    Subclass this and implement the `run()` method. Use `@step` decorator
    for individual workflow steps to get automatic logging and event emission.

    Attributes:
        params: The validated workflow parameters (Pydantic model)
        context: The workflow execution context for tracking
    """

    def __init__(
        self,
        params: ParamsT,
        context: WorkflowContext | None = None,
    ) -> None:
        """Initialize workflow with parameters.

        Args:
            params: Validated workflow parameters
            context: Optional workflow execution context
        """
        self.params = params
        self.context = context

    @abstractmethod
    def run(self) -> int:
        """Execute the workflow.

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        ...

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

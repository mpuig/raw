"""The @agent decorator for LLM-powered workflow steps."""

import functools
import inspect
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from raw_ai.config import get_model
from raw_ai.tools import to_ai_tool

T = TypeVar("T", bound=BaseModel)


def agent(
    result_type: type[T] | None = None,
    model: str | None = None,
    tools: list[Callable] | None = None,
    retries: int = 3,
    temperature: float | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that turns a method into an LLM-powered agent step.

    The decorated method's docstring becomes the system prompt.
    Method arguments become the user message.
    The result_type defines the structured output schema.

    Args:
        result_type: Pydantic model for structured output (required)
        model: Model name (e.g., "gpt-4o", "claude-3-5-sonnet-latest")
        tools: List of functions the agent can call
        retries: Number of retries on validation failure
        temperature: Sampling temperature (0.0-2.0)

    Returns:
        Decorated method that calls the LLM

    Example:
        class Sentiment(BaseModel):
            score: float
            label: str
            reasoning: str

        class MyWorkflow(BaseWorkflow):
            @agent(result_type=Sentiment)
            def analyze(self, text: str) -> Sentiment:
                '''You are a sentiment analyst. Analyze the text and return structured sentiment.'''
                ...

            def run(self) -> int:
                result = self.analyze("I love this!")
                print(result.label)  # "positive"
                return 0
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Extract system prompt from docstring
        system_prompt = inspect.getdoc(func) or "You are a helpful assistant."

        # Get function signature for building user message
        sig = inspect.signature(func)
        param_names = [p for p in sig.parameters if p != "self"]

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> T:
            from pydantic_ai import Agent

            # Build user message from arguments
            bound = sig.bind(self, *args, **kwargs)
            bound.apply_defaults()

            user_parts = []
            for name in param_names:
                value = bound.arguments.get(name)
                if value is not None:
                    if isinstance(value, str):
                        user_parts.append(value)
                    else:
                        user_parts.append(f"{name}: {value}")

            user_message = "\n\n".join(user_parts) if user_parts else "Please proceed."

            # Get model string
            model_str = get_model(model)

            # Create agent
            agent_instance = Agent(
                model_str,
                result_type=result_type,
                system_prompt=system_prompt,
                retries=retries,
            )

            # Add tools if provided
            if tools:
                for tool_func in tools:
                    tool_def = to_ai_tool(tool_func)

                    @agent_instance.tool
                    def _tool_wrapper(**kw):
                        return tool_def["function"](**kw)

                    _tool_wrapper.__name__ = tool_def["name"]
                    _tool_wrapper.__doc__ = tool_def["description"]

            # Run the agent
            result = agent_instance.run_sync(user_message)

            # Emit step event if we have workflow context
            if hasattr(self, "_context") and self._context:
                from datetime import datetime

                from raw_runtime.models import StepResult, StepStatus

                now = datetime.now()
                step_result = StepResult(
                    name=func.__name__,
                    status=StepStatus.SUCCESS,
                    started_at=now,
                    ended_at=now,
                    result=result.data.model_dump() if hasattr(result.data, "model_dump") else result.data,
                )
                self._context.add_step_result(step_result)

            return result.data

        # Mark as agent step for introspection
        wrapper._is_agent = True
        wrapper._result_type = result_type
        wrapper._model = model

        return wrapper

    return decorator


def agent_step(
    name: str | None = None,
    result_type: type[T] | None = None,
    model: str | None = None,
    tools: list[Callable] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Alias for @agent that also adds @step tracking.

    Combines @agent with @step for full workflow integration.

    Args:
        name: Step name for tracking
        result_type: Pydantic model for structured output
        model: Model name
        tools: List of callable tools

    Example:
        @agent_step("analyze", result_type=Sentiment)
        def analyze_text(self, text: str) -> Sentiment:
            '''Analyze sentiment.'''
            ...
    """
    from raw_runtime.decorators import step

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Apply @agent first
        agent_wrapped = agent(
            result_type=result_type,
            model=model,
            tools=tools,
        )(func)

        # Then apply @step
        step_name = name or func.__name__
        return step(step_name)(agent_wrapped)

    return decorator

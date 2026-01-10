"""Agent-in-loop decorator for LLM-powered workflow steps.

This decorator enables selective agent reasoning within workflows. Steps can invoke
Claude for decision-making while maintaining deterministic execution elsewhere.
"""

import functools
import hashlib
import inspect
import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Literal, ParamSpec, TypeVar, get_args, get_origin, get_type_hints

from pydantic import BaseModel

from raw_runtime.context import get_workflow_context
from raw_runtime.events import StepCompletedEvent, StepStartedEvent

P = ParamSpec("P")
T = TypeVar("T")


class AgenticStepError(Exception):
    """Base error for agentic step failures."""

    pass


class CostLimitExceededError(AgenticStepError):
    """Raised when cost limit is exceeded."""

    def __init__(self, actual_cost: float, limit: float) -> None:
        self.actual_cost = actual_cost
        self.limit = limit
        super().__init__(f"Cost ${actual_cost:.4f} exceeds limit ${limit:.4f}")


class ResponseParsingError(AgenticStepError):
    """Raised when response cannot be parsed to expected type."""

    def __init__(self, response: str, expected_type: str, error: str) -> None:
        self.response = response
        self.expected_type = expected_type
        self.error = error
        super().__init__(f"Failed to parse response to {expected_type}: {error}")


# In-memory cache for prompt responses (will be enhanced with file persistence)
_cache: dict[str, Any] = {}


def _generate_cache_key(prompt: str, model: str) -> str:
    """Generate cache key from prompt and model."""
    data = f"{prompt}:{model}"
    return hashlib.sha256(data.encode()).hexdigest()


def _format_prompt(
    template: str, func: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]
) -> str:
    """Format prompt template with function arguments.

    Creates a context object from function arguments for template substitution.
    """
    sig = inspect.signature(func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()

    # Create context object from arguments (skip self)
    context_data = {}
    for param_name, value in bound_args.arguments.items():
        if param_name == "self":
            continue
        context_data[param_name] = value

    # Create a simple namespace object for dot notation
    class Context:
        def __init__(self, data: dict[str, Any]) -> None:
            for key, value in data.items():
                setattr(self, key, value)

    context = Context(context_data)

    # Format using string.format with context object
    try:
        return template.format(context=context)
    except (KeyError, AttributeError) as e:
        raise ValueError(f"Failed to format prompt template: {e}") from e


def _parse_response(response_text: str, return_type: Any) -> Any:
    """Parse LLM response to expected return type."""
    response_text = response_text.strip()

    # Get the origin type for generics (e.g., list from list[str])
    origin = get_origin(return_type)

    # Handle None/NoneType
    if return_type is None or return_type is type(None):
        return None

    # Handle str
    if return_type is str:
        return response_text

    # Handle int
    if return_type is int:
        try:
            return int(response_text)
        except ValueError as e:
            raise ResponseParsingError(response_text, "int", str(e)) from e

    # Handle bool
    if return_type is bool:
        lower = response_text.lower()
        if lower in ("true", "yes", "1"):
            return True
        elif lower in ("false", "no", "0"):
            return False
        raise ResponseParsingError(response_text, "bool", f"Invalid boolean: {response_text}")

    # Handle Literal types
    if get_origin(return_type) is Literal:
        allowed_values = get_args(return_type)
        if response_text in allowed_values:
            return response_text
        raise ResponseParsingError(
            response_text,
            f"Literal{allowed_values}",
            f"Response '{response_text}' not in allowed values",
        )

    # Handle Pydantic models
    if isinstance(return_type, type) and issubclass(return_type, BaseModel):
        try:
            # Try to parse as JSON
            data = json.loads(response_text)
            return return_type.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            raise ResponseParsingError(response_text, return_type.__name__, str(e)) from e

    # Handle list
    if origin is list or return_type is list:
        try:
            data = json.loads(response_text)
            if not isinstance(data, list):
                raise ValueError("Response is not a list")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            raise ResponseParsingError(response_text, "list", str(e)) from e

    # Handle dict
    if origin is dict or return_type is dict:
        try:
            data = json.loads(response_text)
            if not isinstance(data, dict):
                raise ValueError("Response is not a dict")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            raise ResponseParsingError(response_text, "dict", str(e)) from e

    # Default: return as string
    return response_text


def _call_anthropic(
    prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> tuple[str, float]:
    """Call Anthropic API and return response text and cost.

    Returns:
        Tuple of (response_text, cost_in_usd)
    """
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise AgenticStepError(
            "anthropic library not installed. Install with: pip install anthropic"
        ) from e

    client = Anthropic()  # Uses ANTHROPIC_API_KEY from environment

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
    except Exception as e:
        raise AgenticStepError(f"Anthropic API call failed: {e}") from e

    # Extract response text
    response_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            response_text += block.text

    # Calculate cost (simplified - using approximate pricing)
    # Claude 3.5 Sonnet: $3/MTok input, $15/MTok output
    # Claude 3.5 Haiku: $0.25/MTok input, $1.25/MTok output
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    if "haiku" in model.lower():
        cost = (input_tokens * 0.25 + output_tokens * 1.25) / 1_000_000
    elif "sonnet" in model.lower():
        cost = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000
    else:
        # Default to Sonnet pricing
        cost = (input_tokens * 3.0 + output_tokens * 15.0) / 1_000_000

    return response_text, cost


def agentic(
    prompt: str,
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 4096,
    temperature: float = 1.0,
    cost_limit: float | None = None,
    cache: bool = True,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Make a workflow step invoke Claude for reasoning.

    This decorator replaces the function body with an LLM call. The function's
    return type hint is used to parse the LLM response into the correct type.

    Args:
        prompt: Template with {context.field} placeholders for function arguments
        model: Claude model ID (default: claude-3-5-sonnet-20241022)
        max_tokens: Maximum response tokens (default: 4096)
        temperature: Sampling temperature 0-1 (default: 1.0)
        cost_limit: Maximum cost in USD, raises CostLimitExceededError if exceeded
        cache: Enable prompt-based caching (default: True)

    Usage:
        @step("classify")
        @agentic(
            prompt="Classify urgency: {context.ticket}\\nReturn: critical/high/medium/low",
            model="claude-3-5-haiku-20241022",
            max_tokens=10,
            cost_limit=0.01
        )
        def classify_ticket(self, ticket: str) -> Literal["critical", "high", "medium", "low"]:
            pass  # Implementation injected by decorator
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Extract return type at decoration time
        hints = get_type_hints(func)
        return_type = hints.get("return", str)

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            context = get_workflow_context()
            started_at = datetime.now(timezone.utc)
            step_name = func.__name__

            # Format prompt with function arguments
            formatted_prompt = _format_prompt(prompt, func, args, kwargs)

            # Check cache if enabled
            if cache:
                cache_key = _generate_cache_key(formatted_prompt, model)
                if cache_key in _cache:
                    cached_result = _cache[cache_key]

                    # Emit events for cached result
                    if context:
                        context.emit(
                            StepStartedEvent(
                                workflow_id=context.workflow_id,
                                run_id=context.run_id,
                                step_name=step_name,
                                input_types=["agentic"],
                                output_type=str(return_type),
                            )
                        )
                        context.emit(
                            StepCompletedEvent(
                                workflow_id=context.workflow_id,
                                run_id=context.run_id,
                                step_name=step_name,
                                duration_seconds=0.0,
                                result_type=type(cached_result).__name__,
                                result_summary="(cached)",
                            )
                        )

                    return cached_result  # type: ignore[return-value]

            # Emit step started event
            if context:
                context.emit(
                    StepStartedEvent(
                        workflow_id=context.workflow_id,
                        run_id=context.run_id,
                        step_name=step_name,
                        input_types=["agentic"],
                        output_type=str(return_type),
                    )
                )

            # Call Anthropic API
            response_text, cost = _call_anthropic(
                formatted_prompt,
                model,
                max_tokens,
                temperature,
            )

            # Check cost limit
            if cost_limit is not None and cost > cost_limit:
                raise CostLimitExceededError(cost, cost_limit)

            # Parse response to expected type
            try:
                result = _parse_response(response_text, return_type)
            except ResponseParsingError:
                raise

            # Cache result if enabled
            if cache:
                cache_key = _generate_cache_key(formatted_prompt, model)
                _cache[cache_key] = result

            # Emit step completed event
            ended_at = datetime.now(timezone.utc)
            duration = (ended_at - started_at).total_seconds()

            if context:
                context.emit(
                    StepCompletedEvent(
                        workflow_id=context.workflow_id,
                        run_id=context.run_id,
                        step_name=step_name,
                        duration_seconds=duration,
                        result_type=type(result).__name__,
                        result_summary=f"cost: ${cost:.4f}",
                    )
                )

            return result  # type: ignore[return-value]

        return wrapper

    return decorator

"""Decorators for RAW workflow steps.

These decorators provide:
- @raw_step: Track step execution with timing and results
- @retry: Add retry logic with configurable backoff (powered by tenacity)
- @cache_step: Cache expensive computation results

All decorators emit events via the EventBus for decoupled handling.
Console output is handled by ConsoleEventHandler when configured.
"""

import functools
import hashlib
import inspect
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ParamSpec, TypeVar, get_type_hints

from tenacity import (
    RetryCallState,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
)
from tenacity import (
    retry as tenacity_retry,
)

from raw_runtime.context import get_workflow_context
from raw_runtime.events import (
    CacheHitEvent,
    StepCompletedEvent,
    StepFailedEvent,
    StepRetryEvent,
    StepSkippedEvent,
    StepStartedEvent,
)
from raw_runtime.models import StepResult, StepStatus

P = ParamSpec("P")
T = TypeVar("T")


def _get_type_name(type_hint: Any) -> str:
    """Get a readable name for a type hint."""
    if type_hint is None or type_hint is type(None):
        return "None"
    if hasattr(type_hint, "__name__"):
        return type_hint.__name__  # type: ignore[no-any-return]
    return str(type_hint).replace("typing.", "")


def _get_step_signature(func: Callable[..., Any]) -> tuple[list[str], str]:
    """Extract input and output type names from function signature.

    Returns:
        Tuple of (input_type_names, output_type_name)
    """
    input_types: list[str] = []
    output_type = "Any"

    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}

    sig = inspect.signature(func)
    for param_name, _param in sig.parameters.items():
        if param_name == "self":
            continue
        if param_name in hints:
            input_types.append(_get_type_name(hints[param_name]))
        else:
            input_types.append("Any")

    if "return" in hints:
        output_type = _get_type_name(hints["return"])

    return input_types, output_type


def raw_step(name: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to track step execution with typed contracts.

    Records timing, success/failure, and results into the WorkflowContext.
    Emits events for real-time monitoring via EventBus.

    Args:
        name: Step name for tracking and display

    Usage:
        @raw_step("fetch_data")
        def fetch_data(self, query: SearchQuery) -> FetchResult:
            return FetchResult(data_points=100)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Extract type signature once at decoration time
        input_types, output_type = _get_step_signature(func)

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            context = get_workflow_context()
            started_at = datetime.now(timezone.utc)

            if context:
                context.emit(
                    StepStartedEvent(
                        workflow_id=context.workflow_id,
                        run_id=context.run_id,
                        step_name=name,
                        input_types=input_types,
                        output_type=output_type,
                    )
                )

            try:
                result = func(*args, **kwargs)

                ended_at = datetime.now(timezone.utc)
                duration = (ended_at - started_at).total_seconds()
                result_type = type(result).__name__

                if context:
                    step_result = StepResult(
                        name=name,
                        status=StepStatus.SUCCESS,
                        started_at=started_at,
                        ended_at=ended_at,
                        duration_seconds=duration,
                        result=_serialize_result(result),
                    )
                    context.add_step_result(step_result)
                    context.emit(
                        StepCompletedEvent(
                            workflow_id=context.workflow_id,
                            run_id=context.run_id,
                            step_name=name,
                            duration_seconds=duration,
                            result_type=result_type,
                        )
                    )

                return result

            except Exception as e:
                ended_at = datetime.now(timezone.utc)
                duration = (ended_at - started_at).total_seconds()

                if context:
                    step_result = StepResult(
                        name=name,
                        status=StepStatus.FAILED,
                        started_at=started_at,
                        ended_at=ended_at,
                        duration_seconds=duration,
                        error=str(e),
                    )
                    context.add_step_result(step_result)
                    context.emit(
                        StepFailedEvent(
                            workflow_id=context.workflow_id,
                            run_id=context.run_id,
                            step_name=name,
                            error=str(e),
                            duration_seconds=duration,
                        )
                    )

                raise

        return wrapper

    return decorator


def _create_retry_callback(step_name: str, max_retries: int) -> Callable[[RetryCallState], None]:
    """Create a retry callback that emits events."""

    def callback(retry_state: RetryCallState) -> None:
        context = get_workflow_context()
        attempt = retry_state.attempt_number
        outcome = retry_state.outcome
        if outcome and outcome.failed and context:
            exc = outcome.exception()
            next_wait = retry_state.next_action.sleep if retry_state.next_action else 0
            context.emit(
                StepRetryEvent(
                    workflow_id=context.workflow_id,
                    run_id=context.run_id,
                    step_name=step_name,
                    attempt=attempt,
                    max_attempts=max_retries + 1,
                    error=str(exc),
                    delay_seconds=float(next_wait),
                )
            )

    return callback


def retry(
    retries: int = 3,
    backoff: str = "exponential",
    retry_on: tuple[type[Exception], ...] = (Exception,),
    base_delay: float = 1.0,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to add retry logic with backoff (powered by tenacity).

    Args:
        retries: Maximum number of retry attempts
        backoff: Backoff strategy ("exponential" or "fixed")
        retry_on: Exception types to retry on
        base_delay: Base delay in seconds

    Usage:
        @raw_step("fetch_data")
        @retry(retries=3, backoff="exponential")
        def fetch_data(self):
            return api.fetch()
    """
    if backoff == "exponential":
        wait_strategy = wait_exponential(multiplier=base_delay, min=base_delay, max=60)
    else:
        wait_strategy = wait_fixed(base_delay)

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        step_name = func.__name__
        retry_callback = _create_retry_callback(step_name, retries)

        tenacity_wrapper = tenacity_retry(
            stop=stop_after_attempt(retries + 1),
            wait=wait_strategy,
            retry=retry_if_exception_type(retry_on),
            before_sleep=retry_callback,
            reraise=True,
        )(func)

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return tenacity_wrapper(*args, **kwargs)  # type: ignore[no-any-return]

        wrapper._retry_config = {"retries": retries, "backoff": backoff}  # type: ignore[attr-defined]
        return wrapper

    return decorator


def cache_step(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to cache step results.

    Caches based on function name and arguments. Cache is stored
    in .raw/cache/ directory as JSON files.

    Usage:
        @raw_step("calculate_indicators")
        @cache_step
        def calculate_indicators(self, data):
            return expensive_calculation(data)
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        context = get_workflow_context()
        step_name = func.__name__

        cache_key = _generate_cache_key(step_name, args, kwargs)

        if context and context.workflow_dir:
            cache_dir = _find_project_cache_dir(context.workflow_dir)
            cache_file = cache_dir / f"{cache_key}.json" if cache_dir else None

            if cache_file and cache_file.exists():
                try:
                    cached_data = json.loads(cache_file.read_text())

                    context.emit(
                        CacheHitEvent(
                            workflow_id=context.workflow_id,
                            run_id=context.run_id,
                            step_name=step_name,
                            cache_key=cache_key,
                        )
                    )

                    now = datetime.now(timezone.utc)
                    step_result = StepResult(
                        name=step_name,
                        status=StepStatus.SUCCESS,
                        started_at=now,
                        ended_at=now,
                        duration_seconds=0.0,
                        cached=True,
                        result=cached_data.get("result"),
                    )
                    context.add_step_result(step_result)

                    return cached_data.get("result")  # type: ignore[no-any-return]
                except (json.JSONDecodeError, KeyError):
                    pass

        result = func(*args, **kwargs)

        if context and context.workflow_dir:
            cache_dir = _find_project_cache_dir(context.workflow_dir)
            if cache_dir:
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_file = cache_dir / f"{cache_key}.json"
            else:
                cache_file = None

            if cache_file:
                try:
                    cache_data = {"result": _serialize_result(result)}
                    cache_file.write_text(json.dumps(cache_data, default=str))
                except (TypeError, ValueError):
                    pass

        return result

    return wrapper


def _find_project_cache_dir(start_path: Path) -> Path | None:
    """Find the project-level .raw/cache directory.

    Walks up from start_path looking for a .raw directory containing
    config.yaml (project root). Returns the cache subdirectory path.
    Returns None if no project root is found.
    """
    current = start_path.resolve()
    for _ in range(20):  # Limit search depth
        raw_dir = current / ".raw"
        if raw_dir.exists() and (raw_dir / "config.yaml").exists():
            return raw_dir / "cache"
        if current.parent == current:
            break
        current = current.parent
    return None


def _generate_cache_key(func_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """Generate a cache key from function name and arguments."""
    cache_args = args
    if args and hasattr(args[0], "__dict__") and not isinstance(args[0], type):
        cache_args = args[1:]

    key_data = {
        "func": func_name,
        "args": [_make_hashable(a) for a in cache_args],
        "kwargs": {k: _make_hashable(v) for k, v in sorted(kwargs.items())},
    }

    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.sha256(key_str.encode()).hexdigest()[:12]


def _make_hashable(obj: Any) -> Any:
    """Convert object to something JSON-serializable for hashing."""
    if isinstance(obj, str | int | float | bool | type(None)):
        return obj
    elif isinstance(obj, list | tuple):
        return [_make_hashable(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: _make_hashable(v) for k, v in sorted(obj.items())}
    else:
        return str(obj)


def _serialize_result(result: Any) -> Any:
    """Serialize step result for manifest storage."""
    if result is None:
        return None
    if isinstance(result, str | int | float | bool):
        return result
    if isinstance(result, list | tuple):
        return [_serialize_result(x) for x in result]
    if isinstance(result, dict):
        return {k: _serialize_result(v) for k, v in result.items()}
    return {"_type": type(result).__name__, "_str": str(result)[:200]}


def conditional(
    condition: Callable[..., bool],
    skip_reason: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T | None]]:
    """Decorator for conditional step execution.

    If the condition returns False, the step is skipped and recorded
    as SKIPPED in the manifest. If True, the step executes normally.

    Args:
        condition: Callable that returns True to execute, False to skip.
                   Receives the same arguments as the wrapped function.
        skip_reason: Optional reason to record when step is skipped.

    Usage:
        @raw_step("send_alert")
        @conditional(lambda self: self.params.threshold_exceeded)
        def send_alert(self):
            return send_notification()

        # Or with a method reference:
        @raw_step("generate_report")
        @conditional(lambda self: self.should_generate_report())
        def generate_report(self):
            return create_pdf()
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T | None]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
            should_run = condition(*args, **kwargs)

            if should_run:
                return func(*args, **kwargs)

            context = get_workflow_context()
            step_name = func.__name__
            reason = skip_reason or "Condition not met"

            if context:
                context.skip_step(step_name, reason)
                context.emit(
                    StepSkippedEvent(
                        workflow_id=context.workflow_id,
                        run_id=context.run_id,
                        step_name=step_name,
                        reason=reason,
                    )
                )

            return None

        return wrapper

    return decorator

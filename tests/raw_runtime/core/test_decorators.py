"""Tests for RAW runtime decorators."""

from pathlib import Path

import pytest

from raw_runtime import (
    WorkflowContext,
    cache_step,
    raw_step,
    retry,
    set_workflow_context,
)
from raw_runtime.models import StepStatus


class TestRawStep:
    """Tests for @raw_step decorator."""

    def test_tracks_success(self) -> None:
        """Test that successful steps are tracked."""
        ctx = WorkflowContext(
            workflow_id="test-123",
            short_name="test",
        )
        set_workflow_context(ctx)

        @raw_step("my_step")
        def my_step() -> dict[str, int]:
            return {"value": 42}

        result = my_step()

        assert result == {"value": 42}

        steps = ctx.get_steps()
        assert len(steps) == 1
        assert steps[0].name == "my_step"
        assert steps[0].status == StepStatus.SUCCESS
        assert steps[0].duration_seconds is not None
        assert steps[0].duration_seconds >= 0

        set_workflow_context(None)

    def test_tracks_failure(self) -> None:
        """Test that failed steps are tracked."""
        ctx = WorkflowContext(
            workflow_id="test-123",
            short_name="test",
        )
        set_workflow_context(ctx)

        @raw_step("failing_step")
        def failing_step() -> None:
            raise ValueError("Something went wrong")

        with pytest.raises(ValueError, match="Something went wrong"):
            failing_step()

        steps = ctx.get_steps()
        assert len(steps) == 1
        assert steps[0].name == "failing_step"
        assert steps[0].status == StepStatus.FAILED
        assert steps[0].error == "Something went wrong"

        set_workflow_context(None)

    def test_works_without_context(self) -> None:
        """Test that decorator works even without context."""
        set_workflow_context(None)

        @raw_step("no_context_step")
        def no_context_step() -> str:
            return "ok"

        result = no_context_step()
        assert result == "ok"


class TestRetry:
    """Tests for @retry decorator."""

    def test_no_retry_on_success(self) -> None:
        """Test that successful calls don't retry."""
        call_count = 0

        @retry(retries=3)
        def successful_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()

        assert result == "success"
        assert call_count == 1

    def test_retries_on_failure(self) -> None:
        """Test that failures trigger retries."""
        call_count = 0

        @retry(retries=3, base_delay=0.01)  # Short delay for tests
        def failing_func() -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return None

        failing_func()

        assert call_count == 3

    def test_exhausts_retries(self) -> None:
        """Test that all retries are exhausted on persistent failure."""
        call_count = 0

        @retry(retries=2, base_delay=0.01)
        def always_fails() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fails()

        assert call_count == 3  # Initial + 2 retries

    def test_retry_on_specific_exception(self) -> None:
        """Test retry_on parameter."""
        call_count = 0

        @retry(retries=3, retry_on=(ValueError,), base_delay=0.01)
        def selective_retry() -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retry this")
            raise TypeError("Don't retry this")

        with pytest.raises(TypeError, match="Don't retry this"):
            selective_retry()

        assert call_count == 2  # First try + one retry before TypeError

    def test_retry_stores_config(self) -> None:
        """Test that retry config is stored on the wrapper."""

        @retry(retries=5, backoff="fixed")
        def func() -> str:
            return "ok"

        assert hasattr(func, "_retry_config")
        assert func._retry_config["retries"] == 5
        assert func._retry_config["backoff"] == "fixed"


class TestCacheStep:
    """Tests for @cache_step decorator."""

    def test_caches_result(self, tmp_path: Path) -> None:
        """Test that results are cached."""
        # Create project structure with .raw/config.yaml
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        raw_dir = project_dir / ".raw"
        raw_dir.mkdir()
        (raw_dir / "config.yaml").write_text("project: test")

        # Simulate run directory inside workflows
        workflow_dir = project_dir / ".raw" / "workflows" / "test-workflow" / "runs" / "20250101"
        workflow_dir.mkdir(parents=True)

        ctx = WorkflowContext(
            workflow_id="test-123",
            short_name="test",
            workflow_dir=workflow_dir,
        )
        set_workflow_context(ctx)

        call_count = 0

        @cache_step
        def expensive_func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - executes
        result1 = expensive_func(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - uses cache
        result2 = expensive_func(5)
        assert result2 == 10
        assert call_count == 1  # Still 1, used cache

        # Different argument - executes again
        result3 = expensive_func(10)
        assert result3 == 20
        assert call_count == 2

        set_workflow_context(None)

    def test_works_without_context(self) -> None:
        """Test cache_step works without context (no caching)."""
        set_workflow_context(None)

        call_count = 0

        @cache_step
        def no_cache_func() -> str:
            nonlocal call_count
            call_count += 1
            return "result"

        result1 = no_cache_func()
        result2 = no_cache_func()

        assert result1 == "result"
        assert result2 == "result"
        assert call_count == 2  # No caching without context


class TestDecoratorCombination:
    """Test combining decorators."""

    def test_raw_step_with_retry(self) -> None:
        """Test combining @raw_step and @retry."""
        ctx = WorkflowContext(
            workflow_id="test-123",
            short_name="test",
        )
        set_workflow_context(ctx)

        call_count = 0

        @raw_step("retry_step")
        @retry(retries=2, base_delay=0.01)
        def retry_step() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Try again")
            return "success"

        result = retry_step()

        assert result == "success"
        assert call_count == 2

        # Should have recorded success
        steps = ctx.get_steps()
        assert len(steps) == 1
        assert steps[0].status == StepStatus.SUCCESS

        set_workflow_context(None)

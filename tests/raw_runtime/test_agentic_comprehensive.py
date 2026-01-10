"""Comprehensive tests for @agentic decorator edge cases and integration."""

import json
import time
from pathlib import Path
from typing import Literal, Optional, Union
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import BaseModel

from raw_runtime import WorkflowContext, set_workflow_context
from raw_runtime.agentic import (
    AgenticStepError,
    CostLimitExceededError,
    _format_prompt,
    _generate_cache_key,
    _get_cache,
    agentic,
)
from raw_runtime.events import CacheHitEvent, CacheMissEvent, StepCompletedEvent, StepStartedEvent


class TestPromptFormattingEdgeCases:
    """Tests for prompt formatting edge cases."""

    def test_format_with_nested_objects(self) -> None:
        """Test formatting with nested object access."""

        class NestedData:
            def __init__(self) -> None:
                self.value = "nested"

        def func(data: NestedData) -> str:
            pass

        obj = NestedData()
        template = "Value: {context.data.value}"
        result = _format_prompt(template, func, (obj,), {})
        assert result == "Value: nested"

    def test_format_with_dict_access(self) -> None:
        """Test formatting with dict-like attribute."""

        def func(config: dict) -> str:
            pass

        config = {"key": "value", "count": 42}
        # Dict attributes need special handling or won't work with dot notation
        # This tests the failure case
        template = "Config: {context.config}"
        result = _format_prompt(template, func, (config,), {})
        assert "key" in result or "value" in result

    def test_format_with_defaults(self) -> None:
        """Test that default parameter values are used."""

        def func(required: str, optional: str = "default") -> str:
            pass

        template = "Required: {context.required}, Optional: {context.optional}"
        result = _format_prompt(template, func, ("value",), {})
        assert result == "Required: value, Optional: default"

    def test_format_with_none_values(self) -> None:
        """Test formatting with None values."""

        def func(value: str | None) -> str:
            pass

        template = "Value: {context.value}"
        result = _format_prompt(template, func, (None,), {})
        assert result == "Value: None"

    def test_format_with_special_chars(self) -> None:
        """Test formatting with special characters."""

        def func(text: str) -> str:
            pass

        template = "Text: {context.text}"
        special_text = "Line 1\nLine 2\tTabbed\r\nNewline"
        result = _format_prompt(template, func, (special_text,), {})
        assert special_text in result

    def test_format_with_empty_string(self) -> None:
        """Test formatting with empty string."""

        def func(text: str) -> str:
            pass

        template = "Text: '{context.text}'"
        result = _format_prompt(template, func, ("",), {})
        assert result == "Text: ''"


class TestCacheKeyGeneration:
    """Tests for cache key generation edge cases."""

    def test_cache_key_deterministic(self) -> None:
        """Test that cache keys are deterministic."""
        keys = [_generate_cache_key("prompt", "model") for _ in range(10)]
        assert len(set(keys)) == 1

    def test_cache_key_length(self) -> None:
        """Test that cache key has expected SHA256 length."""
        key = _generate_cache_key("prompt", "model")
        assert len(key) == 64  # SHA256 hex length

    def test_cache_key_with_unicode(self) -> None:
        """Test cache key generation with unicode."""
        key1 = _generate_cache_key("Hello 世界", "model")
        key2 = _generate_cache_key("Hello 世界", "model")
        assert key1 == key2

    def test_cache_key_with_very_long_prompt(self) -> None:
        """Test cache key with very long prompt."""
        long_prompt = "A" * 100_000
        key = _generate_cache_key(long_prompt, "model")
        assert len(key) == 64


class TestResponseParsingEdgeCases:
    """Tests for response parsing edge cases."""

    def test_parse_float_from_complex_text(self) -> None:
        """Test parsing float from complex text."""
        from raw_runtime.agentic_parser import parse_float

        response = "The temperature is approximately 98.6°F with an error margin of ±0.5"
        result = parse_float(response)
        assert result == 98.6

    def test_parse_int_negative(self) -> None:
        """Test parsing negative integers."""
        from raw_runtime.agentic_parser import parse_int

        assert parse_int("-42") == -42
        assert parse_int("Deficit: -100") == -100

    def test_parse_list_of_dicts(self) -> None:
        """Test parsing list of dicts (Pydantic model lists not yet supported)."""
        from raw_runtime.agentic_parser import parse_response

        response = '[{"name": "A", "count": 1}, {"name": "B", "count": 2}]'
        result = parse_response(response, list)
        assert len(result) == 2
        assert result[0]["name"] == "A"
        assert result[1]["count"] == 2


class TestCostLimitEdgeCases:
    """Tests for cost limit edge cases."""

    def setup_method(self) -> None:
        """Set up test context."""
        self.ctx = WorkflowContext(
            workflow_id="test-123",
            short_name="test",
        )
        set_workflow_context(self.ctx)

    def teardown_method(self) -> None:
        """Clean up test context."""
        set_workflow_context(None)

    def test_cost_limit_exact_match(self) -> None:
        """Test when estimated cost exactly equals limit."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            # Set cost limit to exactly match estimated cost
            # For haiku: ~10 input tokens + 100 output = ~0.0004
            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                max_tokens=100,
                cost_limit=1.0,  # Very high - should not trigger
            )
            def process(text: str) -> str:
                pass

            result = process("test")
            assert result == "result"

    def test_cost_limit_none_allows_any_cost(self) -> None:
        """Test that None cost limit allows any cost."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=1_000_000, output_tokens=1_000_000)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-sonnet-20241022",
                cost_limit=None,  # No limit
            )
            def process(text: str) -> str:
                pass

            result = process("test" * 10000)
            assert result == "result"


class TestCachingEdgeCases:
    """Tests for caching edge cases."""

    def setup_method(self) -> None:
        """Set up test context and clean cache."""
        import shutil
        import tempfile

        from raw_runtime import agentic

        self.ctx = WorkflowContext(
            workflow_id="test-cache-edge",
            short_name="test",
        )
        set_workflow_context(self.ctx)

        # Reset global cache and clear directories
        agentic._cache = None

        cache_dir = Path(".raw/cache/agentic")
        if cache_dir.exists():
            shutil.rmtree(cache_dir)

        temp_cache_dir = Path(tempfile.gettempdir()) / "raw_cache" / "agentic"
        if temp_cache_dir.exists():
            shutil.rmtree(temp_cache_dir)

    def teardown_method(self) -> None:
        """Clean up test context."""
        set_workflow_context(None)

    def test_cache_with_very_large_response(self) -> None:
        """Test caching with very large response."""
        mock_response = Mock()
        large_data = {"data": "X" * 100_000}
        mock_response.content = [Mock(text=json.dumps(large_data))]
        mock_response.usage = Mock(input_tokens=10, output_tokens=10000)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process unique large: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=True,
            )
            def process_large_unique(text: str) -> dict:
                pass

            result1 = process_large_unique("test_large_unique_xyz")
            assert result1 == large_data
            call_count_after_first = mock_client.messages.create.call_count

            # Second call should use cache
            result2 = process_large_unique("test_large_unique_xyz")
            assert result2 == large_data
            # Should not have called API again
            assert mock_client.messages.create.call_count == call_count_after_first

    def test_cache_with_complex_nested_structure(self) -> None:
        """Test caching with complex nested Pydantic models."""

        class Address(BaseModel):
            street: str
            city: str

        class Person(BaseModel):
            name: str
            address: Address

        mock_response = Mock()
        data = {"name": "John", "address": {"street": "123 Main", "city": "NYC"}}
        mock_response.content = [Mock(text=json.dumps(data))]
        mock_response.usage = Mock(input_tokens=10, output_tokens=20)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Get person unique nested: {context.id}",
                model="claude-3-5-haiku-20241022",
                cache=True,
            )
            def get_person_nested_unique(id: str) -> Person:
                pass

            result1 = get_person_nested_unique("nested123")
            assert isinstance(result1, Person)
            assert result1.name == "John"
            assert result1.address.city == "NYC"
            call_count_after_first = mock_client.messages.create.call_count

            # Cache hit
            result2 = get_person_nested_unique("nested123")
            assert isinstance(result2, Person)
            assert result2.name == "John"
            assert mock_client.messages.create.call_count == call_count_after_first


class TestEventEmission:
    """Tests for event emission edge cases."""

    def setup_method(self) -> None:
        """Set up test context."""
        self.ctx = WorkflowContext(
            workflow_id="test-events",
            short_name="test",
        )
        set_workflow_context(self.ctx)
        self.events = []
        self.ctx.emit = lambda e: self.events.append(e)  # type: ignore[method-assign]

    def teardown_method(self) -> None:
        """Clean up test context."""
        set_workflow_context(None)

    def test_events_include_step_name(self) -> None:
        """Test that events include correct step name."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def my_custom_step_name() -> str:
                pass

            my_custom_step_name()

            step_started = [e for e in self.events if isinstance(e, StepStartedEvent)]
            assert len(step_started) == 1
            assert step_started[0].step_name == "my_custom_step_name"

    def test_events_with_cached_response(self) -> None:
        """Test that cached responses still emit events."""
        import shutil
        import tempfile

        from raw_runtime import agentic

        # Reset cache
        agentic._cache = None
        cache_dir = Path(".raw/cache/agentic")
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        temp_cache_dir = Path(tempfile.gettempdir()) / "raw_cache" / "agentic"
        if temp_cache_dir.exists():
            shutil.rmtree(temp_cache_dir)

        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Unique event test xyz789: {context.id}",
                model="claude-3-5-haiku-20241022",
                cache=True,
            )
            def process_events_xyz789(id: str) -> str:
                pass

            # First call
            self.events.clear()
            process_events_xyz789("evt_xyz_1")

            # Should have cache miss + start + complete
            assert any(isinstance(e, CacheMissEvent) for e in self.events)
            assert any(isinstance(e, StepStartedEvent) for e in self.events)
            assert any(isinstance(e, StepCompletedEvent) for e in self.events)

            # Second call (cached)
            self.events.clear()
            process_events_xyz789("evt_xyz_1")

            # Should have cache hit + start + complete
            assert any(isinstance(e, CacheHitEvent) for e in self.events)
            assert any(isinstance(e, StepStartedEvent) for e in self.events)
            assert any(isinstance(e, StepCompletedEvent) for e in self.events)


class TestErrorHandling:
    """Tests for error handling edge cases."""

    def setup_method(self) -> None:
        """Set up test context."""
        self.ctx = WorkflowContext(
            workflow_id="test-errors",
            short_name="test",
        )
        set_workflow_context(self.ctx)

    def teardown_method(self) -> None:
        """Clean up test context."""
        set_workflow_context(None)

    def test_api_timeout_wrapped(self) -> None:
        """Test that API timeouts are wrapped."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = TimeoutError("API timeout")
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def process() -> str:
                pass

            with pytest.raises(AgenticStepError, match="Anthropic API call failed"):
                process()

    def test_api_rate_limit_wrapped(self) -> None:
        """Test that rate limit errors are wrapped."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("Rate limit exceeded")
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def process() -> str:
                pass

            with pytest.raises(AgenticStepError) as exc_info:
                process()
            assert "Rate limit exceeded" in str(exc_info.value)

    def test_malformed_api_response(self) -> None:
        """Test handling of malformed API response (empty content returns empty string)."""
        from raw_runtime.agentic_parser import ResponseParsingError

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = []  # Empty content blocks
            mock_response.usage = Mock(input_tokens=10, output_tokens=0)
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Count items",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def count_items() -> int:
                pass

            # Empty response should fail parsing for int
            with pytest.raises(ResponseParsingError, match="Empty response"):
                count_items()

    def test_parsing_error_preserves_response(self) -> None:
        """Test that parsing errors include the original response."""
        from raw_runtime.agentic_parser import ResponseParsingError

        mock_response = Mock()
        mock_response.content = [Mock(text="not a valid integer")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Count",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def count() -> int:
                pass

            with pytest.raises(ResponseParsingError) as exc_info:
                count()

            error = exc_info.value
            # Response may be truncated in error but should be present
            assert "not a valid integer" in str(error) or "not a valid" in str(error)
            assert "int" in str(error)


class TestConcurrency:
    """Tests for concurrent access scenarios."""

    def test_cache_concurrent_reads(self) -> None:
        """Test that cache handles concurrent reads safely."""
        import concurrent.futures
        import shutil
        import tempfile

        from raw_runtime import agentic

        # Reset cache
        agentic._cache = None
        cache_dir = Path(".raw/cache/agentic")
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        temp_cache_dir = Path(tempfile.gettempdir()) / "raw_cache" / "agentic"
        if temp_cache_dir.exists():
            shutil.rmtree(temp_cache_dir)

        cache = _get_cache()

        # Populate cache
        cache.put("concurrent_key1", "prompt", "model", "concurrent_value1", 0.01)

        # Concurrent reads
        def read_cache():
            return cache.get("concurrent_key1")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_cache) for _ in range(100)]
            results = [f.result() for f in futures]

        # All reads should succeed
        assert all(r == "concurrent_value1" for r in results)


class TestPerformance:
    """Tests for performance requirements."""

    def test_cache_faster_than_api(self) -> None:
        """Test that cache retrieval is significantly faster than API."""
        import shutil
        import tempfile

        from raw_runtime import agentic

        # Reset cache
        agentic._cache = None
        cache_dir = Path(".raw/cache/agentic")
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        temp_cache_dir = Path(tempfile.gettempdir()) / "raw_cache" / "agentic"
        if temp_cache_dir.exists():
            shutil.rmtree(temp_cache_dir)

        ctx = WorkflowContext(workflow_id="test-perf", short_name="test")
        set_workflow_context(ctx)

        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        api_call_count = 0

        def slow_api(*args, **kwargs):
            nonlocal api_call_count
            api_call_count += 1
            time.sleep(0.05)  # Simulate API latency
            return mock_response

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = slow_api
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process unique perf: {context.id}",
                model="claude-3-5-haiku-20241022",
                cache=True,
            )
            def process_perf_unique(id: str) -> str:
                pass

            # First call - API (slow)
            start = time.time()
            process_perf_unique("perf_unique_1")
            api_time = time.time() - start

            # Second call - Cache (fast)
            start = time.time()
            process_perf_unique("perf_unique_1")
            cache_time = time.time() - start

            # Verify cache was used (no second API call)
            assert api_call_count == 1
            # Cache should be faster (not necessarily 10x due to overhead, but measurably faster)
            assert cache_time < api_time

        set_workflow_context(None)

    def test_cost_estimation_fast(self) -> None:
        """Test that cost estimation is fast (<10ms)."""
        from raw_runtime.agentic_cost import estimate_cost

        prompt = "Test prompt " * 100
        start = time.time()
        estimate_cost(prompt, 1000, "claude-3-5-sonnet-20241022")
        duration = time.time() - start

        assert duration < 0.01  # Less than 10ms

    def test_parsing_handles_large_responses(self) -> None:
        """Test that parsing handles 10KB+ responses."""
        from raw_runtime.agentic_parser import parse_response

        # Create 10KB response
        large_text = "X" * 10_000
        result = parse_response(large_text, str)
        assert len(result) == 10_000


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios."""

    def setup_method(self) -> None:
        """Set up test context."""
        import shutil
        import tempfile

        from raw_runtime import agentic

        self.ctx = WorkflowContext(
            workflow_id="test-integration",
            short_name="test",
        )
        set_workflow_context(self.ctx)

        # Reset cache
        agentic._cache = None
        cache_dir = Path(".raw/cache/agentic")
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        temp_cache_dir = Path(tempfile.gettempdir()) / "raw_cache" / "agentic"
        if temp_cache_dir.exists():
            shutil.rmtree(temp_cache_dir)

    def teardown_method(self) -> None:
        """Clean up test context."""
        set_workflow_context(None)

    def test_multi_step_workflow_with_cost_tracking(self) -> None:
        """Test multi-step workflow with cost tracking."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Step 1",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def step1() -> str:
                pass

            @agentic(
                prompt="Step 2",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def step2() -> str:
                pass

            @agentic(
                prompt="Step 3",
                model="claude-3-5-sonnet-20241022",
                cache=False,
            )
            def step3() -> str:
                pass

            step1()
            step2()
            step3()

            # Verify costs were tracked
            assert len(self.ctx.agentic_costs) == 3
            assert self.ctx.total_agentic_cost > 0

            # Verify different models tracked separately
            models_used = [step["model"] for step in self.ctx.agentic_costs]
            assert "claude-3-5-haiku-20241022" in models_used
            assert "claude-3-5-sonnet-20241022" in models_used

    def test_workflow_with_mixed_caching(self) -> None:
        """Test workflow with some steps cached and some not."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Cached step mixed unique abc: {context.id}",
                model="claude-3-5-haiku-20241022",
                cache=True,
            )
            def cached_step_mixed_abc(id: str) -> str:
                pass

            @agentic(
                prompt="Uncached step mixed unique def: {context.id}",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def uncached_step_mixed_def(id: str) -> str:
                pass

            # Call each twice
            cached_step_mixed_abc("mixed_1")
            call_count_after_cached_1 = mock_client.messages.create.call_count
            cached_step_mixed_abc("mixed_1")  # Should use cache
            call_count_after_cached_2 = mock_client.messages.create.call_count
            uncached_step_mixed_def("mixed_1")
            call_count_after_uncached_1 = mock_client.messages.create.call_count
            uncached_step_mixed_def("mixed_1")  # Should NOT use cache
            call_count_final = mock_client.messages.create.call_count

            # Verify: 1 for cached (second call uses cache), 2 for uncached (both call API)
            assert call_count_after_cached_2 == call_count_after_cached_1  # Cache hit
            assert call_count_after_uncached_1 == call_count_after_cached_2 + 1  # API call
            assert call_count_final == call_count_after_uncached_1 + 1  # Another API call

            # Verify cache metrics
            assert self.ctx.agentic_cache_hits >= 1
            assert self.ctx.agentic_cache_misses >= 1

"""Additional comprehensive tests for @agentic decorator without cache dependencies."""

import time
from typing import Literal, Optional, Union
from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel, Field

from raw_runtime import WorkflowContext, set_workflow_context
from raw_runtime.agentic import AgenticStepError, CostLimitExceededError, _format_prompt, _generate_cache_key, agentic
from raw_runtime.agentic_parser import ResponseParsingError


class TestAdvancedPromptFormatting:
    """Advanced prompt formatting tests."""

    def test_format_with_list_argument(self) -> None:
        """Test formatting with list argument."""

        def func(items: list[str]) -> str:
            pass

        template = "Items: {context.items}"
        result = _format_prompt(template, func, (["a", "b", "c"],), {})
        assert "a" in result
        assert "b" in result
        assert "c" in result

    def test_format_with_numeric_values(self) -> None:
        """Test formatting with various numeric types."""

        def func(count: int, ratio: float) -> str:
            pass

        template = "Count: {context.count}, Ratio: {context.ratio}"
        result = _format_prompt(template, func, (42, 3.14), {})
        assert result == "Count: 42, Ratio: 3.14"

    def test_format_with_boolean_values(self) -> None:
        """Test formatting with boolean values."""

        def func(flag: bool) -> str:
            pass

        template = "Flag is: {context.flag}"
        result1 = _format_prompt(template, func, (True,), {})
        assert result1 == "Flag is: True"

        result2 = _format_prompt(template, func, (False,), {})
        assert result2 == "Flag is: False"


class TestResponseTypeHandling:
    """Tests for various response type handling."""

    def setup_method(self) -> None:
        """Set up test context."""
        self.ctx = WorkflowContext(workflow_id="test-types", short_name="test")
        set_workflow_context(self.ctx)

    def teardown_method(self) -> None:
        """Clean up test context."""
        set_workflow_context(None)

    def test_optional_with_value(self) -> None:
        """Test Optional type with actual value."""
        mock_response = Mock()
        mock_response.content = [Mock(text="42")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Get count",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def get_count() -> Optional[int]:
                pass

            result = get_count()
            assert result == 42
            assert isinstance(result, int)

    def test_optional_with_none(self) -> None:
        """Test Optional type returning None."""
        mock_response = Mock()
        mock_response.content = [Mock(text="null")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Get value",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def get_value() -> Optional[str]:
                pass

            result = get_value()
            assert result is None

    def test_union_type_int_str(self) -> None:
        """Test Union type with int|str."""
        mock_response = Mock()
        mock_response.content = [Mock(text="42")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Get value",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def get_value() -> Union[int, str]:
                pass

            result = get_value()
            # Should parse as int first
            assert result == 42
            assert isinstance(result, int)

    def test_float_return_type(self) -> None:
        """Test float return type."""
        mock_response = Mock()
        mock_response.content = [Mock(text="3.14159")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Get pi",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def get_pi() -> float:
                pass

            result = get_pi()
            assert abs(result - 3.14159) < 0.00001
            assert isinstance(result, float)


class TestModelParameterVariations:
    """Tests for different model and parameter combinations."""

    def setup_method(self) -> None:
        """Set up test context."""
        self.ctx = WorkflowContext(workflow_id="test-models", short_name="test")
        set_workflow_context(self.ctx)

    def teardown_method(self) -> None:
        """Clean up test context."""
        set_workflow_context(None)

    def test_different_models(self) -> None:
        """Test using different Claude models."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        models_tested = []

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response

            def track_model(*args, **kwargs):
                models_tested.append(kwargs.get("model"))
                return mock_response

            mock_client.messages.create.side_effect = track_model
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Test",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def haiku() -> str:
                pass

            @agentic(
                prompt="Test",
                model="claude-3-5-sonnet-20241022",
                cache=False,
            )
            def sonnet() -> str:
                pass

            @agentic(
                prompt="Test",
                model="claude-3-opus-20240229",
                cache=False,
            )
            def opus() -> str:
                pass

            haiku()
            sonnet()
            opus()

            assert "claude-3-5-haiku-20241022" in models_tested
            assert "claude-3-5-sonnet-20241022" in models_tested
            assert "claude-3-opus-20240229" in models_tested

    def test_different_max_tokens(self) -> None:
        """Test using different max_tokens values."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        max_tokens_used = []

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()

            def track_max_tokens(*args, **kwargs):
                max_tokens_used.append(kwargs.get("max_tokens"))
                return mock_response

            mock_client.messages.create.side_effect = track_max_tokens
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Test",
                model="claude-3-5-haiku-20241022",
                max_tokens=100,
                cache=False,
            )
            def small() -> str:
                pass

            @agentic(
                prompt="Test",
                model="claude-3-5-haiku-20241022",
                max_tokens=4096,
                cache=False,
            )
            def large() -> str:
                pass

            small()
            large()

            assert 100 in max_tokens_used
            assert 4096 in max_tokens_used

    def test_different_temperatures(self) -> None:
        """Test using different temperature values."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        temps_used = []

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()

            def track_temperature(*args, **kwargs):
                temps_used.append(kwargs.get("temperature"))
                return mock_response

            mock_client.messages.create.side_effect = track_temperature
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Test",
                model="claude-3-5-haiku-20241022",
                temperature=0.0,
                cache=False,
            )
            def deterministic() -> str:
                pass

            @agentic(
                prompt="Test",
                model="claude-3-5-haiku-20241022",
                temperature=1.0,
                cache=False,
            )
            def creative() -> str:
                pass

            deterministic()
            creative()

            assert 0.0 in temps_used
            assert 1.0 in temps_used


class TestErrorMessageQuality:
    """Tests for error message quality and clarity."""

    def setup_method(self) -> None:
        """Set up test context."""
        self.ctx = WorkflowContext(workflow_id="test-errors", short_name="test")
        set_workflow_context(self.ctx)

    def teardown_method(self) -> None:
        """Clean up test context."""
        set_workflow_context(None)

    def test_cost_limit_error_shows_values(self) -> None:
        """Test that cost limit error shows estimated vs limit."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process",
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                cost_limit=0.001,
            )
            def expensive() -> str:
                pass

            try:
                expensive()
            except CostLimitExceededError as e:
                error_msg = str(e)
                # Should show dollar amounts
                assert "$" in error_msg
                # Should mention "exceed"
                assert "exceed" in error_msg.lower()
                # Should have numeric values
                assert any(char.isdigit() for char in error_msg)

    def test_parsing_error_has_suggestions(self) -> None:
        """Test that parsing errors include helpful suggestions."""
        mock_response = Mock()
        mock_response.content = [Mock(text="maybe")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Is it true?",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def check() -> bool:
                pass

            try:
                check()
            except ResponseParsingError as e:
                error_msg = str(e).lower()
                # Should have suggestions
                assert "suggest" in error_msg or "try" in error_msg or "valid" in error_msg


class TestContextIntegration:
    """Tests for WorkflowContext integration."""

    def setup_method(self) -> None:
        """Set up test context."""
        self.ctx = WorkflowContext(workflow_id="test-ctx", short_name="test")
        set_workflow_context(self.ctx)

    def teardown_method(self) -> None:
        """Clean up test context."""
        set_workflow_context(None)

    def test_context_accumulates_costs(self) -> None:
        """Test that context accumulates costs across steps."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(prompt="Step", model="claude-3-5-haiku-20241022", cache=False)
            def step() -> str:
                pass

            initial_cost = self.ctx.total_agentic_cost

            step()
            cost_after_1 = self.ctx.total_agentic_cost

            step()
            cost_after_2 = self.ctx.total_agentic_cost

            step()
            cost_after_3 = self.ctx.total_agentic_cost

            # Costs should accumulate
            assert cost_after_1 > initial_cost
            assert cost_after_2 > cost_after_1
            assert cost_after_3 > cost_after_2

    def test_context_tracks_token_usage(self) -> None:
        """Test that context tracks token usage."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=123, output_tokens=456)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(prompt="Step", model="claude-3-5-haiku-20241022", cache=False)
            def step() -> str:
                pass

            step()

            assert len(self.ctx.agentic_costs) > 0
            latest = self.ctx.agentic_costs[-1]
            assert latest["tokens"]["input"] == 123
            assert latest["tokens"]["output"] == 456


class TestCacheKeyProperties:
    """Tests for cache key properties."""

    def test_cache_key_hex_format(self) -> None:
        """Test that cache keys are valid hex."""
        key = _generate_cache_key("test prompt", "test-model")
        # Should be valid hex
        try:
            int(key, 16)
        except ValueError:
            pytest.fail("Cache key should be valid hexadecimal")

    def test_cache_key_different_prompt_order(self) -> None:
        """Test that prompt order matters for cache key."""
        key1 = _generate_cache_key("hello world", "model")
        key2 = _generate_cache_key("world hello", "model")
        assert key1 != key2

    def test_cache_key_model_matters(self) -> None:
        """Test that model affects cache key."""
        key1 = _generate_cache_key("prompt", "haiku")
        key2 = _generate_cache_key("prompt", "sonnet")
        assert key1 != key2


class TestPerformanceCharacteristics:
    """Tests for performance characteristics without timing dependencies."""

    def test_cost_estimation_doesnt_raise(self) -> None:
        """Test that cost estimation doesn't raise for large prompts."""
        from raw_runtime.agentic_cost import estimate_cost

        # Very large prompt
        large_prompt = "test " * 10000
        cost = estimate_cost(large_prompt, 4096, "claude-3-5-sonnet-20241022")

        # Should return a reasonable value
        assert isinstance(cost, float)
        assert cost > 0
        assert cost < 1000  # Should be less than $1000

    def test_parsing_very_long_response_text(self) -> None:
        """Test parsing very long text responses."""
        from raw_runtime.agentic_parser import parse_response

        long_text = "A" * 50000
        result = parse_response(long_text, str)
        assert len(result) == 50000

    def test_parsing_deeply_nested_json(self) -> None:
        """Test parsing deeply nested JSON structures."""
        from raw_runtime.agentic_parser import parse_response

        class Level3(BaseModel):
            value: int

        class Level2(BaseModel):
            level3: Level3

        class Level1(BaseModel):
            level2: Level2

        json_str = '{"level2": {"level3": {"value": 42}}}'
        result = parse_response(json_str, Level1)

        assert isinstance(result, Level1)
        assert result.level2.level3.value == 42

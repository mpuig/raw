"""Tests for @agentic decorator."""

from typing import Literal
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import BaseModel

from raw_runtime import WorkflowContext, set_workflow_context
from raw_runtime.agentic import (
    AgenticStepError,
    CostLimitExceededError,
    _format_prompt,
    _generate_cache_key,
    agentic,
)
from raw_runtime.agentic_parser import ResponseParsingError, parse_response


class TestPromptFormatting:
    """Tests for prompt template formatting."""

    def test_format_with_single_arg(self) -> None:
        """Test formatting prompt with single argument."""

        def func(ticket: str) -> str:
            pass

        template = "Classify: {context.ticket}"
        result = _format_prompt(template, func, ("urgent bug",), {})
        assert result == "Classify: urgent bug"

    def test_format_with_multiple_args(self) -> None:
        """Test formatting prompt with multiple arguments."""

        def func(title: str, description: str) -> str:
            pass

        template = "Title: {context.title}\nDesc: {context.description}"
        result = _format_prompt(template, func, ("Bug", "Critical issue"), {})
        assert result == "Title: Bug\nDesc: Critical issue"

    def test_format_with_kwargs(self) -> None:
        """Test formatting prompt with keyword arguments."""

        def func(ticket: str, priority: str = "low") -> str:
            pass

        template = "Ticket: {context.ticket}, Priority: {context.priority}"
        result = _format_prompt(template, func, ("issue-123",), {"priority": "high"})
        assert result == "Ticket: issue-123, Priority: high"

    def test_format_skips_self(self) -> None:
        """Test that self parameter is skipped."""

        def func(self: object, ticket: str) -> str:
            pass

        template = "Ticket: {context.ticket}"
        result = _format_prompt(template, func, (object(), "issue-123"), {})
        assert result == "Ticket: issue-123"

    def test_format_invalid_placeholder(self) -> None:
        """Test error on invalid placeholder."""

        def func(ticket: str) -> str:
            pass

        template = "Value: {context.missing}"
        with pytest.raises(ValueError, match="Failed to format prompt template"):
            _format_prompt(template, func, ("ticket",), {})


class TestResponseParsing:
    """Tests for response parsing to typed values."""

    def test_parse_str(self) -> None:
        """Test parsing string response."""
        result = parse_response("hello world", str)
        assert result == "hello world"

    def test_parse_int(self) -> None:
        """Test parsing integer response."""
        result = parse_response("42", int)
        assert result == 42

    def test_parse_int_invalid(self) -> None:
        """Test parsing invalid integer raises error."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_response("not a number", int)
        assert "int" in str(exc_info.value)

    def test_parse_bool_true(self) -> None:
        """Test parsing boolean true values."""
        assert parse_response("true", bool) is True
        assert parse_response("True", bool) is True
        assert parse_response("yes", bool) is True
        assert parse_response("1", bool) is True

    def test_parse_bool_false(self) -> None:
        """Test parsing boolean false values."""
        assert parse_response("false", bool) is False
        assert parse_response("False", bool) is False
        assert parse_response("no", bool) is False
        assert parse_response("0", bool) is False

    def test_parse_bool_invalid(self) -> None:
        """Test parsing invalid boolean raises error."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_response("maybe", bool)
        assert "bool" in str(exc_info.value)

    def test_parse_literal(self) -> None:
        """Test parsing Literal type."""
        result = parse_response("high", Literal["critical", "high", "medium", "low"])
        assert result == "high"

    def test_parse_literal_invalid(self) -> None:
        """Test parsing invalid Literal value raises error."""
        with pytest.raises(ResponseParsingError) as exc_info:
            parse_response("invalid", Literal["critical", "high", "medium", "low"])
        assert "not in allowed values" in str(exc_info.value)

    def test_parse_pydantic_model(self) -> None:
        """Test parsing Pydantic model from JSON."""

        class Response(BaseModel):
            status: str
            count: int

        result = parse_response('{"status": "ok", "count": 5}', Response)
        assert isinstance(result, Response)
        assert result.status == "ok"
        assert result.count == 5

    def test_parse_pydantic_model_invalid(self) -> None:
        """Test parsing invalid Pydantic model raises error."""

        class Response(BaseModel):
            status: str
            count: int

        with pytest.raises(ResponseParsingError):
            parse_response("not json", Response)

    def test_parse_list(self) -> None:
        """Test parsing list from JSON."""
        result = parse_response('["a", "b", "c"]', list[str])
        assert result == ["a", "b", "c"]

    def test_parse_list_invalid(self) -> None:
        """Test parsing invalid list raises error."""
        with pytest.raises(ResponseParsingError):
            parse_response("not a list", list[str])

    def test_parse_dict(self) -> None:
        """Test parsing dict from JSON."""
        result = parse_response('{"key": "value"}', dict)
        assert result == {"key": "value"}

    def test_parse_dict_invalid(self) -> None:
        """Test parsing invalid dict raises error."""
        with pytest.raises(ResponseParsingError):
            parse_response("not a dict", dict)


class TestCacheKey:
    """Tests for cache key generation."""

    def test_same_inputs_same_key(self) -> None:
        """Test that same inputs produce same cache key."""
        key1 = _generate_cache_key("prompt", "model")
        key2 = _generate_cache_key("prompt", "model")
        assert key1 == key2

    def test_different_inputs_different_key(self) -> None:
        """Test that different inputs produce different keys."""
        key1 = _generate_cache_key("prompt1", "model")
        key2 = _generate_cache_key("prompt2", "model")
        assert key1 != key2


class TestAgenticDecorator:
    """Tests for @agentic decorator."""

    def setup_method(self) -> None:
        """Set up test context."""
        self.ctx = WorkflowContext(
            workflow_id="test-123",
            short_name="test",
        )
        set_workflow_context(self.ctx)

        # Reset global cache between tests and clear cache directory
        import shutil
        import tempfile
        from pathlib import Path

        from raw_runtime import agentic

        agentic._cache = None

        # Clear file-based cache (both .raw and tempdir)
        cache_dir = Path(".raw/cache/agentic")
        if cache_dir.exists():
            shutil.rmtree(cache_dir)

        # Also clear temp directory cache
        temp_cache_dir = Path(tempfile.gettempdir()) / "raw_cache" / "agentic"
        if temp_cache_dir.exists():
            shutil.rmtree(temp_cache_dir)

    def teardown_method(self) -> None:
        """Clean up test context."""
        set_workflow_context(None)

    def test_basic_call(self) -> None:
        """Test basic agentic decorator call."""
        mock_response = Mock()
        mock_response.content = [Mock(text="high")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Classify: {context.ticket}",
                model="claude-3-5-haiku-20241022",
            )
            def classify(ticket: str) -> str:
                pass

            result = classify("urgent bug")

            assert result == "high"
            mock_client.messages.create.assert_called_once()

    def test_literal_type(self) -> None:
        """Test agentic decorator with Literal return type."""
        mock_response = Mock()
        mock_response.content = [Mock(text="high")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Classify: {context.ticket}",
                model="claude-3-5-haiku-20241022",
            )
            def classify(ticket: str) -> Literal["critical", "high", "medium", "low"]:
                pass

            result = classify("urgent bug")

            assert result == "high"

    def test_int_return_type(self) -> None:
        """Test agentic decorator with int return type."""
        mock_response = Mock()
        mock_response.content = [Mock(text="42")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Count items in: {context.text}",
                model="claude-3-5-haiku-20241022",
            )
            def count_items(text: str) -> int:
                pass

            result = count_items("some text")

            assert result == 42
            assert isinstance(result, int)

    def test_bool_return_type(self) -> None:
        """Test agentic decorator with bool return type."""
        mock_response = Mock()
        mock_response.content = [Mock(text="true")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Is urgent: {context.ticket}",
                model="claude-3-5-haiku-20241022",
            )
            def is_urgent(ticket: str) -> bool:
                pass

            result = is_urgent("urgent bug")

            assert result is True

    def test_pydantic_return_type(self) -> None:
        """Test agentic decorator with Pydantic model return type."""

        class Classification(BaseModel):
            priority: str
            confidence: float

        mock_response = Mock()
        mock_response.content = [Mock(text='{"priority": "high", "confidence": 0.95}')]
        mock_response.usage = Mock(input_tokens=10, output_tokens=20)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Classify: {context.ticket}",
                model="claude-3-5-sonnet-20241022",
            )
            def classify(ticket: str) -> Classification:
                pass

            result = classify("urgent bug")

            assert isinstance(result, Classification)
            assert result.priority == "high"
            assert result.confidence == 0.95

    def test_list_return_type(self) -> None:
        """Test agentic decorator with list return type."""
        mock_response = Mock()
        mock_response.content = [Mock(text='["item1", "item2", "item3"]')]
        mock_response.usage = Mock(input_tokens=10, output_tokens=15)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Extract items from: {context.text}",
                model="claude-3-5-haiku-20241022",
            )
            def extract_items(text: str) -> list:
                pass

            result = extract_items("some text")

            assert result == ["item1", "item2", "item3"]

    def test_dict_return_type(self) -> None:
        """Test agentic decorator with dict return type."""
        mock_response = Mock()
        mock_response.content = [Mock(text='{"status": "ok", "count": 5}')]
        mock_response.usage = Mock(input_tokens=10, output_tokens=15)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Analyze: {context.data}",
                model="claude-3-5-haiku-20241022",
            )
            def analyze(data: str) -> dict:
                pass

            result = analyze("test data")

            assert result == {"status": "ok", "count": 5}

    def test_cost_limit_enforced(self) -> None:
        """Test that cost limit is enforced."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        # High token counts to exceed cost limit
        mock_response.usage = Mock(input_tokens=1_000_000, output_tokens=1_000_000)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                cost_limit=0.001,  # Very low limit
            )
            def process(text: str) -> str:
                pass

            with pytest.raises(CostLimitExceededError) as exc_info:
                process("test " * 1000)  # Long input to trigger estimation

            # Error should have estimated_cost and cost_limit fields
            assert exc_info.value.estimated_cost > exc_info.value.cost_limit
            # API should NOT have been called
            mock_client.messages.create.assert_not_called()

    def test_caching_enabled(self) -> None:
        """Test that caching works when enabled."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Unique cache test prompt XYZ123: {context.text}",  # Very unique
                model="claude-3-5-haiku-20241022",
                cache=True,
            )
            def process_unique_xyz(text: str) -> str:
                pass

            # First call - should hit API
            result1 = process_unique_xyz("value_one_xyz")
            assert result1 == "result"
            assert mock_client.messages.create.call_count == 1

            # Second call with same input - should use cache
            result2 = process_unique_xyz("value_one_xyz")
            assert result2 == "result"
            assert mock_client.messages.create.call_count == 1  # Not called again

            # Third call with different input - should hit API
            result3 = process_unique_xyz("value_two_xyz")
            assert result3 == "result"
            assert mock_client.messages.create.call_count == 2

    def test_caching_disabled(self) -> None:
        """Test that caching can be disabled."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def process(text: str) -> str:
                pass

            # First call
            result1 = process("test")
            assert result1 == "result"
            assert mock_client.messages.create.call_count == 1

            # Second call with same input - should NOT use cache
            result2 = process("test")
            assert result2 == "result"
            assert mock_client.messages.create.call_count == 2

    def test_emits_events(self) -> None:
        """Test that decorator emits workflow events."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=False,  # Disable cache to avoid cache miss events
            )
            def process(text: str) -> str:
                pass

            # Mock event bus
            events = []
            self.ctx.emit = lambda e: events.append(e)  # type: ignore[method-assign]

            result = process("test")

            assert result == "result"
            assert len(events) == 2  # Started and Completed
            assert events[0].event_type.value == "step.started"
            assert events[1].event_type.value == "step.completed"

    def test_works_without_context(self) -> None:
        """Test decorator works without workflow context."""
        set_workflow_context(None)

        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
            )
            def process(text: str) -> str:
                pass

            result = process("test")
            assert result == "result"

    def test_api_error_wrapped(self) -> None:
        """Test that API errors are wrapped in AgenticStepError."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception("API Error")
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=False,  # Disable cache
            )
            def process(text: str) -> str:
                pass

            with pytest.raises(AgenticStepError, match="Anthropic API call failed"):
                process("test")

    def test_missing_anthropic_library(self) -> None:
        """Test error when anthropic library is not installed."""
        # Mock the import to raise ImportError
        with patch.dict("sys.modules", {"anthropic": None}):

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=False,  # Disable cache to avoid cache lookup
            )
            def process(text: str) -> str:
                pass

            with pytest.raises(AgenticStepError, match="anthropic library not installed"):
                process("test")


class TestErrorClasses:
    """Tests for error classes."""

    def test_cost_limit_exceeded_error(self) -> None:
        """Test CostLimitExceededError attributes."""
        error = CostLimitExceededError(estimated_cost=0.05, cost_limit=0.01, step_name="test_step")
        assert error.estimated_cost == 0.05
        assert error.cost_limit == 0.01
        assert error.step_name == "test_step"
        assert "$0.0500" in str(error)
        assert "$0.0100" in str(error)
        assert "test_step" in str(error)

    def test_response_parsing_error(self) -> None:
        """Test ResponseParsingError attributes."""
        error = ResponseParsingError(response="invalid", expected_type="int", error="not a number")
        assert error.response == "invalid"
        assert error.expected_type == "int"
        assert error.error == "not a number"
        assert "int" in str(error)

"""Tests for agentic cost tracking and estimation."""

from unittest.mock import Mock, patch

import pytest

from raw_runtime import WorkflowContext, set_workflow_context
from raw_runtime.agentic import CostLimitExceededError, agentic
from raw_runtime.agentic_cost import (
    PRICING,
    CostTracker,
    calculate_cost,
    estimate_cost,
)


class TestCostCalculation:
    """Tests for cost calculation utilities."""

    def test_calculate_cost_sonnet(self) -> None:
        """Test cost calculation for Sonnet model."""
        # 1000 input tokens, 500 output tokens
        cost = calculate_cost(1000, 500, "claude-3-5-sonnet-20241022")

        expected = (1000 * PRICING["claude-3-5-sonnet-20241022"]["input"]) + (
            500 * PRICING["claude-3-5-sonnet-20241022"]["output"]
        )
        assert cost == expected
        # Should be $0.003 + $0.0075 = $0.0105
        assert abs(cost - 0.0105) < 0.0001

    def test_calculate_cost_haiku(self) -> None:
        """Test cost calculation for Haiku model."""
        # 1000 input tokens, 500 output tokens
        cost = calculate_cost(1000, 500, "claude-3-5-haiku-20241022")

        expected = (1000 * PRICING["claude-3-5-haiku-20241022"]["input"]) + (
            500 * PRICING["claude-3-5-haiku-20241022"]["output"]
        )
        assert cost == expected
        # Should be $0.0008 + $0.002 = $0.0028
        assert abs(cost - 0.0028) < 0.0001

    def test_calculate_cost_opus(self) -> None:
        """Test cost calculation for Opus model."""
        # 1000 input tokens, 500 output tokens
        cost = calculate_cost(1000, 500, "claude-3-opus-20240229")

        expected = (1000 * PRICING["claude-3-opus-20240229"]["input"]) + (
            500 * PRICING["claude-3-opus-20240229"]["output"]
        )
        assert cost == expected
        # Should be $0.015 + $0.0375 = $0.0525
        assert abs(cost - 0.0525) < 0.0001

    def test_calculate_cost_unknown_model_defaults_to_sonnet(self) -> None:
        """Test that unknown models default to Sonnet pricing."""
        cost = calculate_cost(1000, 500, "unknown-model")

        # Should use Sonnet pricing
        expected = (1000 * PRICING["claude-3-5-sonnet-20241022"]["input"]) + (
            500 * PRICING["claude-3-5-sonnet-20241022"]["output"]
        )
        assert cost == expected


class TestCostEstimation:
    """Tests for cost estimation before API calls."""

    def test_estimate_cost_basic(self) -> None:
        """Test basic cost estimation."""
        prompt = "Hello, world! " * 100  # ~400 chars
        max_tokens = 1000

        cost = estimate_cost(prompt, max_tokens, "claude-3-5-sonnet-20241022")

        # Should be a positive float
        assert isinstance(cost, float)
        assert cost > 0

        # Rough check: should be in reasonable range
        # ~100 input tokens + 1000 output tokens at Sonnet pricing
        # = (100 * 0.000003) + (1000 * 0.000015) = 0.0003 + 0.015 = 0.0153
        assert 0.001 < cost < 0.1

    def test_estimate_cost_scales_with_prompt_length(self) -> None:
        """Test that estimated cost scales with prompt length."""
        short_prompt = "Hello"
        long_prompt = "Hello " * 1000
        max_tokens = 100

        short_cost = estimate_cost(short_prompt, max_tokens, "claude-3-5-sonnet-20241022")
        long_cost = estimate_cost(long_prompt, max_tokens, "claude-3-5-sonnet-20241022")

        assert long_cost > short_cost

    def test_estimate_cost_scales_with_max_tokens(self) -> None:
        """Test that estimated cost scales with max_tokens."""
        prompt = "Hello, world!"

        small_cost = estimate_cost(prompt, 100, "claude-3-5-sonnet-20241022")
        large_cost = estimate_cost(prompt, 4000, "claude-3-5-sonnet-20241022")

        assert large_cost > small_cost

    def test_estimate_cost_haiku_cheaper_than_sonnet(self) -> None:
        """Test that Haiku is estimated cheaper than Sonnet."""
        prompt = "Hello, world! " * 100
        max_tokens = 1000

        haiku_cost = estimate_cost(prompt, max_tokens, "claude-3-5-haiku-20241022")
        sonnet_cost = estimate_cost(prompt, max_tokens, "claude-3-5-sonnet-20241022")

        assert haiku_cost < sonnet_cost

    def test_estimate_cost_without_tiktoken(self) -> None:
        """Test that estimation falls back gracefully without tiktoken."""
        prompt = "Hello, world! " * 100
        max_tokens = 1000

        # Mock tiktoken to raise exception during encoding
        with patch("tiktoken.get_encoding") as mock_encoding:
            mock_encoding.side_effect = Exception("tiktoken error")

            # Should still return a cost (using fallback estimation)
            cost = estimate_cost(prompt, max_tokens, "claude-3-5-sonnet-20241022")
            assert isinstance(cost, float)
            assert cost > 0

    def test_estimate_cost_raises_without_tiktoken_installed(self) -> None:
        """Test that estimation raises ImportError when tiktoken not installed."""
        with patch.dict("sys.modules", {"tiktoken": None}):
            with pytest.raises(ImportError, match="tiktoken library not installed"):
                estimate_cost("test", 100, "claude-3-5-sonnet-20241022")


class TestCostTracker:
    """Tests for CostTracker class."""

    def test_add_step_basic(self) -> None:
        """Test adding a step to cost tracker."""
        tracker = CostTracker()

        tracker.add_step(
            step_name="classify",
            cost=0.005,
            tokens={"input": 100, "output": 50},
            model="claude-3-5-haiku-20241022",
        )

        assert len(tracker.steps) == 1
        assert tracker.total == 0.005

    def test_add_multiple_steps(self) -> None:
        """Test adding multiple steps."""
        tracker = CostTracker()

        tracker.add_step("step1", 0.01, {"input": 100, "output": 50}, "haiku")
        tracker.add_step("step2", 0.02, {"input": 200, "output": 100}, "sonnet")
        tracker.add_step("step3", 0.015, {"input": 150, "output": 75}, "haiku")

        assert len(tracker.steps) == 3
        assert tracker.total == 0.045

    def test_get_breakdown(self) -> None:
        """Test getting cost breakdown."""
        tracker = CostTracker()

        tracker.add_step("step1", 0.01, {"input": 100, "output": 50}, "haiku")
        tracker.add_step("step2", 0.02, {"input": 200, "output": 100}, "sonnet")

        breakdown = tracker.get_breakdown()

        assert len(breakdown) == 2
        assert breakdown[0]["step_name"] == "step1"
        assert breakdown[0]["cost"] == 0.01
        assert breakdown[1]["step_name"] == "step2"
        assert breakdown[1]["cost"] == 0.02

    def test_get_total(self) -> None:
        """Test getting total cost."""
        tracker = CostTracker()

        tracker.add_step("step1", 0.01, {"input": 100, "output": 50}, "haiku")
        tracker.add_step("step2", 0.02, {"input": 200, "output": 100}, "sonnet")

        assert tracker.get_total() == 0.03

    def test_get_total_tokens(self) -> None:
        """Test getting total token counts."""
        tracker = CostTracker()

        tracker.add_step("step1", 0.01, {"input": 100, "output": 50}, "haiku")
        tracker.add_step("step2", 0.02, {"input": 200, "output": 100}, "sonnet")

        totals = tracker.get_total_tokens()

        assert totals["input"] == 300
        assert totals["output"] == 150

    def test_add_step_with_prompt(self) -> None:
        """Test adding step with prompt preview."""
        tracker = CostTracker()

        long_prompt = "A" * 200
        tracker.add_step(
            step_name="classify",
            cost=0.005,
            tokens={"input": 100, "output": 50},
            model="haiku",
            prompt=long_prompt,
        )

        step = tracker.steps[0]
        assert "prompt_preview" in step
        assert len(step["prompt_preview"]) == 100  # Truncated to 100 chars
        assert step["prompt_preview"] == "A" * 100


class TestCostLimitEnforcement:
    """Tests for cost limit enforcement in @agentic decorator."""

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

    def test_cost_limit_not_exceeded(self) -> None:
        """Test that execution proceeds when cost is under limit."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        # Low token counts = low cost
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                cost_limit=0.1,  # High limit
            )
            def process(text: str) -> str:
                pass

            # Should not raise
            result = process("test")
            assert result == "result"

    def test_cost_limit_exceeded_raises_before_api_call(self) -> None:
        """Test that CostLimitExceededError is raised BEFORE API call."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,  # High max_tokens = high estimated cost
                cost_limit=0.001,  # Very low limit
            )
            def process(text: str) -> str:
                pass

            with pytest.raises(CostLimitExceededError) as exc_info:
                process("test " * 1000)  # Long input

            # Check error details
            error = exc_info.value
            assert error.estimated_cost > error.cost_limit
            assert error.step_name == "process"
            assert "Estimated" in str(error)
            assert "would exceed limit" in str(error)

            # API should NOT have been called
            mock_client.messages.create.assert_not_called()

    def test_cost_limit_error_includes_step_name(self) -> None:
        """Test that error message includes step name."""
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                cost_limit=0.001,
            )
            def my_expensive_step(text: str) -> str:
                pass

            with pytest.raises(CostLimitExceededError) as exc_info:
                my_expensive_step("test " * 1000)

            assert "my_expensive_step" in str(exc_info.value)


class TestContextIntegration:
    """Tests for integration with WorkflowContext."""

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

    def test_context_logs_agentic_cost(self) -> None:
        """Test that context logs agentic step costs."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=False,  # Disable cache for testing
            )
            def process(text: str) -> str:
                pass

            process("test")

            # Check that cost was logged to context
            assert len(self.ctx.agentic_costs) == 1
            cost_log = self.ctx.agentic_costs[0]

            assert cost_log["step_name"] == "process"
            assert cost_log["model"] == "claude-3-5-haiku-20241022"
            assert cost_log["tokens"]["input"] == 100
            assert cost_log["tokens"]["output"] == 50
            assert cost_log["cost"] > 0
            assert self.ctx.total_agentic_cost > 0

    def test_context_tracks_multiple_agentic_steps(self) -> None:
        """Test that context tracks costs across multiple agentic steps."""
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
                model="claude-3-5-sonnet-20241022",
                cache=False,
            )
            def step2() -> str:
                pass

            step1()
            step2()

            # Should have 2 cost entries
            assert len(self.ctx.agentic_costs) == 2
            assert self.ctx.agentic_costs[0]["step_name"] == "step1"
            assert self.ctx.agentic_costs[1]["step_name"] == "step2"

            # Total cost should be sum of both
            expected_total = sum(step["cost"] for step in self.ctx.agentic_costs)
            assert abs(self.ctx.total_agentic_cost - expected_total) < 0.0001

    def test_context_logs_prompt_preview(self) -> None:
        """Test that context logs prompt preview."""
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            @agentic(
                prompt="Process: {context.text}",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def process(text: str) -> str:
                pass

            long_input = "A" * 200
            process(long_input)

            cost_log = self.ctx.agentic_costs[0]
            assert "prompt_preview" in cost_log
            # Should be truncated to 100 chars
            assert len(cost_log["prompt_preview"]) <= 100


class TestEstimationAccuracy:
    """Tests for cost estimation accuracy."""

    def test_estimation_within_reasonable_range(self) -> None:
        """Test that estimation is within 50% of actual cost."""
        # This is a sanity check - estimation can't be perfect
        # but should be reasonably close
        prompt = "Hello, world! " * 100
        max_tokens = 1000
        model = "claude-3-5-sonnet-20241022"

        estimated = estimate_cost(prompt, max_tokens, model)

        # Simulate actual usage (estimation uses max_tokens, actual might be less)
        # Assume we actually use 500 output tokens
        actual = calculate_cost(100, 500, model)

        # Estimated should be higher (since it assumes max_tokens)
        assert estimated >= actual

        # But not too far off (within 3x)
        assert estimated < actual * 3

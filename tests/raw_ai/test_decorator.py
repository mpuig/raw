"""Tests for raw_ai decorator."""

from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from raw_ai.decorator import agent


class SentimentResult(BaseModel):
    """Test result type for sentiment analysis."""

    score: float
    label: str


class SimpleResult(BaseModel):
    """Simple test result."""

    value: int


class TestAgentDecoratorMetadata:
    """Tests for @agent decorator metadata (no mocking needed)."""

    def test_decorator_marks_function(self) -> None:
        """Test that decorator adds metadata to function."""

        class TestWorkflow:
            @agent(result_type=SentimentResult)
            def analyze(self, text: str) -> SentimentResult:
                """Analyze sentiment."""
                ...

        assert hasattr(TestWorkflow.analyze, "_is_agent")
        assert TestWorkflow.analyze._is_agent is True
        assert TestWorkflow.analyze._result_type is SentimentResult

    def test_decorator_preserves_name(self) -> None:
        """Test that decorator preserves function name."""

        class TestWorkflow:
            @agent(result_type=SimpleResult)
            def my_analysis(self, x: int) -> SimpleResult:
                """Do analysis."""
                ...

        assert TestWorkflow.my_analysis.__name__ == "my_analysis"

    def test_decorator_stores_model(self) -> None:
        """Test that model parameter is stored."""

        class TestWorkflow:
            @agent(result_type=SimpleResult, model="gpt-4o")
            def analyze(self, text: str) -> SimpleResult:
                """Analyze."""
                ...

        assert TestWorkflow.analyze._model == "gpt-4o"

    def test_decorator_stores_none_model_by_default(self) -> None:
        """Test that model is None by default."""

        class TestWorkflow:
            @agent(result_type=SimpleResult)
            def analyze(self, text: str) -> SimpleResult:
                """Analyze."""
                ...

        assert TestWorkflow.analyze._model is None


class TestAgentDecoratorExecution:
    """Tests for @agent decorator execution (with mocking)."""

    @patch("pydantic_ai.Agent")
    def test_agent_uses_docstring_as_system_prompt(self, mock_agent_cls: MagicMock) -> None:
        """Test that docstring becomes system prompt."""
        mock_result = MagicMock()
        mock_result.data = SimpleResult(value=42)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run_sync.return_value = mock_result
        mock_agent_cls.return_value = mock_agent_instance

        class TestWorkflow:
            @agent(result_type=SimpleResult)
            def calculate(self, x: int) -> SimpleResult:
                """You are a calculator. Return the doubled value."""
                ...

        workflow = TestWorkflow()
        workflow.calculate(5)

        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args.kwargs
        assert call_kwargs["system_prompt"] == "You are a calculator. Return the doubled value."

    @patch("pydantic_ai.Agent")
    def test_agent_builds_user_message_from_args(self, mock_agent_cls: MagicMock) -> None:
        """Test that arguments become user message."""
        mock_result = MagicMock()
        mock_result.data = SimpleResult(value=10)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run_sync.return_value = mock_result
        mock_agent_cls.return_value = mock_agent_instance

        class TestWorkflow:
            @agent(result_type=SimpleResult)
            def process(self, text: str) -> SimpleResult:
                """Process the text."""
                ...

        workflow = TestWorkflow()
        workflow.process("Hello world")

        mock_agent_instance.run_sync.assert_called_once_with("Hello world")

    @patch("pydantic_ai.Agent")
    def test_agent_handles_multiple_args(self, mock_agent_cls: MagicMock) -> None:
        """Test multiple arguments in user message."""
        mock_result = MagicMock()
        mock_result.data = SimpleResult(value=10)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run_sync.return_value = mock_result
        mock_agent_cls.return_value = mock_agent_instance

        class TestWorkflow:
            @agent(result_type=SimpleResult)
            def process(self, text: str, count: int) -> SimpleResult:
                """Process text."""
                ...

        workflow = TestWorkflow()
        workflow.process("hello", 5)

        call_args = mock_agent_instance.run_sync.call_args[0][0]
        assert "hello" in call_args
        assert "count: 5" in call_args

    @patch("pydantic_ai.Agent")
    def test_agent_returns_result_data(self, mock_agent_cls: MagicMock) -> None:
        """Test that agent returns the result data."""
        expected = SentimentResult(score=0.9, label="positive")
        mock_result = MagicMock()
        mock_result.data = expected
        mock_agent_instance = MagicMock()
        mock_agent_instance.run_sync.return_value = mock_result
        mock_agent_cls.return_value = mock_agent_instance

        class TestWorkflow:
            @agent(result_type=SentimentResult)
            def analyze(self, text: str) -> SentimentResult:
                """Analyze sentiment."""
                ...

        workflow = TestWorkflow()
        result = workflow.analyze("I love this!")

        assert result == expected
        assert result.score == 0.9
        assert result.label == "positive"

    @patch("pydantic_ai.Agent")
    def test_agent_uses_retries(self, mock_agent_cls: MagicMock) -> None:
        """Test that retries parameter is passed."""
        mock_result = MagicMock()
        mock_result.data = SimpleResult(value=1)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run_sync.return_value = mock_result
        mock_agent_cls.return_value = mock_agent_instance

        class TestWorkflow:
            @agent(result_type=SimpleResult, retries=5)
            def analyze(self, text: str) -> SimpleResult:
                """Analyze."""
                ...

        workflow = TestWorkflow()
        workflow.analyze("test")

        call_kwargs = mock_agent_cls.call_args.kwargs
        assert call_kwargs["retries"] == 5

    @patch("pydantic_ai.Agent")
    def test_agent_default_retries(self, mock_agent_cls: MagicMock) -> None:
        """Test default retries value."""
        mock_result = MagicMock()
        mock_result.data = SimpleResult(value=1)
        mock_agent_instance = MagicMock()
        mock_agent_instance.run_sync.return_value = mock_result
        mock_agent_cls.return_value = mock_agent_instance

        class TestWorkflow:
            @agent(result_type=SimpleResult)
            def analyze(self, text: str) -> SimpleResult:
                """Analyze."""
                ...

        workflow = TestWorkflow()
        workflow.analyze("test")

        call_kwargs = mock_agent_cls.call_args.kwargs
        assert call_kwargs["retries"] == 3


class TestAgentWithContext:
    """Tests for @agent with workflow context."""

    @patch("pydantic_ai.Agent")
    def test_emits_step_result_when_context_present(self, mock_agent_cls: MagicMock) -> None:
        """Test that step results are emitted with context."""
        mock_result = MagicMock()
        mock_result.data = SimpleResult(value=42)
        mock_result.usage = {"total_tokens": 100}
        mock_agent_instance = MagicMock()
        mock_agent_instance.run_sync.return_value = mock_result
        mock_agent_cls.return_value = mock_agent_instance

        mock_context = MagicMock()

        class TestWorkflow:
            def __init__(self) -> None:
                self._context = mock_context

            @agent(result_type=SimpleResult)
            def analyze(self, text: str) -> SimpleResult:
                """Analyze."""
                ...

        workflow = TestWorkflow()
        workflow.analyze("test")

        mock_context.add_step_result.assert_called_once()
        step_result = mock_context.add_step_result.call_args[0][0]
        assert step_result.name == "analyze"
        assert step_result.result == {"value": 42}
        assert step_result.started_at is not None
        assert step_result.ended_at is not None

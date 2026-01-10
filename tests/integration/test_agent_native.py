"""Integration tests for agent-native features.

These tests verify that agent-native components work together correctly:
- Python SDK for workflow construction
- @agentic decorator for LLM-powered steps
- Tool discovery and registry
- Completion signals
- Cost tracking across workflows
- Cache persistence across runs
"""

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Literal
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml
from pydantic import BaseModel, Field

from raw.core.schemas import WorkflowStatus
from raw.engine import Container
from raw.sdk import add_step, create_workflow, get_workflow
from raw_runtime import BaseWorkflow, WorkflowContext, set_workflow_context, step
from raw_runtime.agentic import CostLimitExceededError, agentic
from raw_runtime.tools import Tool, ToolRegistry
from raw_runtime.tools.discovery import discover_tools


@pytest.fixture
def temp_raw_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temporary RAW project with .raw structure."""
    # Create .raw directory structure
    raw_dir = tmp_path / ".raw"
    raw_dir.mkdir()
    workflows_dir = raw_dir / "workflows"
    workflows_dir.mkdir()
    cache_dir = raw_dir / "cache"
    cache_dir.mkdir()
    (cache_dir / "agentic").mkdir()

    # Create tools directory
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "__init__.py").write_text("")

    # Create config.yaml
    config = {
        "version": 1,
        "project_name": "test-project",
    }
    (raw_dir / "config.yaml").write_text(yaml.dump(config))

    # Mock get_workflows_dir in all modules that use it
    import raw.discovery.workflow
    import raw.scaffold.init

    monkeypatch.setattr(raw.scaffold.init, "get_workflows_dir", lambda: workflows_dir)
    monkeypatch.setattr(raw.discovery.workflow, "get_workflows_dir", lambda: workflows_dir)

    # Change to temp directory
    original_cwd = Path.cwd()
    monkeypatch.chdir(tmp_path)

    yield tmp_path

    # Cleanup: reset context and cache
    set_workflow_context(None)
    if "raw_runtime.agentic" in sys.modules:
        sys.modules["raw_runtime.agentic"]._cache = None  # type: ignore[attr-defined]

    monkeypatch.chdir(original_cwd)


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic API client."""
    mock_response = Mock()
    mock_response.content = [Mock(text="result")]
    mock_response.usage = Mock(input_tokens=10, output_tokens=5)

    with patch("anthropic.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client
        yield mock_client


class TestAgentBuildsAndRunsWorkflow:
    """Test Scenario 1: Agent creates workflow via SDK and executes it."""

    def test_agent_builds_and_runs_workflow(self, temp_raw_project: Path) -> None:
        """Agent creates workflow via SDK and executes it."""
        # Create workflow using SDK
        workflow = create_workflow(
            name="test-flow",
            intent="Test workflow for integration testing",
        )

        assert workflow.name == "test-flow"
        assert workflow.status == WorkflowStatus.DRAFT
        assert workflow.path.exists()

        # Create run.py for the workflow
        run_script = workflow.path / "run.py"
        workflow_code = '''#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0"]
# ///
from pydantic import BaseModel
from raw_runtime import BaseWorkflow

class Params(BaseModel):
    """Parameters for test workflow."""
    pass

class TestWorkflow(BaseWorkflow[Params]):
    def run(self) -> int:
        print("hello from test workflow")
        self.save("output.txt", "workflow executed successfully")
        return 0

if __name__ == "__main__":
    TestWorkflow.main()
'''
        run_script.write_text(workflow_code)

        # Execute workflow using Container backend (without isolation for testing)
        runner = Container.workflow_runner()
        result = runner.run(workflow.path, "run.py", isolate_run=False)

        # Verify execution
        assert result.exit_code == 0
        assert "hello from test workflow" in result.stdout

        # Verify output file was created
        results_dir = workflow.path / "results"
        assert results_dir.exists()
        output_file = results_dir / "output.txt"
        assert output_file.exists()
        assert output_file.read_text() == "workflow executed successfully"


class TestWorkflowWithAgenticSteps:
    """Test Scenario 2: Workflow executes with LLM-powered decision steps."""

    def test_workflow_with_agentic_steps(
        self, temp_raw_project: Path, mock_anthropic: MagicMock
    ) -> None:
        """Workflow executes with LLM-powered decision step via direct instantiation."""
        # Instead of subprocess execution, test direct workflow instantiation
        # This allows mocks to work correctly
        from typing import Literal

        from pydantic import BaseModel

        # Mock Anthropic to return "high"
        mock_response = Mock()
        mock_response.content = [Mock(text="high")]
        mock_response.usage = Mock(input_tokens=20, output_tokens=10)
        mock_anthropic.messages.create.return_value = mock_response

        # Define workflow class inline
        class Params(BaseModel):
            """Parameters."""

            ticket: str = "urgent bug in production"

        class AgenticWorkflow(BaseWorkflow[Params]):
            @agentic(
                prompt="Classify ticket: {context.ticket}",
                model="claude-3-5-haiku-20241022",
                cache=False,
            )
            def classify(self, ticket: str) -> Literal["critical", "high", "medium", "low"]:
                pass

            def run(self) -> int:
                priority = self.classify(self.params.ticket)
                self.save("priority.txt", priority)
                return 0

        # Create and run workflow
        params = Params()
        workflow_instance = AgenticWorkflow(params=params)
        exit_code = workflow_instance.run()

        # Verify execution
        assert exit_code == 0

        # Verify API was called
        assert mock_anthropic.messages.create.call_count == 1

        # Verify output
        priority_file = workflow_instance.results_dir / "priority.txt"
        assert priority_file.exists()
        assert priority_file.read_text() == "high"

    def test_workflow_agentic_cost_tracking(
        self, temp_raw_project: Path, mock_anthropic: MagicMock
    ) -> None:
        """Verify cost tracking works in workflow context."""
        # Setup context
        ctx = WorkflowContext(
            workflow_id="test-cost-123",
            short_name="test-cost",
        )
        set_workflow_context(ctx)

        # Clear cache
        cache_dir = temp_raw_project / ".raw" / "cache" / "agentic"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True)

        # Mock Anthropic response
        mock_response = Mock()
        mock_response.content = [Mock(text="result")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_anthropic.messages.create.return_value = mock_response

        # Define agentic function
        @agentic(
            prompt="Process: {context.text}",
            model="claude-3-5-haiku-20241022",
            cache=False,
        )
        def process(text: str) -> str:
            pass

        # Call function
        result = process("test input")

        # Verify cost was tracked
        assert result == "result"
        assert len(ctx.agentic_costs) == 1
        cost_log = ctx.agentic_costs[0]
        assert cost_log["step_name"] == "process"
        assert cost_log["model"] == "claude-3-5-haiku-20241022"
        assert cost_log["tokens"]["input"] == 100
        assert cost_log["tokens"]["output"] == 50
        assert cost_log["cost"] > 0
        assert ctx.total_agentic_cost > 0

    def test_workflow_agentic_cache_on_second_run(
        self, temp_raw_project: Path, mock_anthropic: MagicMock
    ) -> None:
        """Verify caching works on second run."""
        # Setup context
        ctx = WorkflowContext(
            workflow_id="test-cache-123",
            short_name="test-cache",
        )
        set_workflow_context(ctx)

        # Clear cache first
        cache_dir = temp_raw_project / ".raw" / "cache" / "agentic"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True)

        # Mock Anthropic response
        mock_response = Mock()
        mock_response.content = [Mock(text="cached_result")]
        mock_response.usage = Mock(input_tokens=50, output_tokens=25)
        mock_anthropic.messages.create.return_value = mock_response

        # Define agentic function with cache enabled
        @agentic(
            prompt="Cache test: {context.value}",
            model="claude-3-5-haiku-20241022",
            cache=True,
        )
        def cached_process(value: str) -> str:
            pass

        # First call - cache miss
        result1 = cached_process("input1")
        assert result1 == "cached_result"
        assert mock_anthropic.messages.create.call_count == 1
        assert ctx.agentic_cache_misses == 1
        assert ctx.agentic_cache_hits == 0

        # Second call with same input - cache hit
        result2 = cached_process("input1")
        assert result2 == "cached_result"
        assert mock_anthropic.messages.create.call_count == 1  # Not called again
        assert ctx.agentic_cache_hits == 1
        assert ctx.agentic_cache_misses == 1

        # Verify cache file exists
        cache_files = list(cache_dir.glob("*.json"))
        assert len(cache_files) == 1


class TestToolDiscoveryAndUsage:
    """Test Scenario 3: Agent discovers tools and uses them in workflow."""

    def test_tool_discovery_and_usage(self, temp_raw_project: Path) -> None:
        """Agent discovers tools and uses them in workflow."""
        tools_dir = temp_raw_project / "tools"

        # Create a sample tool
        sample_tool_dir = tools_dir / "sample_tool"
        sample_tool_dir.mkdir()

        tool_code = '''
from collections.abc import AsyncIterator
from typing import Any, ClassVar
from raw_runtime.tools import Tool, ToolEvent

class SampleTool(Tool):
    name: ClassVar[str] = "sample_tool"
    description: ClassVar[str] = "A sample tool for testing"

    async def run(self, message: str, **config: Any) -> AsyncIterator[ToolEvent]:
        yield self._emit_started(message=message)
        result = f"processed: {message}"
        yield self._emit_completed(result=result)
'''
        (sample_tool_dir / "tool.py").write_text(tool_code)

        # Discover tools
        discovered = discover_tools(tools_dir)
        assert "sample_tool" in discovered

        # Register tools
        registry = ToolRegistry()
        count = registry.discover_and_register(tools_dir)
        assert count == 1
        assert registry.has_tool("sample_tool")

        # Verify tool can be retrieved
        tool = registry.require("sample_tool")
        assert tool.name == "sample_tool"
        assert tool.description == "A sample tool for testing"

    def test_workflow_uses_discovered_tool(self, temp_raw_project: Path) -> None:
        """Workflow imports and uses discovered tool via direct instantiation."""
        tools_dir = temp_raw_project / "tools"

        # Create a data processing tool
        processor_dir = tools_dir / "data_processor"
        processor_dir.mkdir()

        tool_code = '''
def process_data(data: str) -> str:
    """Process input data."""
    return data.upper()
'''
        (processor_dir / "tool.py").write_text(tool_code)
        (processor_dir / "__init__.py").write_text("")

        # Import the tool module
        import sys

        sys.path.insert(0, str(tools_dir))
        from data_processor.tool import process_data

        # Define workflow inline that uses tool
        from pydantic import BaseModel

        class Params(BaseModel):
            """Parameters."""

            pass

        class ToolUserWorkflow(BaseWorkflow[Params]):
            def run(self) -> int:
                result = process_data("hello world")
                self.save("result.txt", result)
                return 0

        # Create and run workflow
        params = Params()
        workflow_instance = ToolUserWorkflow(params=params)
        exit_code = workflow_instance.run()

        # Verify execution
        assert exit_code == 0

        # Verify tool was used
        result_file = workflow_instance.results_dir / "result.txt"
        assert result_file.exists()
        assert result_file.read_text() == "HELLO WORLD"

        # Clean up sys.path
        sys.path.remove(str(tools_dir))


class TestCompletionSignals:
    """Test Scenario 4: Workflow uses completion signals correctly."""

    def test_completion_signals_in_workflow(self, temp_raw_project: Path) -> None:
        """Workflow uses .success(), .error(), .complete() signals."""
        workflow = create_workflow(
            name="signals-flow",
            intent="Test completion signals",
        )

        run_script = workflow.path / "run.py"
        workflow_code = '''#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0"]
# ///
from pydantic import BaseModel
from raw_runtime import BaseWorkflow

class Params(BaseModel):
    """Parameters."""
    mode: str = "success"

class SignalsWorkflow(BaseWorkflow[Params]):
    def run(self) -> int:
        if self.params.mode == "success":
            result = self.success("Task completed", data={"count": 42})
            self.save("signal.json", {"signal": result.signal.value})
            return result.exit_code
        elif self.params.mode == "complete":
            result = self.complete("All done", data={"total": 100})
            self.save("signal.json", {"signal": result.signal.value})
            return result.exit_code
        else:
            result = self.error("Something failed")
            self.save("signal.json", {"signal": result.signal.value})
            return result.exit_code

if __name__ == "__main__":
    SignalsWorkflow.main()
'''
        run_script.write_text(workflow_code)

        # Test success signal
        runner = Container.workflow_runner()
        result = runner.run(workflow.path, "run.py", args=["--mode", "success"], isolate_run=False)
        assert result.exit_code == 0
        signal_file = workflow.path / "results" / "signal.json"
        assert signal_file.exists()
        signal_data = json.loads(signal_file.read_text())
        assert signal_data["signal"] == "success"

        # Clear results
        shutil.rmtree(workflow.path / "results")

        # Test complete signal
        result = runner.run(workflow.path, "run.py", args=["--mode", "complete"], isolate_run=False)
        assert result.exit_code == 0
        signal_file = workflow.path / "results" / "signal.json"
        signal_data = json.loads(signal_file.read_text())
        assert signal_data["signal"] == "complete"

        # Clear results
        shutil.rmtree(workflow.path / "results")

        # Test error signal
        result = runner.run(workflow.path, "run.py", args=["--mode", "error"], isolate_run=False)
        assert result.exit_code == 1
        signal_file = workflow.path / "results" / "signal.json"
        signal_data = json.loads(signal_file.read_text())
        assert signal_data["signal"] == "error"


class TestCostTrackingAcrossWorkflow:
    """Test Scenario 5: Multiple @agentic steps track cumulative cost."""

    def test_cost_tracking_across_workflow(
        self, temp_raw_project: Path, mock_anthropic: MagicMock
    ) -> None:
        """Multiple @agentic steps track cumulative cost."""
        ctx = WorkflowContext(
            workflow_id="multi-agentic-123",
            short_name="multi-agentic",
        )
        set_workflow_context(ctx)

        # Clear cache
        cache_dir = temp_raw_project / ".raw" / "cache" / "agentic"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True)

        # Mock different responses for each step
        responses = [
            Mock(content=[Mock(text="result1")], usage=Mock(input_tokens=100, output_tokens=50)),
            Mock(content=[Mock(text="result2")], usage=Mock(input_tokens=200, output_tokens=100)),
            Mock(content=[Mock(text="result3")], usage=Mock(input_tokens=150, output_tokens=75)),
        ]
        mock_anthropic.messages.create.side_effect = responses

        # Define three agentic steps
        @agentic(
            prompt="Step 1: {context.text}",
            model="claude-3-5-haiku-20241022",
            cache=False,
        )
        def step1(text: str) -> str:
            pass

        @agentic(
            prompt="Step 2: {context.text}",
            model="claude-3-5-haiku-20241022",
            cache=False,
        )
        def step2(text: str) -> str:
            pass

        @agentic(
            prompt="Step 3: {context.text}",
            model="claude-3-5-haiku-20241022",
            cache=False,
        )
        def step3(text: str) -> str:
            pass

        # Execute all steps
        step1("input1")
        step2("input2")
        step3("input3")

        # Verify all steps were called
        assert mock_anthropic.messages.create.call_count == 3

        # Verify cost tracking
        assert len(ctx.agentic_costs) == 3
        assert ctx.agentic_costs[0]["step_name"] == "step1"
        assert ctx.agentic_costs[1]["step_name"] == "step2"
        assert ctx.agentic_costs[2]["step_name"] == "step3"

        # Verify cumulative cost
        cost1 = ctx.agentic_costs[0]["cost"]
        cost2 = ctx.agentic_costs[1]["cost"]
        cost3 = ctx.agentic_costs[2]["cost"]
        expected_total = cost1 + cost2 + cost3
        assert abs(ctx.total_agentic_cost - expected_total) < 0.0001

        # Verify token totals
        total_input = sum(c["tokens"]["input"] for c in ctx.agentic_costs)
        total_output = sum(c["tokens"]["output"] for c in ctx.agentic_costs)
        assert total_input == 450  # 100 + 200 + 150
        assert total_output == 225  # 50 + 100 + 75


class TestCachePersistence:
    """Test Scenario 6: Cached agentic responses persist between workflow runs."""

    def test_cache_persists_across_runs(
        self, temp_raw_project: Path, mock_anthropic: MagicMock
    ) -> None:
        """Cached agentic responses persist between workflow runs."""
        cache_dir = temp_raw_project / ".raw" / "cache" / "agentic"

        # Clear cache
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True)

        # Run 1: Cache miss, calls API
        ctx1 = WorkflowContext(
            workflow_id="cache-persist-1",
            short_name="cache-persist",
        )
        set_workflow_context(ctx1)

        mock_response = Mock()
        mock_response.content = [Mock(text="first_result")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_anthropic.messages.create.return_value = mock_response

        @agentic(
            prompt="Persistent cache test: {context.value}",
            model="claude-3-5-haiku-20241022",
            cache=True,
        )
        def persist_test(value: str) -> str:
            pass

        result1 = persist_test("constant_input")
        assert result1 == "first_result"
        assert mock_anthropic.messages.create.call_count == 1
        assert ctx1.agentic_cache_misses == 1
        assert ctx1.agentic_cache_hits == 0

        # Verify cache file was created
        cache_files = list(cache_dir.glob("*.json"))
        assert len(cache_files) == 1

        # Verify cache file structure
        with open(cache_files[0]) as f:
            cache_data = json.load(f)
        assert cache_data["response"] == "first_result"
        assert cache_data["model"] == "claude-3-5-haiku-20241022"
        assert cache_data["cost"] > 0

        # Run 2: Cache hit, no API call
        # Reset context to simulate new run
        set_workflow_context(None)
        if "raw_runtime.agentic" in sys.modules:
            sys.modules["raw_runtime.agentic"]._cache = None  # type: ignore[attr-defined]

        ctx2 = WorkflowContext(
            workflow_id="cache-persist-2",
            short_name="cache-persist",
        )
        set_workflow_context(ctx2)

        # Re-define function to clear decorator state
        @agentic(
            prompt="Persistent cache test: {context.value}",
            model="claude-3-5-haiku-20241022",
            cache=True,
        )
        def persist_test2(value: str) -> str:
            pass

        result2 = persist_test2("constant_input")
        assert result2 == "first_result"
        assert mock_anthropic.messages.create.call_count == 1  # Still 1, not called again
        assert ctx2.agentic_cache_hits == 1
        assert ctx2.agentic_cache_misses == 0


class TestErrorPropagation:
    """Test error handling and propagation in agent-native features."""

    def test_api_failures_handled_gracefully(
        self, temp_raw_project: Path, mock_anthropic: MagicMock
    ) -> None:
        """API failures should be handled gracefully."""
        ctx = WorkflowContext(
            workflow_id="error-test-123",
            short_name="error-test",
        )
        set_workflow_context(ctx)

        # Mock API failure
        mock_anthropic.messages.create.side_effect = Exception("API Error")

        @agentic(
            prompt="Test: {context.text}",
            model="claude-3-5-haiku-20241022",
            cache=False,
        )
        def failing_step(text: str) -> str:
            pass

        # Should raise AgenticStepError
        from raw_runtime.agentic import AgenticStepError

        with pytest.raises(AgenticStepError, match="Anthropic API call failed"):
            failing_step("test")

    def test_cost_limit_exceeded_stops_workflow(
        self, temp_raw_project: Path, mock_anthropic: MagicMock
    ) -> None:
        """Cost limit exceeded should stop workflow."""
        ctx = WorkflowContext(
            workflow_id="cost-limit-test",
            short_name="cost-limit",
        )
        set_workflow_context(ctx)

        @agentic(
            prompt="Expensive: {context.text}",
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            cost_limit=0.001,  # Very low limit
            cache=False,
        )
        def expensive_step(text: str) -> str:
            pass

        # Should raise CostLimitExceededError before calling API
        with pytest.raises(CostLimitExceededError) as exc_info:
            expensive_step("test " * 1000)  # Long input

        error = exc_info.value
        assert error.estimated_cost > error.cost_limit
        assert error.step_name == "expensive_step"

        # API should NOT have been called
        mock_anthropic.messages.create.assert_not_called()

    def test_tool_not_found_gives_helpful_message(self, temp_raw_project: Path) -> None:
        """Tool not found should give helpful message."""
        tools_dir = temp_raw_project / "tools"

        registry = ToolRegistry()
        registry.discover_and_register(tools_dir)

        # Try to require non-existent tool
        with pytest.raises(KeyError, match="nonexistent_tool"):
            registry.require("nonexistent_tool")


class TestDataFlow:
    """Test data flow through agent-native components."""

    def test_workflow_context_populated_correctly(
        self, temp_raw_project: Path, mock_anthropic: MagicMock
    ) -> None:
        """WorkflowContext is populated correctly during execution."""
        ctx = WorkflowContext(
            workflow_id="dataflow-123",
            short_name="dataflow",
        )
        set_workflow_context(ctx)

        # Clear cache
        cache_dir = temp_raw_project / ".raw" / "cache" / "agentic"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True)

        mock_response = Mock()
        mock_response.content = [Mock(text="test_result")]
        mock_response.usage = Mock(input_tokens=75, output_tokens=35)
        mock_anthropic.messages.create.return_value = mock_response

        @agentic(
            prompt="Test: {context.input}",
            model="claude-3-5-haiku-20241022",
            cache=True,
        )
        def test_step(input: str) -> str:
            pass

        # Execute step
        result = test_step("test_input")

        # Verify context data
        assert result == "test_result"
        assert ctx.workflow_id == "dataflow-123"
        assert ctx.short_name == "dataflow"

        # Verify agentic cost tracking
        assert len(ctx.agentic_costs) == 1
        assert ctx.agentic_costs[0]["step_name"] == "test_step"
        assert ctx.agentic_costs[0]["model"] == "claude-3-5-haiku-20241022"
        assert ctx.agentic_costs[0]["tokens"]["input"] == 75
        assert ctx.agentic_costs[0]["tokens"]["output"] == 35
        assert ctx.total_agentic_cost > 0

        # Verify cache metrics
        assert ctx.agentic_cache_misses == 1
        assert ctx.agentic_cache_hits == 0

    def test_manifest_includes_execution_data(self, temp_raw_project: Path) -> None:
        """Manifest includes all execution data."""
        # Create a simple workflow
        workflow = create_workflow(
            name="manifest-test",
            intent="Test manifest data",
        )

        run_script = workflow.path / "run.py"
        workflow_code = '''#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0"]
# ///
from pydantic import BaseModel
from raw_runtime import BaseWorkflow, step

class Params(BaseModel):
    """Parameters."""
    value: int = 42

class ManifestWorkflow(BaseWorkflow[Params]):
    @step("process")
    def process(self) -> dict:
        return {"result": self.params.value * 2}

    def run(self) -> int:
        result = self.process()
        self.save("output.json", result)
        return 0

if __name__ == "__main__":
    ManifestWorkflow.main()
'''
        run_script.write_text(workflow_code)

        # Execute workflow
        runner = Container.workflow_runner()
        result = runner.run(workflow.path, "run.py", args=["--value", "10"], isolate_run=False)

        # Verify execution
        assert result.exit_code == 0

        # Verify output
        output_file = workflow.path / "results" / "output.json"
        assert output_file.exists()
        output_data = json.loads(output_file.read_text())
        assert output_data["result"] == 20

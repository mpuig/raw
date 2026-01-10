# RAW Examples

This directory contains example workflows demonstrating RAW's capabilities.

## Agent-Native Examples

These examples demonstrate the agent-native architecture - workflows designed to be built and executed by AI agents.

### Layer 1: Agents as Builders

**[agent_built_workflow.py](agent_built_workflow.py)** - Agent constructs workflows using SDK

Demonstrates how an agent can programmatically build workflows from natural language requirements:

```bash
python examples/agent_built_workflow.py
```

Key concepts:
- Using SDK to create workflows programmatically
- Composing steps from tools and inline code
- Inspecting and validating workflows before execution
- Agent reasoning about user requirements

Shows two examples:
1. ETL pipeline (extract, transform, load)
2. Conditional alerting workflow with branching logic

### Layer 2: Selective Agent-in-Loop

**[edge_case_handler.py](edge_case_handler.py)** - Using @agentic for classification

Demonstrates cost-effective agent-in-loop pattern:

```bash
python examples/edge_case_handler.py --ticket-id TKT-12345
```

Key concepts:
- Most steps are deterministic (free, fast)
- One step uses LLM reasoning (@agentic decorator)
- Classification decision affects deterministic routing
- Cost tracking and limits

Pattern:
1. Fetch ticket data (deterministic, $0)
2. Classify urgency with LLM (agentic, ~$0.001)
3. Route based on classification (deterministic, $0)

Total cost: ~$0.001 per execution

**[hybrid_workflow.py](hybrid_workflow.py)** - Mixing deterministic and agentic steps

Demonstrates best practices for cost-effective workflows:

```bash
python examples/hybrid_workflow.py --article-url "https://example.com/article"
```

Key concepts:
- Deterministic steps for data operations (HTTP, parsing)
- Agentic steps for semantic tasks (summarization, topic extraction)
- Response caching for repeated executions
- Detailed cost breakdown and tracking
- Model selection (haiku for simple tasks)
- Token limits to control costs

Pattern:
1. Fetch article HTML (deterministic, $0)
2. Extract text (deterministic, $0)
3. Summarize with LLM (agentic, ~$0.001, cached)
4. Extract topics with LLM (agentic, ~$0.0005, cached)
5. Analyze sentiment with LLM (agentic, ~$0.0003, cached)

Total cost: ~$0.002 per unique article, ~$0 for cached repeats

## Other Examples

**[sentiment_analysis.py](sentiment_analysis.py)** - Text sentiment analysis workflow

Basic workflow demonstrating step tracking and result persistence.

**[sdk_workflow_construction.py](sdk_workflow_construction.py)** - SDK usage patterns

More examples of programmatic workflow construction with the Python SDK.

**[inbound_call_workflow.py](inbound_call_workflow.py)** - Call center automation

Complex workflow demonstrating tool integration and multi-step processing.

**[solution-callcenter/](solution-callcenter/)** - Complete call center solution

Full-featured example with multiple workflows, tools, and configurations.

## Running Examples

All examples are executable Python scripts with PEP 723 inline dependencies:

```bash
# Run directly
python examples/hybrid_workflow.py --article-url "https://example.com"

# Or via uv (recommended)
uv run examples/hybrid_workflow.py --article-url "https://example.com"
```

## Agent-Native Architecture

RAW's agent-native design has two layers:

### Layer 1: Agents as Builders

Agents can use the SDK to construct workflows programmatically:

```python
from raw.sdk import create_workflow, add_step

workflow = create_workflow(name="data-pipeline", intent="ETL workflow")
add_step(workflow, name="extract", tool="http_client", config={...})
add_step(workflow, name="transform", code="def transform(data): ...")
add_step(workflow, name="load", tool="database", config={...})
```

Benefits:
- Natural language to workflow translation
- Automatic tool discovery
- Validation before execution
- Version control of workflow definitions

### Layer 2: Selective Agent-in-Loop

Within workflows, use @agentic decorator for steps requiring LLM reasoning:

```python
from raw_runtime import BaseWorkflow, step, agentic

class MyWorkflow(BaseWorkflow[Params]):
    @step("fetch")
    def fetch_data(self):
        return fetch_from_api()  # Deterministic, free

    @step("classify")
    @agentic(
        prompt="Classify: {context.data}",
        model="claude-3-5-haiku-20241022",
        max_tokens=10,
        cost_limit=0.01
    )
    def classify(self, data):
        pass  # LLM reasoning, ~$0.001

    @step("route")
    def route(self, classification):
        return route_by_rules(classification)  # Deterministic, free
```

Benefits:
- Cost-effective (only pay for reasoning steps)
- Fast execution (deterministic steps are instant)
- Predictable costs (limits and tracking)
- Caching (avoid repeated LLM calls)

## Cost Management

The hybrid examples demonstrate cost management best practices:

1. **Model Selection**: Use cheaper models for simple tasks
   - `claude-3-5-haiku-20241022` for classification/extraction (~10x cheaper)
   - `claude-3-5-sonnet-20241022` for complex reasoning

2. **Token Limits**: Set max_tokens to minimum needed
   - Classification: 10 tokens
   - Extraction: 50 tokens
   - Summarization: 100 tokens
   - Complex: 1000+ tokens

3. **Cost Limits**: Set per-step limits to prevent overruns
   ```python
   @agentic(cost_limit=0.01)  # Raise error if estimate exceeds $0.01
   ```

4. **Caching**: Enable for idempotent operations
   ```python
   @agentic(cache=True, cache_ttl=604800)  # Cache for 7 days
   ```

5. **Cost Tracking**: Monitor actual costs per execution
   ```python
   total_cost = sum(step.get("cost", 0) for step in context._steps.values())
   ```

## Best Practices

1. **Use deterministic code by default** - Only use @agentic when LLM reasoning adds value

2. **Start with cheaper models** - Use haiku for simple tasks, upgrade only if needed

3. **Set token limits** - Prevent unbounded token generation

4. **Enable caching** - Especially for idempotent operations

5. **Track costs** - Monitor and optimize based on actual usage

6. **Test with --dry-run** - Validate workflows before real execution

7. **Use SDK for construction** - Let agents build workflows from requirements

## Further Reading

- [CLAUDE.md](../CLAUDE.md) - Development guide for agents
- [AGENTS.md](../AGENTS.md) - Agent integration instructions
- [docs/agent-native-guide.md](../docs/agent-native-guide.md) - Detailed architecture guide

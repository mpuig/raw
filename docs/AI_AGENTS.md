# RAW AI Agents

The `raw_ai` package provides LLM-powered workflow steps using PydanticAI for structured output. This enables workflows to include AI-driven analysis, generation, and decision-making steps.

## Installation

Install the AI dependencies:

```bash
uv add raw[ai]
```

This adds `pydantic-ai` and its dependencies.

## Quick Start

```python
from pydantic import BaseModel
from raw_ai import agent
from raw_runtime import BaseWorkflow

class Sentiment(BaseModel):
    score: float
    label: str
    reasoning: str

class MyWorkflow(BaseWorkflow):
    @agent(result_type=Sentiment)
    def analyze(self, text: str) -> Sentiment:
        '''You are a sentiment analyst. Analyze the text.'''
        ...

    def run(self) -> int:
        result = self.analyze("I love this product!")
        self.save("sentiment.json", result.model_dump())
        return 0
```

## The @agent Decorator

The `@agent` decorator transforms a method into an LLM-powered step:

- **Docstring → System Prompt**: The method's docstring becomes the LLM's system prompt
- **Arguments → User Message**: Method arguments are formatted as the user message
- **Return Type → Structured Output**: The `result_type` Pydantic model defines the output schema

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `result_type` | `type[BaseModel]` | Required | Pydantic model for structured output |
| `model` | `str` | `"gpt-4o-mini"` | Model name (e.g., "gpt-4o", "claude-3-5-sonnet-latest") |
| `tools` | `list[Callable]` | `None` | Functions the agent can call |
| `retries` | `int` | `3` | Retries on validation failure |
| `temperature` | `float` | `None` | Sampling temperature (0.0-2.0) |

### Example with All Parameters

```python
from tools.web_scraper import fetch_url

class Analysis(BaseModel):
    summary: str
    key_points: list[str]
    confidence: float

class ResearchWorkflow(BaseWorkflow):
    @agent(
        result_type=Analysis,
        model="gpt-4o",
        tools=[fetch_url],
        retries=5,
        temperature=0.3,
    )
    def research_topic(self, topic: str, depth: str = "medium") -> Analysis:
        '''You are a research analyst. Analyze the given topic thoroughly.
        Use the fetch_url tool to gather information from the web.
        Be precise and cite your sources.'''
        ...
```

## Model Configuration

The `get_model()` function automatically detects the provider from the model name:

| Prefix | Provider | Example |
|--------|----------|---------|
| `gpt-*`, `o1-*` | OpenAI | `gpt-4o`, `o1-preview` |
| `claude-*` | Anthropic | `claude-3-5-sonnet-latest` |
| `llama-*`, `mixtral-*` | Groq | `llama-3.1-70b-versatile` |

### Environment Variables

Set the appropriate API key for your provider:

```bash
export OPENAI_API_KEY="sk-..."       # For OpenAI models
export ANTHROPIC_API_KEY="sk-ant-..." # For Anthropic models
export GROQ_API_KEY="gsk_..."         # For Groq models
```

## Using Tools

Agent steps can call tools (functions) to perform actions:

```python
def search_database(query: str, limit: int = 10) -> list[dict]:
    """Search the database for matching records.

    Args:
        query: Search query string
        limit: Maximum results to return

    Returns:
        List of matching records
    """
    # Implementation...
    return results

class QueryWorkflow(BaseWorkflow):
    @agent(result_type=QueryResult, tools=[search_database])
    def answer_question(self, question: str) -> QueryResult:
        '''Answer questions using the database search tool.'''
        ...
```

### Tool Conversion

Use `to_ai_tool()` to inspect how a function will be exposed to the LLM:

```python
from raw_ai import to_ai_tool

tool_def = to_ai_tool(search_database)
print(tool_def)
# {
#   "name": "search_database",
#   "description": "Search the database for matching records.",
#   "parameters": {
#     "type": "object",
#     "properties": {
#       "query": {"type": "string", "description": "Search query string"},
#       "limit": {"type": "integer", "description": "Maximum results to return"}
#     },
#     "required": ["query"]
#   },
#   "function": <function search_database>
# }
```

## Workflow Integration

Agent steps integrate with RAW's workflow context:

- Results are tracked in the workflow manifest
- Step timing is recorded
- Errors are handled with retry logic

### With @step Tracking

Use `@agent_step` to combine agent behavior with explicit step tracking:

```python
from raw_ai.decorator import agent_step

class MyWorkflow(BaseWorkflow):
    @agent_step("sentiment_analysis", result_type=Sentiment)
    def analyze(self, text: str) -> Sentiment:
        '''Analyze sentiment.'''
        ...
```

## Best Practices

### 1. Write Clear System Prompts

The docstring is your system prompt. Be specific about:
- The agent's role and expertise
- Expected output format
- Any constraints or guidelines

```python
@agent(result_type=Review)
def review_code(self, code: str) -> Review:
    '''You are a senior Python developer performing code review.

    Focus on:
    - Code correctness and bugs
    - Performance issues
    - Security vulnerabilities
    - Adherence to PEP 8 style

    Be constructive and specific in your feedback.'''
    ...
```

### 2. Use Precise Result Types

Define Pydantic models with clear field descriptions:

```python
class CodeReview(BaseModel):
    severity: Literal["critical", "major", "minor", "info"]
    issues: list[str] = Field(description="List of specific issues found")
    suggestions: list[str] = Field(description="Improvement suggestions")
    approved: bool = Field(description="Whether the code is ready for merge")
```

### 3. Handle Failures Gracefully

Agent steps can fail due to:
- API errors
- Validation failures (output doesn't match schema)
- Rate limiting

Use the `retries` parameter and handle exceptions:

```python
@agent(result_type=Analysis, retries=5)
def analyze(self, data: str) -> Analysis:
    '''Analyze the data.'''
    ...

def run(self) -> int:
    try:
        result = self.analyze(data)
    except Exception as e:
        self.console.print(f"[red]Analysis failed: {e}[/]")
        return 1
    return 0
```

## API Reference

### raw_ai.agent

```python
def agent(
    result_type: type[T],
    model: str | None = None,
    tools: list[Callable] | None = None,
    retries: int = 3,
    temperature: float | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]
```

### raw_ai.to_ai_tool

```python
def to_ai_tool(func: Callable) -> dict[str, Any]
```

Converts a Python function to a PydanticAI tool definition.

### raw_ai.get_model

```python
def get_model(
    model: str | None = None,
    provider: ModelProvider | None = None,
) -> str
```

Returns a model string for PydanticAI (e.g., `"openai:gpt-4o"`).

### raw_ai.AIConfig

```python
class AIConfig(BaseModel):
    provider: Literal["openai", "anthropic", "groq", "ollama"]
    model: str
    api_key: str | None
    base_url: str | None
    temperature: float
    max_tokens: int | None
    timeout: float
```

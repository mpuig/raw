# Agent-Native Architecture Guide

RAW implements a two-layer agent-native architecture that separates construction from execution:

1. **Layer 1: Programmatic Construction** - Agents build workflows via Python SDK
2. **Layer 2: Selective Agentic Steps** - Workflows invoke LLM for specific decisions

This guide shows when and how to use each layer.

## When to Use the SDK vs CLI

### Use CLI When:
- Building one-off workflows manually
- Prototyping or experimenting
- User is directly creating workflows

### Use SDK When:
- Agent is constructing workflows programmatically
- Building workflows from user requests
- Implementing workflow generators or templates
- Need to validate or inspect workflows before running

## SDK Examples

### Creating a Workflow

```python
from raw.sdk import create_workflow, add_step

# Create workflow from user request
workflow = create_workflow(
    name="email-report",
    intent="Fetch data and email daily report"
)

# Add steps with configuration
add_step(
    workflow,
    name="fetch_data",
    tool="api_client",
    config={"endpoint": "/metrics", "date": "today"}
)

add_step(
    workflow,
    name="generate_report",
    tool="report_generator",
    config={"format": "pdf"}
)

add_step(
    workflow,
    name="send_email",
    tool="email_sender",
    config={"to": "team@company.com", "subject": "Daily Report"}
)

print(f"Created workflow: {workflow.id}")
```

### Managing Workflows

```python
from raw.sdk import list_workflows, get_workflow, update_workflow

# List all workflows
workflows = list_workflows()
for wf in workflows:
    print(f"{wf.id}: {wf.name} ({wf.status})")

# Get specific workflow
workflow = get_workflow("email-report")
if workflow:
    print(f"Found: {workflow.name}")

# Update metadata
update_workflow(workflow, status="published", version="1.0.0")
```

### Adding Inline Code Steps

```python
from raw.sdk import create_workflow, add_step

workflow = create_workflow(
    name="data-processor",
    intent="Process CSV and calculate statistics"
)

# Add step with inline Python code
add_step(
    workflow,
    name="calculate_stats",
    code="""
import pandas as pd

def calculate(data_path):
    df = pd.read_csv(data_path)
    return {
        "mean": df['value'].mean(),
        "std": df['value'].std(),
        "count": len(df)
    }
    """
)
```

## When to Use @agentic Decorator

### Use @agentic When:
- Decision requires subjective judgment
- Classification based on natural language
- Content summarization or extraction
- Sentiment analysis
- Intent detection
- Pattern recognition in unstructured data

### Use Deterministic Code When:
- Mathematical calculations
- Data transformation
- API calls
- Database queries
- File operations
- Rules-based logic
- Anything with predictable output

## @agentic Best Practices

### 1. Keep Prompts Focused

```python
# Good - Single, clear task
@agentic(
    prompt="Classify sentiment: {context.text}\nReturn: positive, negative, or neutral",
    max_tokens=10
)
def classify_sentiment(self, text: str) -> Literal["positive", "negative", "neutral"]:
    pass

# Bad - Multiple tasks in one step
@agentic(
    prompt="Classify sentiment, extract topics, and summarize: {context.text}",
    max_tokens=500
)
def analyze_everything(self, text: str) -> dict:
    pass
```

### 2. Use Return Type Hints

The decorator parses LLM responses based on return types:

```python
# String response
@agentic(prompt="Summarize: {context.text}")
def summarize(self, text: str) -> str:
    pass

# Literal values (enforced)
@agentic(prompt="Classify: {context.text}\nReturn: spam or ham")
def classify(self, text: str) -> Literal["spam", "ham"]:
    pass

# Integer
@agentic(prompt="Count items: {context.text}")
def count_items(self, text: str) -> int:
    pass

# List
@agentic(prompt="Extract keywords: {context.text}")
def extract_keywords(self, text: str) -> list[str]:
    pass
```

### 3. Set Cost Limits

Always set cost limits to prevent runaway expenses:

```python
# Small classification task
@agentic(
    prompt="Classify urgency: {context.ticket}",
    model="claude-3-5-haiku-20241022",
    max_tokens=10,
    cost_limit=0.001  # $0.001 per call
)
def classify_urgency(self, ticket: str) -> str:
    pass

# Larger summarization task
@agentic(
    prompt="Summarize meeting: {context.transcript}",
    model="claude-3-5-sonnet-20241022",
    max_tokens=500,
    cost_limit=0.05  # $0.05 per call
)
def summarize_meeting(self, transcript: str) -> str:
    pass
```

### 4. Choose the Right Model

```python
# Haiku - Fast, cheap, simple tasks
@agentic(
    prompt="Classify: {context.text}",
    model="claude-3-5-haiku-20241022",  # Cheapest
    max_tokens=10
)
def quick_classification(self, text: str) -> str:
    pass

# Sonnet - Complex reasoning, most use cases
@agentic(
    prompt="Analyze customer complaint: {context.text}",
    model="claude-3-5-sonnet-20241022",  # Default
    max_tokens=200
)
def analyze_complaint(self, text: str) -> dict:
    pass

# Opus - Very complex reasoning, rare
@agentic(
    prompt="Legal document analysis: {context.contract}",
    model="claude-opus-4-5-20251101",  # Most expensive
    max_tokens=2000
)
def analyze_contract(self, contract: str) -> dict:
    pass
```

## Cost Optimization Strategies

### 1. Cache Aggressively

Caching is enabled by default and saves significant cost:

```python
# Same prompt + model = cache hit (no API call)
@agentic(
    prompt="Classify sentiment: {context.text}",
    cache=True,  # Default
    cache_ttl=604800  # 7 days (default)
)
def classify(self, text: str) -> str:
    pass
```

Identical prompts return cached results instantly with zero cost.

### 2. Reduce Token Usage

Use the smallest `max_tokens` that works:

```python
# Classification - use minimal tokens
@agentic(
    prompt="Return only: critical, high, medium, or low",
    max_tokens=10  # Just enough for one word
)
def classify_urgency(self, ticket: str) -> str:
    pass

# Summary - be specific about length
@agentic(
    prompt="Summarize in 2-3 sentences: {context.text}",
    max_tokens=100  # Not 1000
)
def summarize(self, text: str) -> str:
    pass
```

### 3. Use Haiku for Simple Tasks

Haiku is 5-10x cheaper than Sonnet:

```python
# Simple classification - Haiku is plenty
@agentic(
    prompt="Classify: {context.text}",
    model="claude-3-5-haiku-20241022"
)
def classify(self, text: str) -> str:
    pass

# Complex analysis - Sonnet is better
@agentic(
    prompt="Deep analysis: {context.text}",
    model="claude-3-5-sonnet-20241022"
)
def analyze(self, text: str) -> dict:
    pass
```

### 4. Monitor Cost in Manifest

Check `manifest.json` after runs to see actual costs:

```json
{
  "agentic_steps": [
    {
      "step_name": "classify_urgency",
      "cost": 0.0002,
      "tokens": {"input": 25, "output": 8},
      "model": "claude-3-5-haiku-20241022"
    }
  ],
  "total_agentic_cost": 0.0002,
  "agentic_cache_hits": 5,
  "agentic_cache_misses": 1
}
```

## Tool Discovery Patterns

Before creating new tools, always search:

```python
from raw.discovery import search_tools

# Search before creating
results = search_tools("fetch stock prices")
if results:
    print(f"Found existing: {results[0].name}")
else:
    # Create new tool only if nothing found
    from raw.sdk import create_tool
    tool = create_tool(
        name="stock_fetcher",
        description="Fetch real-time stock prices from Yahoo Finance API"
    )
```

## Complete Example: Agent-Built Workflow

```python
from raw.sdk import create_workflow, add_step, get_workflow
from raw.discovery import search_tools

def build_support_workflow(user_request: str) -> str:
    """Build a customer support workflow from user request."""

    # Search for existing tools
    crm_tool = search_tools("CRM customer lookup")
    email_tool = search_tools("send email")

    if not crm_tool:
        raise ValueError("CRM tool not found - create it first")

    # Create workflow
    workflow = create_workflow(
        name="customer-support",
        intent=user_request
    )

    # Add steps using found tools
    add_step(
        workflow,
        name="lookup_customer",
        tool=crm_tool[0].name,
        config={"email": "{params.customer_email}"}
    )

    add_step(
        workflow,
        name="classify_urgency",
        code="""
from typing import Literal
from raw_runtime import agentic

@agentic(
    prompt="Classify: {context.issue}\\nReturn: critical, high, medium, or low",
    model="claude-3-5-haiku-20241022",
    max_tokens=10,
    cost_limit=0.001
)
def classify(issue: str) -> Literal["critical", "high", "medium", "low"]:
    pass
        """
    )

    add_step(
        workflow,
        name="send_response",
        tool=email_tool[0].name,
        config={"template": "support_response"}
    )

    return workflow.id
```

## Testing Agentic Steps

Test with dry runs to validate prompts without cost:

```bash
# Create workflow with @agentic steps
raw create customer-support --intent "Handle support tickets"

# Test with mocks (no API calls)
raw run customer-support --dry

# Test with real API (but limited data)
raw run customer-support --limit 1
```

## Common Patterns

### Classification Pipeline

```python
class TicketClassifier(BaseWorkflow[Params]):
    @step("load")
    def load_ticket(self) -> dict:
        # Deterministic - just load data
        return load_from_db(self.params.ticket_id)

    @step("classify_urgency")
    @agentic(
        prompt="Classify urgency: {context.ticket}",
        model="claude-3-5-haiku-20241022",
        max_tokens=10
    )
    def classify_urgency(self, ticket: dict) -> str:
        pass

    @step("classify_category")
    @agentic(
        prompt="Classify category: {context.ticket}",
        model="claude-3-5-haiku-20241022",
        max_tokens=20
    )
    def classify_category(self, ticket: dict) -> str:
        pass

    @step("route")
    def route_ticket(self, urgency: str, category: str):
        # Deterministic - routing logic
        return self.assign_to_queue(urgency, category)

    def run(self):
        ticket = self.load_ticket()
        urgency = self.classify_urgency(ticket)
        category = self.classify_category(ticket)
        self.route_ticket(urgency, category)
        return self.success(f"Routed to {category}/{urgency}")
```

### Extraction + Transformation

```python
class DataProcessor(BaseWorkflow[Params]):
    @step("extract")
    @agentic(
        prompt="Extract items from: {context.text}",
        max_tokens=500
    )
    def extract_items(self, text: str) -> list[str]:
        pass

    @step("transform")
    def transform_items(self, items: list[str]) -> list[dict]:
        # Deterministic - structured transformation
        return [{"name": item, "id": generate_id(item)} for item in items]

    @step("save")
    def save_items(self, items: list[dict]):
        # Deterministic - database operation
        db.insert_many(items)

    def run(self):
        items = self.extract_items(self.params.input_text)
        transformed = self.transform_items(items)
        self.save_items(transformed)
        return self.success(f"Processed {len(transformed)} items")
```

## Summary

**SDK Usage:**
- Use SDK for programmatic workflow construction
- Always search for existing tools before creating
- Validate workflows before running

**@agentic Usage:**
- Use only for decisions requiring LLM reasoning
- Set cost limits on every agentic step
- Use smallest model and token count that works
- Let caching save you money automatically

**Cost Optimization:**
- Cache is free performance (enabled by default)
- Haiku for simple classification ($0.0001-0.001)
- Sonnet for complex reasoning ($0.001-0.05)
- Monitor costs in manifest after runs

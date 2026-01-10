# RAW Development Guide

BEFORE ANYTHING ELSE: run `bd onboard` and follow the instructions

---

## Issue Tracking

**IMPORTANT**: Use `bd` (beads) for ALL issue tracking. Do NOT use markdown TODOs.

```bash
bd ready --json                           # Find unblocked work
bd create "Title" -t task -p 2 --json     # Create issue
bd update <id> --status in_progress       # Claim task
bd close <id> --reason "Done"             # Complete task
```

Commit `.beads/issues.jsonl` with code changes.

---

## Project Overview

**RAW (Run Agentic Workflows)** is an agent-native orchestration platform. It separates **intelligence** (you, the agent) from **infrastructure** (RAW):

- **You (Agent)** handle reasoning: understanding intent, generating logic, reacting to errors
- **RAW (Platform)** handles engineering: state, logging, caching, retries, manifests

### Architecture: Tools are Libraries, Workflows are Applications

- **Tools** = Reusable Python packages in `tools/` (internal, agent-managed)
- **Workflows** = Applications that import and use tools (user-facing)

Tools are imported in workflows like regular Python packages:
```python
from tools.web_scraper import fetch_url
from tools.llm_client import summarize

result = fetch_url("https://example.com")
summary = summarize(result)
```

```
Human: "What's Tesla's stock performance this quarter?"
    ↓
You: raw list tools → (need to build) → raw create --tool → raw create → write run.py → raw run
    ↓
Human receives the answer (not a workflow—an answer)
```

---

## Quick Commands

```bash
# Development
uv sync --group dev              # Install dependencies
uv run pytest tests/ -v          # Run tests (157 tests)
uv run ruff check . && uv run ruff format .  # Lint + format

# RAW CLI - Setup & Integration
raw init                         # Initialize .raw/ directory
raw onboard                      # Agent integration instructions (for AGENTS.md)
raw prime                        # Session context (workflows, tools)

# RAW CLI - Tool Discovery (CRITICAL - always check before creating!)
raw search "fetch stock data"    # Semantic search - USE THIS FIRST
raw list tools                   # Browse tools (only for small sets)

# RAW CLI - Build & Run
raw create <name> --tool -d ".." # Create reusable tool
raw create <name> --intent "..." # Create draft workflow
raw create <name> --from <id>    # Duplicate workflow
raw run <id> --dry --init        # Generate mock template
raw run <id> --dry               # Test with mocks
raw publish <id>                 # Freeze workflow
raw run <id> --arg value         # Execute
raw list                         # List workflows
raw show <id>                    # View workflow details
raw logs <id>                    # View execution logs
```

---

## Project Structure

```
src/
  raw/                    # CLI application
    cli.py                # Click commands (entry point)
    core/
      init.py             # Project initialization
      workflow.py         # Workflow management
      execution.py        # Workflow execution
      schemas.py          # Pydantic models
      markdown/           # Markdown generation (Jinja2)
      templates/          # Code scaffold templates
  raw_runtime/            # Library for workflow scripts
    decorators.py         # @step, @retry, @cache_step
    context.py            # WorkflowContext
    models.py             # StepResult, Artifact, Manifest

tests/                    # pytest suite
  fixtures/markdown/      # Golden files for template tests

# In user projects after `raw init`:
.raw/                     # RAW orchestration data
  config.yaml             # Project config
  workflows/              # Workflow definitions
  cache/                  # Cached data (gitignored)
  logs/                   # Execution logs (gitignored)
tools/                    # Tool packages (importable)
  __init__.py             # Package marker
  web_scraper/            # Example tool
    tool.py               # Tool implementation
    config.yaml           # Tool config
```

---

## Code Style

- Python 3.10+ with type hints everywhere
- Pydantic models for all data structures
- `ruff` for formatting and linting
- Jinja2 templates for code generation (see `src/raw/core/templates/`)

### Comments

- Comments explain WHY, not WHAT - code should be self-documenting
- No comments for self-explanatory code (`# Create directory` before `mkdir()`)
- Docstrings: one line when possible, no redundant parameter descriptions

## Core Principles (Non-Negotiable)

### 1. Clean Architecture

Follow strict layer separation:
```
Presentation → Application → Domain → Infrastructure
```

**Rules:**
- Domain layer has ZERO external dependencies
- Dependencies point inward only
- All external services use Protocol interfaces
- 100% dependency injection

### 2. SOLID Principles

Apply all five principles:
- **S**ingle Responsibility: One class, one reason to change
- **O**pen/Closed: Extend via protocols, not modification
- **L**iskov Substitution: Subtypes must be swappable
- **I**nterface Segregation: Small, focused protocols
- **D**ependency Inversion: Depend on abstractions

### 3. Test-Driven Development (TDD)

Always follow red-green-refactor:

1. **RED** - Write failing test first
2. **GREEN** - Write minimal code to pass
3. **REFACTOR** - Improve while tests pass

**Requirements:**
- 90%+ test coverage minimum
- Unit tests for all business logic
- Integration tests for external systems
- No code without tests

### 5. Human-Style Documentation

Write like a human, not an LLM.

**Two core principles:**
1. **Docstrings are concise** - State what the code does in 1-2 sentences. No essays.
2. **Comments explain "why" not "what"** - Only add comments when the reason isn't obvious from the code itself.

**Avoid these words/phrases:**
- "pivotal," "crucial," "revolutionary," "groundbreaking"
- "Moreover," "Furthermore," "It is worth noting"
- "In conclusion," "In summary," "Overall"
- "breathtaking," "a testament to," "boasts a rich heritage"
- "It should be said," "One could argue"
- "This highlights its significance," "underscoring the influence"

**Good docstring:**
```python
def analyze_content(content_id: int) -> AnalysisResult:
    """Analyze content and extract topics.

    Runs content through LLM and saves topics, sentiment,
    and summary to database.
    """
```

**Bad docstring:**
```python
def analyze_content(content_id: int) -> AnalysisResult:
    """This pivotal function leverages cutting-edge AI to
    revolutionize content analysis. Moreover, it should be
    noted that this plays a crucial role in the system.
    """
```

**Good comments (explain "why"):**
```python
# Twitter API returns max 100 items per request
page_size = 100

# Check if content exists to avoid duplicate capture
if self._repository.find_by_twitter_id(tweet.id):
    return None

# Retry with exponential backoff to handle rate limits
for attempt in range(3):
    try:
        response = self._client.fetch()
        break
    except RateLimitError:
        time.sleep(2 ** attempt)
```

**Bad comments (explain "what", which is obvious):**
```python
# Set page size to 100
page_size = 100

# Check if content exists
if self._repository.find_by_twitter_id(tweet.id):
    return None

# Loop 3 times
for attempt in range(3):
    ...
```

**No comment needed (code is self-documenting):**
```python
if content.is_analyzed:
    return cached_result

user_tweets = [t for t in tweets if t.author == username]
```

### Clean code Architecture

Here is a list of software engineering best practices to be applied:

1. Clean Architecture Principles (Separation into Layers):
    * Goal: Decouple core business logic from infrastructure concerns.
    * Concept: Organize code into concentric layers (e.g., Domain, Application, Adapters, Infrastructure). Inner layers define essential rules and don't know about outer layers. Dependencies flow
      inwards.

2. Dependency Injection (DI):
    * Goal: Promote loose coupling and enhance testability.
    * Concept: Components receive their dependencies from an external source (a "configurator" or "composition root") rather than creating them internally.

3. Programming to Interfaces (Protocols/Abstract Classes):
    * Goal: Allow interchangeable implementations and reduce coupling to concrete types.
    * Concept: Define contracts (interfaces/protocols) for services and components. Components should depend on these abstractions, not on specific implementations.

4. Single Responsibility Principle (SRP):
    * Goal: Ensure each component has one, clear, and well-defined purpose.
    * Concept: A class or module should have only one reason to change, preventing cascading changes when requirements evolve.

5. Type Safety and Data Validation:
    * Goal: Catch errors early and ensure data integrity.
    * Concept: Use a robust type system and validation libraries for data structures (e.g., configuration, API inputs/outputs). Validate data upon entry to the system's boundaries.

6. Modularity and Clear Organization:
    * Goal: Improve navigability, reduce cognitive load, and enable parallel development.
    * Concept: Group related files and classes into logical modules or packages based on features or architectural layers.

7. Robust Error Handling and Fault Tolerance:
    * Goal: Prevent system crashes and allow for graceful recovery.
    * Concept: Implement structured error handling (custom exceptions, error policies, retry mechanisms) to differentiate between transient and fatal errors, enabling appropriate responses.

8. Progressive Disclosure of Complexity:
    * Goal: Keep simple things simple, while allowing for complex functionality when needed.
    * Concept: Design systems where components expose only necessary information initially, loading more detail or functionality only when explicitly requested or required.

9. Immutability:
    * Goal: Reduce side effects and simplify reasoning about state.
    * Concept: Prefer immutable data structures, especially for events or configuration objects, ensuring their state cannot change after creation.

10. "Why > What" Documentation:
    * Goal: Provide context and architectural intent in documentation.
    * Concept: Comments and docstrings should explain why a particular design choice was made or why a piece of code behaves in a certain way, rather than merely restating what the code does (which is
      often self-evident).

---

## Testing

```bash
uv run pytest tests/ -v                    # All tests
uv run pytest tests/raw/ -v                # CLI/core tests
uv run pytest tests/raw_runtime/ -v        # Runtime tests
uv run pytest -k "test_render" -v          # Pattern match
```

Golden file tests in `tests/fixtures/markdown/` - update with:
```bash
uv run python -c "from raw.core.markdown import render_onboard; print(render_onboard())" > tests/fixtures/markdown/onboard.md
```

---

## Key Conventions

- Workflows use PEP 723 inline dependencies (`# /// script`)
- All execution via `uv run` (fast, reproducible)
- Published workflows are immutable - use `raw create --from` to modify
- Tool versions pinned on publish

---

## Writing Searchable Descriptions

Descriptions are indexed for semantic search (`raw search`). Write them for discoverability.

**Structure:** `[Action verb] [what] [from/to where] [key capabilities]`

**Good examples:**
```
Fetch real-time stock prices, historical data, and dividends from Yahoo Finance API
Send templated emails via SMTP with HTML support, attachments, and retry logic
Generate PDF reports from structured data with charts, tables, and custom styling
Scrape web pages and extract structured content using CSS selectors and XPath
```

**Bad examples:**
```
Tool for getting stock data              # Too vague
A utility that handles email sending     # Filler words, no specifics
This workflow processes files            # What files? How?
Data fetcher                             # Not a sentence, no context
```

**Rules:**
- Start with action verb: Fetch, Send, Generate, Convert, Scrape, Parse, Validate
- Include domain keywords: stock prices, emails, PDF, API, database
- Mention sources/destinations: from Yahoo Finance, to S3, via SMTP
- List key features: retry logic, caching, pagination, HTML support
- Avoid: "This tool...", "A utility for...", "Used to..."

---

## Workflow Creation (Agent Skill)

When user asks for something that requires a new capability:

1. **SEARCH FIRST** - `raw search "what you need"` - Find existing tools (scales to thousands)
2. Try different phrasings if first search doesn't find match
3. Create tools ONLY if search finds nothing: `raw create <name> --tool -d "description"`
4. `raw create <name> --intent "..."` - Create workflow
5. Write `run.py` using `BaseWorkflow` pattern (see below)
6. `raw run <id> --dry --init` - Generate mock template
7. `raw run <id> --dry` - Test with mocks
8. `raw run <id> --args` - Execute and deliver the answer

### Workflow run.py Pattern (CRITICAL)

**Always use `BaseWorkflow` and `self.save()` to persist results:**

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "rich>=13.0", "httpx>=0.27"]
# ///
from pydantic import BaseModel, Field
from raw_runtime import BaseWorkflow, step

# Import your tools
from tools.web_scraper import fetch_json

class MyParams(BaseModel):
    """CLI parameters."""
    limit: int = Field(default=3, description="Number of items")

class MyWorkflow(BaseWorkflow[MyParams]):
    @step("fetch")
    def fetch_data(self) -> list[dict]:
        return fetch_json("https://api.example.com/data")

    def run(self) -> int:
        data = self.fetch_data()
        self.save("result.json", data)  # CRITICAL: saves to results/
        return 0

if __name__ == "__main__":
    MyWorkflow.main()
```

**Key rules:**
- Use `self.save(filename, data)` to persist results (saved to `results/`)
- Use `@step` decorator for tracked operations
- Return `0` from `run()` for success
- When run via `raw run`, results end up in `runs/<timestamp>/results/`

**CRITICAL:** Always search before creating. Duplicate tools waste time and create maintenance burden.

**Tools are dependencies, workflows are applications.** Build reusable tools—capabilities built today solve tomorrow's problems.

---

## Agent-Native Architecture

RAW implements agent-native design at two layers:

### Layer 1: Programmatic Workflow Construction

Agents build workflows using the Python SDK instead of only CLI:

```python
from raw.sdk import create_workflow, add_step

# Agent creates workflow programmatically
workflow = create_workflow(
    name="stock-analysis",
    intent="Fetch Tesla stock data and generate report"
)

# Add steps
add_step(workflow, name="fetch", tool="stock_fetcher",
         config={"ticker": "TSLA"})
add_step(workflow, name="report", tool="pdf_generator")

# Validate before running
from raw.validation import WorkflowValidator
validator = WorkflowValidator()
result = validator.validate(workflow.directory)
if result.success:
    print("✓ Workflow valid")
```

**SDK Functions:**
- `create_workflow(name, intent, description)` - Create new workflow
- `list_workflows()` - List all workflows
- `get_workflow(id)` - Get workflow by ID
- `update_workflow(workflow, **kwargs)` - Update metadata
- `delete_workflow(workflow)` - Delete workflow
- `add_step(workflow, name, tool, code, config)` - Add step

### Layer 2: Selective Agentic Steps

Use `@agentic` decorator for LLM-powered reasoning in specific steps:

```python
from typing import Literal
from raw_runtime import BaseWorkflow, step, agentic

class SupportWorkflow(BaseWorkflow[Params]):
    @step("extract")
    def extract_ticket(self):
        # Deterministic - just reads data
        return self.params.ticket_data

    @step("classify")
    @agentic(
        prompt="""
        Classify support ticket urgency:
        Customer: {context.customer_tier}
        Issue: {context.issue}
        History: {context.history}

        Return ONLY: critical, high, medium, or low
        """,
        model="claude-3-5-haiku-20241022",
        max_tokens=10,
        cost_limit=0.01  # Safety limit
    )
    def classify_urgency(self, customer_tier: str, issue: str,
                         history: list) -> Literal["critical", "high", "medium", "low"]:
        pass  # Implementation injected by decorator

    @step("route")
    def route_ticket(self, urgency: str):
        # Deterministic - uses classification result
        if urgency == "critical":
            return self.escalate()
        return self.assign_to_pool(urgency)
```

**@agentic Parameters:**
- `prompt` - Template with {context.field} placeholders
- `model` - Claude model (sonnet/haiku/opus)
- `max_tokens` - Max response tokens
- `temperature` - Sampling temperature (0-1)
- `cost_limit` - Max cost per call (raises if exceeded)
- `cache` - Enable response caching (default: True)
- `cache_ttl` - Cache TTL in seconds (default: 7 days)

**Cost Tracking:**
Agentic steps automatically track:
- Estimated cost (before API call)
- Actual cost (from API response)
- Token usage (input/output)
- Per-step breakdown in manifest

**Caching:**
Responses are cached in `.raw/cache/agentic/` by prompt hash.
Identical prompts skip API calls, saving cost.

### Completion Signals

Use explicit signals instead of exit codes:

```python
class MyWorkflow(BaseWorkflow[Params]):
    def run(self):
        result = self.fetch_data()

        if result is None:
            return self.error("API returned no data")

        self.save("output.json", result)
        return self.success("Fetched 42 items", data={"count": 42})

        # Use .complete() for terminal state
        # return self.complete("Processing finished")
```

**Signal Types:**
- `.success(message, data)` - Succeeded, can continue
- `.error(message)` - Failed, can retry
- `.complete(message, data)` - Terminal state, stop execution

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

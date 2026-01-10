# RAW Guide

Guide for building workflows with RAW.

**New to RAW?** Start with [QUICKSTART.md](QUICKSTART.md).

---

## Why RAW?

**Problem:** AI agents can write code, but that code is ephemeral. Each execution starts fresh—no memory of what worked, no state management, no observability. When something fails, you have no logs, no manifests, no way to debug.

**Solution:** RAW provides the infrastructure layer that makes agent-generated code production-ready:

| Without RAW | With RAW |
|-------------|----------|
| Code runs once, outputs lost | Results persisted in `runs/<timestamp>/` |
| No retry logic | `@retry` with exponential backoff |
| Print statements for debugging | Structured manifests with timing |
| Manual dependency management | PEP 723 inline dependencies |
| No caching | `@cache_step` for expensive operations |

**Insight:** RAW separates **intelligence** from **infrastructure**:
- **RAW (Platform)** handles deterministic engineering: state, logging, caching, retries, manifests
- **Agent (Client)** handles probabilistic reasoning: understanding intent, generating code, reacting to errors

---

## Setting Up RAW

### Step 1: Create a Project Directory

```bash
mkdir my-project
cd my-project
```

### Step 2: Initialize Python Project with RAW

```bash
uv init
uv add raw
```

### Step 3: Initialize RAW

```bash
raw init
```

### Step 4: Configure API Keys

Copy the environment template and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your provider credentials:

```bash
# LLM Providers (at least one required for AI features)
ANTHROPIC_API_KEY=sk-ant-...    # Claude API
OPENAI_API_KEY=sk-...           # GPT-4 API
GEMINI_API_KEY=...              # Google Gemini API

# Messaging (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# Data Sources (optional)
ALPHAVANTAGE_API_KEY=...        # Stock data
NEWS_API_KEY=...                # News aggregation
```

RAW auto-loads `.env` from your project directory. For LLM features, configure at least one provider. Priority order: OpenAI > Anthropic > Gemini.

Check available providers:
```python
from raw_runtime import get_available_providers
print(get_available_providers())  # {'llm': ['anthropic'], 'messaging': [], 'data': []}
```

This creates the project structure:

```
my-project/
├── .raw/
│   ├── README.md       # Quick reference
│   ├── config.yaml     # RAW configuration
│   ├── libraries.yaml  # Preferred libraries for code generation
│   ├── workflows/      # Workflow definitions
│   ├── cache/          # Cached step results (gitignored)
│   └── logs/           # Execution logs (gitignored)
├── tools/              # Reusable tools (importable Python package)
│   └── __init__.py     # Package marker
├── pyproject.toml
└── ...
```

**Architecture:** Tools are Python packages in `tools/` that workflows import:
```python
from tools.web_scraper import fetch_url
```

### Step 5: AI Agent Integration

For Claude Code integration, run init with the hooks flag:

```bash
raw init --hooks
```

This creates `.claude/settings.local.json` with hooks that run `raw show --context` on session start, giving Claude awareness of your workflows and tools.

For manual context refresh:

```bash
raw show --context   # Output current session context
```

Ask Claude: *"Create a workflow that fetches stock data and generates a report"*

## Creating Your First Workflow

### Step 1: Create a Draft Workflow

```bash
raw create hello-world --intent "Greet a user by name and save the greeting to a file"
```

This creates a draft workflow with just the intent:

```
.raw/workflows/20251206-hello-world-abc123/
├── config.yaml     # Workflow definition with intent
├── README.md       # Documentation
└── mocks/          # Mock data for dry-run
```

### Step 2: View the Workflow

```bash
raw show hello-world
```

Output:
```
╭──────────────── Workflow: 20251206-hello-world-abc123 ────────────────╮
│ Status: draft                                                         │
│ Version: 1.0.0                                                        │
│ Created: 2025-12-06 10:30                                             │
│                                                                       │
│ "Greet a user by name and save the greeting to a file"                │
╰───────────────────────────────────────────────────────────────────────╯
```

### Step 3: Implement the Workflow

The AI agent (Claude Code) implements the workflow by:
1. Analyzing the workflow intent
2. Breaking it into steps
3. Creating or reusing tools
4. Writing `run.py`
5. Updating `config.yaml` with step definitions

Here's an example `run.py`:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "rich>=13.0"]
# ///
"""Hello World Workflow"""

from pathlib import Path
from pydantic import BaseModel, Field
from rich.console import Console

console = Console()

class WorkflowParams(BaseModel):
    name: str = Field(default="World", description="Name to greet")

class HelloWorldWorkflow:
    def __init__(self, params: WorkflowParams) -> None:
        self.params = params

    def run(self) -> int:
        message = f"Hello, {self.params.name}!"
        console.print(f"[green]>[/] {message}")
        Path("results").mkdir(exist_ok=True)
        Path("results/greeting.txt").write_text(message)
        return 0

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="World")
    args = parser.parse_args()
    exit(HelloWorldWorkflow(WorkflowParams(**vars(args))).run())
```

### Step 4: Test with Mock Data

```bash
raw run hello-world --dry
```

### Step 5: Run the Workflow

```bash
raw run hello-world --name "Claude"
```

Output:
```
> Generating greeting...
> Hello, Claude!
> Saved to results/greeting.txt

Done!

╭────────────────── Success ──────────────────╮
│ Workflow completed successfully!            │
│                                             │
│ Workflow: 20251206-hello-world-abc123       │
│ Duration: 0.15s                             │
│ Exit code: 0                                │
╰─────────────────────────────────────────────╯
```

## Working with Tools

Tools are reusable components that can be shared across workflows.

### Create a Tool

```bash
raw create fetch_data --tool --description "Fetch data from an API endpoint"
```

This creates:
```
tools/fetch_data/
├── config.yaml     # Tool configuration
├── tool.py         # Implementation
├── test.py         # Tests
└── README.md       # Documentation
```

### List Tools

```bash
raw list tools
```

### View Tool Details

```bash
raw show fetch-data
```

## Duplicating Workflows

To create a copy of an existing workflow:

```bash
raw create hello-world-v2 --from hello-world
```

## Workflow Lifecycle

```
create → implement → test → run
  │          │         │      │
  │          │         │      └── Execute with raw run
  │          │         └── Test with mock data (raw run --dry)
  │          └── AI agent writes code + tools
  └── Define intent (raw create)
```

1. **Create**: Scaffold with `raw create --intent "..."`
2. **Implement**: Write code and create/reuse tools
3. **Test**: Validate with mock data using `raw run <id> --dry`
4. **Run**: Execute with `raw run <id>`

## Using Decorators (Advanced)

RAW provides decorators for advanced workflow features. These require `raw_runtime`:

### @step - Track Step Execution

```python
from raw_runtime import step

@step("fetch_data")
def fetch_data(self):
    """Automatically tracks timing and results."""
    return {"count": 100}
```

### @retry - Resilient Operations

```python
from raw_runtime import step, retry

@step("api_call")
@retry(retries=3, backoff="exponential")
def api_call(self):
    """Retries up to 3 times with exponential backoff."""
    return requests.get(url).json()
```

### @cache_step - Cache Expensive Operations

```python
from raw_runtime import step
from raw_runtime.decorators import cache_step

@step("calculate")
@cache_step
def calculate(self, data):
    """Results are cached based on arguments."""
    return expensive_operation(data)
```

### @agent - LLM-Powered Steps

For workflow steps that need AI reasoning (summarization, classification, analysis):

```bash
uv add raw[ai]  # Install AI dependencies
```

```python
from pydantic import BaseModel
from raw_ai import agent

class Summary(BaseModel):
    title: str
    key_points: list[str]

@agent(result_type=Summary, model="gpt-4o-mini")
def summarize(self, text: str) -> Summary:
    """You are a summarizer. Extract the key points from the text."""
    ...
```

The docstring becomes the system prompt, arguments become the user message, and `result_type` defines the structured output. See [AI_AGENTS.md](AI_AGENTS.md) for full documentation.

## CLI Reference

| Command | Description |
|---------|-------------|
| `raw init` | Initialize RAW in current directory |
| `raw init --hooks` | Initialize with Claude Code hooks |
| `raw create <name>` | Create a new workflow |
| `raw create <name> --tool -d "..."` | Create a reusable tool |
| `raw create <name> --from <id>` | Duplicate existing workflow |
| `raw run <id>` | Execute a workflow |
| `raw run <id> --dry` | Test with mock data |
| `raw list` | List workflows |
| `raw list tools` | List tools |
| `raw list tools -s "query"` | Search tools by description |
| `raw show <id>` | Show workflow/tool details |
| `raw show <id> --logs` | View execution logs |
| `raw show --context` | Output agent context |

Most commands support **interactive selection** when ID is omitted.

## Best Practices

### 1. Use Descriptive Intents

```bash
# Good
raw create stock-report --intent "Fetch TSLA stock data for the last 3 months, calculate daily returns and 50-day moving average, then generate a PDF report with price charts"

# Too vague
raw create stock-report --intent "Analyze stocks"
```

### 2. Reuse Tools

Search for existing tools before creating new ones:
```bash
raw list tools -s "what you need"   # Search tools
raw list tools                      # List all tools
raw show <tool-name>                # View tool details
```

### 3. Test Before Running

Always run `raw run <id> --dry` before the real execution.

### 4. Use Pydantic for Parameters

```python
class WorkflowParams(BaseModel):
    ticker: str = Field(..., description="Stock symbol")
    period: str = Field(default="3mo", description="Time period")
```

### 5. Save Outputs to results/

```python
results_dir = Path("results")
results_dir.mkdir(exist_ok=True)
(results_dir / "output.json").write_text(json.dumps(data))
```

---

## See Also

- [QUICKSTART.md](QUICKSTART.md) - 30-second setup
- [API.md](API.md) - Runtime API reference
- [ARCHITECTURE.md](ARCHITECTURE.md) - Event-driven design

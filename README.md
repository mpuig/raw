# RAW: The Agent-Native Orchestration Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**RAW is local infrastructure for AI agents to perform complex work.**

It acts as a headless orchestration platform that separates **intelligence** (the agent) from **infrastructure** (RAW):

-   **The Platform (RAW)** handles deterministic engineering: state management, logging, caching, retries, dependency isolation, and execution history.
-   **The Client (Agent)** handles probabilistic reasoning: understanding user intent, generating logic, and reacting to errors.

The agent uses RAW via the CLI to build and execute durable workflows.

---

## Usage

RAW is **agent-native**: designed for AI agents. While humans use the CLI for debugging, observability, and manual intervention, the primary operator is the AI agent.

### Scenario 1: Building tools
You ask for an outcome. The agent builds the tool to deliver it.

> **Human:** "Fetch the top stories from Hacker News and summarize them."

**Claude Code (Behind the Scenes):**
1.  **Reasoning:** "I need a workflow for this. Let me check what tools exist."
2.  **Engineering:**
    *   `raw search "hacker news"` (finds existing tool)
    *   `raw create hn-summary --intent "Fetch HN stories and summarize"`
    *   Writes `run.py` using the discovered tool
    *   `raw run hn-summary --dry` (Verifies with mock data)
    *   `raw run hn-summary` (Executes)
3.  **Result:** "Here are today's top stories..."

### Scenario 2: System state
You ask about the state of the system.

> **Human:** "What workflows do I have? Show me the last run."

**Claude Code (Behind the Scenes):**
1.  **Action:** Runs `raw list` and `raw status`
2.  **Result:** "You have 2 workflows. Here's the recent execution history..."

---

## Installation (Project Setup)

Enable RAW for your agent in any Python project.

### 1. Prerequisites
-   **Python 3.10+**
-   **uv** (Recommended): `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 2. Initialize
```bash
# Add RAW to your project
uv add raw

# Initialize the platform
raw init

# Install Claude Code hooks (automatic context injection)
raw hooks install
```

**What happens?**
- `raw init` creates `.raw/` directory for workflows and config
- `raw hooks install` adds hooks to `.claude/settings.local.json` that run `raw prime` on session start

For full documentation, run `raw onboard`.

---

## Testing with Claude Code

After installation, you can test the integration:

### 1. Check what context Claude Code receives

```bash
raw prime
```

This outputs available workflows, tools, and recent execution history. The `SessionStart` hook runs this automatically when Claude Code starts a session.

### 2. View the installed hooks

```bash
cat .claude/settings.local.json
```

### 3. Test end-to-end

Open Claude Code in the project directory and try:

- "What workflows do I have?"
- "Create a workflow that fetches weather data"
- "Run the weather workflow"

Claude Code will use `raw create`, write `run.py`, and execute with `raw run`.

### 4. Manual workflow test

```bash
# Create a workflow
raw create hello-world --intent "Print hello world"

# Test with mock data
raw run hello-world --dry

# Execute
raw run hello-world

# Check logs
raw logs hello-world
```

---

## CLI

RAW has **5 core commands**:

| Command | Purpose |
| :--- | :--- |
| `raw init` | Initialize RAW (`--hooks` for Claude Code) |
| `raw create <name>` | Create a workflow (`--tool` for tools) |
| `raw build <id>` | Build workflow with agentic loop (`--resume`, `--last`) |
| `raw run <id>` | Execute a workflow (`--dry` for testing) |
| `raw show [id]` | List, inspect, validate (`--validate`, `--logs`) |

Run `raw --help` for all options.

```bash
# Navigation
raw show                    # List all workflows
raw show tools              # List all tools
raw show tools -s "fetch"   # Search tools

# Inspection
raw show my-workflow        # Show details
raw show my-workflow -v     # Validate structure
raw show my-workflow -l     # View logs
```

### Builder

The `raw build` command runs an agentic builder loop that:
- Plans implementation in read-only mode
- Executes changes to workflow and tools
- Verifies with quality gates (validate, dry run, optional tests)
- Iterates until gates pass or budget exhausted

```bash
# Start a new build
raw build my-workflow

# Resume interrupted build
raw build --resume build-20240110-123456-abc123
raw build --last  # Resume most recent build

# Configure budget
raw build my-workflow --max-iterations 5 --max-minutes 15
```

Builder state is journaled to `.raw/builds/<build-id>/events.jsonl` for resumability and observability.

---

## How It Works

```
User (Natural Language)
  │
  ▼
Agent Client (Claude Code) ──┐
  │ Logic & Reasoning        │ "Logs in" via CLI
  │                          │
  ▼                          ▼
RAW Platform (Local Runtime)
  ├── Workflows (Stateful Programs)
  ├── Tools (Reusable Components)
  ├── Runtime (Caching, Retries, Logs)
  └── Manifests (Execution History)
```

## Code Design

Workflows follow five **Agent-Native Code Rules**:

1. **Data Contract** - Pydantic models between steps, never raw dicts
2. **Resilience** - `@retry` on all external interactions
3. **Granularity** - Logic in `@step` methods, `run()` only coordinates
4. **IO Isolation** - Pure steps return data, save in `run()`
5. **Semantic Logging** - `self.log()` for business progress

See individual package READMEs for detailed guidance.

## Packages

RAW is a uv workspace monorepo. Each package can be installed independently.

### Core

| Package | Description |
| :--- | :--- |
| `raw-core` | Shared types, errors, and base protocols |
| `raw-bot` | Transport-agnostic conversation engine |
| `raw-agent` | Workflow execution with @step, @retry, @cache decorators |
| `raw-cli` | Command-line interface |
| `raw-codegen` | Code generation utilities |
| `raw-creator` | Tool and workflow creation |

### Integrations

| Package | Description |
| :--- | :--- |
| `integration-llm` | LiteLLM wrapper for multi-provider LLM support |
| `integration-deepgram` | Speech-to-text via Deepgram |
| `integration-elevenlabs` | Text-to-speech via ElevenLabs |
| `integration-twilio` | Voice calls and SMS |

### Transports

| Package | Description |
| :--- | :--- |
| `transport-voice` | Real-time voice pipeline (Pipecat) |
| `transport-webhook` | HTTP webhook handlers |

### Infrastructure

| Package | Description |
| :--- | :--- |
| `raw-state` | Session state backends (Redis, PostgreSQL) |
| `raw-queue` | Message queue backends (SQS, Kafka) |
| `raw-telemetry` | OpenTelemetry tracing and metrics |
| `raw-server` | Production FastAPI server with health checks |

## Examples

- `examples/solution-callcenter/` — Full call center implementation with skills, workflows, and Twilio integration

## Documentation

- **[CLAUDE.md](CLAUDE.md)** — Development guide

## Inspiration

RAW's agent integration pattern is inspired by [beads](https://github.com/steveyegge/beads), an AI-native issue tracker. Both tools share a common philosophy:

**Shared Principles:**
- **Agent-native design** - CLI tools designed to be used *by* AI agents, not just *for* them
- **Instruction-based onboarding** - The `onboard` command outputs instructions for the agent to follow, keeping the agent in control of documentation changes
- **Separation of concerns** - `init` creates infrastructure, `onboard` provides integration instructions, `prime` delivers session context

**The Pattern:**
```
init    → Create directory structure (.raw/, .beads/)
onboard → Output instructions for AGENTS.md integration
prime   → Provide session context for the agent
```

This pattern enables AI agents to discover and integrate with tools autonomously, while maintaining clear boundaries between infrastructure setup and documentation.

## License

MIT

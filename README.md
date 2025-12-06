# RAW: The Agent-Native Orchestration Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**RAW is the local infrastructure for AI agents to perform complex work.**

It acts as a headless orchestration platform that separates **intelligence** (the agent) from **infrastructure** (RAW):

-   **The Platform (RAW)** handles deterministic engineering: state management, logging, caching, retries, dependency isolation, and execution history.
-   **The Client (Agent)** handles probabilistic reasoning: understanding user intent, generating logic, and reacting to errors.

The agent "logs in" to RAW via the CLI—much like a developer uses AWS to deploy infrastructure—to build and execute durable workflows.

---

## Usage

RAW is **agent-native**: designed to be piloted by AI agents. While humans can (and should) use the CLI for debugging, observability, and manual intervention, the primary operator is your AI agent.

**Quick start:** [docs/QUICKSTART.md](docs/QUICKSTART.md)

### Scenario 1: Just-in-Time Capability
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

### Scenario 2: System Observability
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

## The Agent's API (CLI Reference)

While designed for agents, these commands are available for debugging or manual intervention.

| Command | Purpose |
| :--- | :--- |
| **`raw init`** | Initialize the platform in the current directory. |
| **`raw hooks install`** | Install Claude Code hooks for automatic context injection. |
| **`raw onboard`** | Interactive wizard to create/update AGENTS.md instructions. |
| **`raw prime`** | Dump session context for the agent. |
| **`raw create <name>`** | Create a new workflow (supports `--from <id>` to duplicate). |
| **`raw create <name> --tool`** | Create a reusable tool. |
| **`raw install <url>`** | Install a remote tool from a Git repository. |
| **`raw run [id]`** | Execute a workflow (prompts if id omitted, `--dry` for mocks). |
| **`raw list`** | List all workflows. |
| **`raw list tools`** | List all tools. |
| **`raw search <query>`** | Search tools by description (semantic or keyword). |
| **`raw show [id]`** | Show details/configuration (prompts if id omitted). |
| **`raw status [id]`** | Show execution history and logs. |
| **`raw publish [id]`** | Freeze a workflow and pin dependencies. |
| **`raw serve`** | Start daemon server for webhooks and approvals. |

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

## Code Philosophy

Workflows follow five **Agent-Native Code Rules** that ensure robust, testable, observable code resistant to agent hallucinations:

1. **Data Contract** - Pydantic models between steps, never raw dicts
2. **Resilience** - `@retry` on all external interactions
3. **Granularity** - Logic in `@step` methods, `run()` only coordinates
4. **IO Isolation** - Pure steps return data, save in `run()`
5. **Semantic Logging** - `self.log()` for business progress

See [docs/GUIDE.md](docs/GUIDE.md) for detailed guidance.

## Documentation

-   **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - 30-second setup guide
-   **[docs/GUIDE.md](docs/GUIDE.md)** - Building workflows and best practices
-   **[docs/API.md](docs/API.md)** - Runtime API reference
-   **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Event-driven design
-   **[CLAUDE.md](CLAUDE.md)** - Development guide

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

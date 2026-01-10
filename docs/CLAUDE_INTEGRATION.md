# Claude Code Integration

This document explains how RAW integrates with Claude Code and the rationale behind design decisions.

---

## Integration Approach

RAW uses **CLI + Hooks** for Claude Code integration:

```bash
# 1. Install RAW
uv add raw

# 2. Initialize with hooks
cd your-project
raw init --hooks
```

**How it works:**
- `SessionStart` hook runs `raw show --context` when Claude Code starts
- `PreCompact` hook refreshes context before compaction
- Context injection is ~500-1k tokens of workflow state
- You use `raw` CLI commands directly in conversation

---

## Why CLI + Hooks (Not MCP)

RAW deliberately uses the lightweight CLI approach instead of MCP servers.

### Token Efficiency

**Compute cost scales with tokens**—every token in your context consumes compute on every inference, regardless of whether it's used.

| Approach | Context Cost | Notes |
|----------|--------------|-------|
| MCP Server | 10-50k tokens | Full tool schemas loaded always |
| CLI + Hooks | ~500-1k tokens | Only current state, refreshed on demand |

The `raw show --context` output is minimal: quick reference, key rules, and a list of current workflows/tools.

### Simplicity

- **No protocol overhead**: Direct CLI calls, no MCP message passing
- **Universal**: Works with any editor that has shell access
- **Debuggable**: `raw show --context` output is plain markdown you can inspect
- **Portable**: Same commands work in terminal, Claude Code, Cursor, Windsurf

### When MCP Makes Sense

MCP is better for:
- Tools that need streaming responses
- Complex state management across calls
- Tools the AI calls frequently (every message)

RAW workflows are typically run once per task, making CLI the right choice.

---

## Agent Skills

RAW provides **Agent Skills** that Claude Code automatically invokes when you ask to create workflows or tools.

### What Are Agent Skills?

Agent Skills are a Claude Code feature: modular `SKILL.md` files in `.claude/skills/` that Claude reads when relevant to your request. Unlike slash commands (user-invoked), Skills are **model-invoked**—Claude decides when to use them based on your task and the Skill's description.

### RAW Skills

RAW includes two skills that are installed via `raw init --hooks`:

| Skill | Description |
|-------|-------------|
| `raw-workflow-creator` | Create and run RAW workflows. Invoked when you ask to create a workflow, automate a task, or generate reports. |
| `raw-tool-creator` | Create reusable RAW tools. Invoked when you ask to create a tool or extract reusable functionality. |

These skills provide:
- Step-by-step processes for creating workflows and tools
- Code templates and patterns (BaseWorkflow, tool structure)
- Validation checklists
- Error recovery guidance

### Skill Installation

Skills are automatically installed when you run:

```bash
raw init --hooks
```

This installs:
1. **Hooks** in `.claude/settings.local.json` (runs `raw show --context` on session start)
2. **Skills** in `.claude/skills/` (auto-invoked by Claude when relevant)

```
.claude/
├── settings.local.json      # Hooks configuration
└── skills/
    ├── raw-workflow-creator/
    │   └── SKILL.md
    └── raw-tool-creator/
        └── SKILL.md
```

### How Skills Work

When you ask Claude to create a workflow:

```
User: "Create a workflow that fetches stock data and generates a report"
```

Claude sees the `raw-workflow-creator` skill description and automatically reads the full `SKILL.md` to get detailed instructions on:
- Searching for existing tools first
- Using `raw create` to scaffold
- Implementing with BaseWorkflow pattern
- Testing with `raw run --dry`

### Skill Storage Locations

```
~/.claude/skills/          # Personal skills (all projects)
.claude/skills/            # Project skills (shared via git)
```

RAW installs skills to the project level (`.claude/skills/`) so they're version-controlled and shared with your team.

See [Claude Code Skills documentation](https://code.claude.com/docs/en/skills) for more on creating custom Skills.

---

## Context Injection Flow

```
Session Start
     │
     ▼
┌─────────────────────────┐
│ SessionStart hook       │  ← Runs raw show --context
│ (settings.local.json)   │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Claude Code Context     │  ← Receives workflow/tool summary
└─────────────────────────┘
```

### What `raw show --context` Outputs

```markdown
# RAW Context

## Quick Reference
raw search "capability"    # Search tools (DO THIS FIRST)
raw create <name> --intent # Create workflow
raw run <id> --dry         # Test with mocks

## Key Rules
1. SEARCH FIRST - raw search before creating tools
2. Tools in tools/ - Auto-snapshotted on run
3. Test before delivery - raw run --dry

## Workflows (2)
- 📝 hn-summary - Fetch and summarize HN stories
- ✓ daily-digest - Generate daily news digest

## Tools (3)
- hackernews: Fetch stories from HN API
- web-scraper: Scrape and parse web pages
```

This gives Claude Code awareness of:
- Available commands
- Key workflow rules
- Current project state (workflows + tools)

---

## Hook Management

Hooks are installed **per-project** in `.claude/settings.local.json`. This keeps RAW context scoped to projects that use it.

### Install Hooks

```bash
raw init --hooks
```

Creates `.claude/settings.local.json`:
```json
{
  "hooks": {
    "SessionStart": [{"matcher": "", "hooks": [{"type": "command", "command": "raw show --context"}]}],
    "PreCompact": [{"matcher": "", "hooks": [{"type": "command", "command": "raw show --context"}]}]
  }
}
```

---

## Tools-as-Libraries Architecture

RAW's tool architecture is designed for AI agents:

```
tools/                        # Project root (importable)
    hackernews/
        __init__.py           # from .tool import fetch_top_stories
        tool.py               # def fetch_top_stories(limit=10): ...
        config.yaml           # name, version, description, deps

.raw/workflows/
    hn-summary/
        run.py                # from tools.hackernews import ...
        _tools/               # Auto-snapshotted on run
```

### Why This Design?

1. **Reusability**: Tools are Python packages, imported like any library
2. **Discoverability**: `raw search` finds tools by description
3. **Portability**: `raw run` snapshots tools into `_tools/`, rewrites imports
4. **Version tracking**: `origin.json` records git commit, content hash

### The Auto-Snapshot Flow

```
Developer writes:          raw run executes:
─────────────────          ─────────────────
from tools.hn        →     from _tools.hn
import fetch               import fetch
```

Workflows are self-contained after snapshot—no external dependencies.

---

## Comparison: RAW vs Beads Integration

| Aspect | RAW | Beads |
|--------|-----|-------|
| Primary command | `raw show --context` | `bd prime` |
| Hook events | SessionStart, PreCompact | SessionStart, PreCompact |
| Context size | ~500-1k tokens | ~1-2k tokens |
| Skills | Core feature | Not used |
| Focus | Workflow orchestration | Issue tracking |

Both tools follow the same integration philosophy: lightweight CLI + hooks for efficient context injection.

---

## Troubleshooting

### Hooks Not Running

```bash
# Reinstall hooks
raw init --hooks
```

### Context Not Refreshing

```bash
# Manual refresh
raw show --context

# Check RAW is initialized
ls .raw/
```

### Wrong Project Context

`raw show --context` reads from `.raw/` in the current directory. Ensure you're in the right project:

```bash
pwd
ls .raw/workflows/
```

---

## See Also

- [QUICKSTART.md](QUICKSTART.md) - Get started
- [GUIDE.md](GUIDE.md) - Building workflows
- [ARCHITECTURE.md](ARCHITECTURE.md) - Event-driven design

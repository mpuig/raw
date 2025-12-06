# GitHub Copilot Instructions for RAW

## Project Overview

**RAW** (Run Agentic Workflows) is an agent-first CLI tool for workflow orchestration designed to be used by Claude Code and similar AI agents.

**Key Features:**
- Prompt-first workflow design with intent
- Reusable tool system
- Publish/versioning lifecycle
- Local-first execution via uv

## Tech Stack

- **Language**: Python 3.10+
- **CLI Framework**: Click
- **Models**: Pydantic v2
- **Output**: Rich
- **Execution**: uv (PEP 723 inline dependencies)
- **Testing**: pytest

## Issue Tracking with bd (beads)

**CRITICAL**: This project uses **bd** for ALL task tracking. Do NOT create markdown TODO lists.

### Essential Commands

```bash
# Find work
bd ready --json                    # Unblocked issues

# Create and manage
bd create "Title" -t bug|feature|task -p 0-4 --json
bd create "Subtask" --parent <epic-id> --json  # Hierarchical subtask
bd update <id> --status in_progress --json
bd close <id> --reason "Done" --json
```

### Workflow

1. **Check ready work**: `bd ready --json`
2. **Claim task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** `bd create "Found bug" -p 1 --deps discovered-from:<parent-id> --json`
5. **Complete**: `bd close <id> --reason "Done" --json`

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

## Project Structure

```
raw/
├── src/raw/
│   ├── __init__.py          # Version
│   ├── cli.py               # CLI commands
│   └── core/
│       ├── display.py       # Rich output
│       ├── execution.py     # Workflow execution
│       ├── init.py          # Project init, tools
│       ├── schemas.py       # Pydantic models
│       └── workflow.py      # Workflow management
├── tests/
│   └── test_cli.py          # CLI tests
├── .raw/                    # RAW project data (when initialized)
│   ├── config.yaml
│   ├── libraries.yaml
│   ├── workflows/
│   └── tools/
└── .beads/
    └── issues.jsonl         # Issue tracking
```

## RAW CLI Commands

| Command | Description |
|---------|-------------|
| `raw init` | Initialize RAW in project |
| `raw onboard` | Show agent instructions |
| `raw prime` | Output context (workflows, tools, skills) |
| `raw create <name>` | Create draft workflow |
| `raw edit <id>` | Edit draft workflow intent or name |
| `raw generate <id>` | Guide for code generation |
| `raw run <id> [args]` | Execute workflow |
| `raw dry-run <id>` | Test with mocks |
| `raw dry-run <id> --init` | Generate dry_run.py template |
| `raw test <id>` | Run tests |
| `raw publish <id>` | Freeze workflow |
| `raw dup <id>` | Duplicate workflow |
| `raw status <id>` | Show status |
| `raw list` | List workflows |
| `raw show <id>` | Show details |
| `raw tools` | List tools |
| `raw tool-create <name>` | Create tool |

## Coding Guidelines

### Testing
- Run `uv run pytest` before committing
- Use Click's CliRunner for CLI tests
- Use `isolated_filesystem()` for file tests

### Code Style
- Run `uv run ruff check .` and `uv run ruff format .`
- Follow existing patterns in cli.py for new commands
- Use Pydantic models for all data structures
- Use Rich for all CLI output

## Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic bd commands
- ✅ Run tests before committing
- ✅ Follow existing code patterns
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT skip tests

---

**For detailed workflows and features, see [AGENTS.md](../AGENTS.md)**

## RAW (Run Agentic Workflows)

**RAW is your orchestration platform.** You handle reasoning; RAW handles infrastructure (state, logging, caching, retries).

### Architecture

- **Tools** = Reusable Python packages in `tools/` (created on-demand)
- **Workflows** = Applications in `.raw/workflows/` that import tools

```python
from tools.hackernews import fetch_top_stories  # Tool import
stories = fetch_top_stories(limit=3)
```

### Quick Reference

```bash
raw search "stock data"           # Search existing tools (DO THIS FIRST)
raw list tools                    # Browse all tools
raw create <name> --intent "..."  # Create workflow
raw create <name> --tool -d "..." # Create tool (only if search finds nothing)
raw run <id> --dry                # Test with mocks
raw run <id> [args]               # Execute
```

---

## Workflow Creation

**Key Directives**:
1. **SEARCH FIRST** - `raw search "capability"` before creating tools
2. **TOOLS ARE LIBRARIES** - Reusable packages in `tools/`, created on-demand
3. **AUTO-SNAPSHOT** - `raw run` copies tools to `_tools/` automatically
4. **TEST BEFORE DELIVERY** - Always `raw run --dry` before telling user it's ready

### Process

```bash
# 1. Create workflow
raw create <name> --intent "..."

# 2. For each capability needed in run.py:
raw search "hackernews"                    # Search first
# Not found? Create: tools/hackernews/tool.py + __init__.py + config.yaml
# Then import: from tools.hackernews import fetch_top_stories

# 3. Test and run
raw run <id> --dry
raw run <id> [args]
```

### Ask Before Building

Clarify when: data source unclear, output format unspecified, parameters ambiguous, delivery method unclear.

### run.py Template

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "rich>=13.0"]
# ///
"""Workflow description."""

import json
from pathlib import Path
from pydantic import BaseModel, Field
from rich.console import Console

from tools.example import fetch_data  # Import from tools

console = Console()

class WorkflowParams(BaseModel):
    limit: int = Field(default=10, description="Number of items")

class Workflow:
    def __init__(self, params: WorkflowParams) -> None:
        self.params = params
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)

    def run(self) -> int:
        try:
            console.print("[blue]>[/] Fetching...")
            data = fetch_data(limit=self.params.limit)

            console.print("[blue]>[/] Saving...")
            path = self.results_dir / "output.json"
            path.write_text(json.dumps(data, indent=2))

            console.print(f"[green]Done![/] {path}")
            return 0
        except Exception as e:
            console.print(f"[red]Error:[/] {e}")
            return 1

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    exit(Workflow(WorkflowParams(**vars(args))).run())

if __name__ == "__main__":
    main()
```

---

## Tool Creation

Tools are Python packages in `tools/` with: `tool.py`, `__init__.py`, `config.yaml`

```bash
raw search "capability"              # 1. Search first!
raw create <name> --tool -d "..."    # 2. Create scaffold
# 3. Implement tools/<name>/tool.py
# 4. Export in tools/<name>/__init__.py
```

**Tool config.yaml:**
```yaml
name: hackernews
version: "1.0.0"
status: draft
description: Fetch stories from HackerNews API
dependencies:
  - httpx>=0.27
```

---

## Directory Structure

```
tools/                        # Tools (project root, importable)
    <tool-name>/
        __init__.py           # Exports
        tool.py               # Implementation
        config.yaml           # Metadata
.raw/
    workflows/
        <workflow-id>/
            config.yaml       # Workflow config
            run.py            # Entry point
            _tools/           # Auto-snapshotted tools
            runs/             # Execution history
```

---

## Error Recovery

1. **Dependency errors** → Add to PEP 723 header
2. **API failures** → Add retry logic, check timeouts
3. **Stuck after 2 attempts** → Explain error, ask user

## Security

- Never hardcode secrets → `os.environ.get("API_KEY")`
- Always set timeouts → `httpx.get(url, timeout=30)`
- Validate inputs, sanitize paths

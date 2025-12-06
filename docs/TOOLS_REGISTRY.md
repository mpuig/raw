# Tool Registry

The Tool Registry provides discovery, installation, and management of reusable tools in RAW.

## Overview

Tools are Python packages in `tools/` that workflows import. The registry system enables:

- **Discovery**: Search and list available tools
- **Installation**: Fetch tools from git repositories
- **Management**: Update and remove tools
- **Portability**: Auto-snapshot tools into workflow runs

## Directory Structure

```
project/
├── tools/                    # Tool packages (project root)
│   ├── __init__.py
│   ├── coingecko/            # Example tool
│   │   ├── config.yaml       # Tool metadata
│   │   ├── tool.py           # Implementation
│   │   ├── __init__.py       # Exports
│   │   └── test.py           # Tests
│   └── web_scraper/
│       └── ...
└── .raw/
    └── workflows/
        └── my-workflow/
            └── runs/
                └── 20251208-123456/
                    ├── _tools/           # Snapshotted tools
                    │   └── coingecko/    # Copied from tools/
                    └── run.py            # Imports rewritten
```

## CLI Commands

### Search Tools

```bash
raw search "crypto price"     # Search by keyword
raw search "fetch api"        # Try different phrasings
```

### List Tools

```bash
raw list tools                # Show all installed tools
```

### Install from Git

```bash
# Basic install (derives name from URL)
raw install https://github.com/user/my-tool

# Pin to specific version
raw install https://github.com/user/my-tool --ref v1.0.0
raw install https://github.com/user/my-tool --ref main

# Override tool name
raw install https://github.com/user/my-tool --name custom_name
```

### Uninstall

```bash
raw uninstall my_tool
```

## Tool Configuration

Each tool has a `config.yaml`:

```yaml
name: coingecko
version: 1.0.0
description: Fetch cryptocurrency prices from CoinGecko API
status: draft

inputs:
  - name: coin_ids
    type: list[str]
    required: true
    description: Coin IDs to fetch

outputs:
  - name: prices
    type: dict
    description: Price data by coin

dependencies:
  - httpx>=0.27
```

## Using Tools in Workflows

### Import Pattern

```python
# In run.py - use tools.X
from tools.coingecko import get_prices, get_market_chart

class MyWorkflow(BaseWorkflow[Params]):
    @step("fetch")
    def fetch_data(self) -> dict:
        return get_prices(["bitcoin", "ethereum"])
```

### Auto-Snapshotting

When `raw run` executes a workflow:

1. Copies used tools from `tools/` to `_tools/` in the run directory
2. Rewrites imports: `from tools.X` → `from _tools.X`
3. Records provenance in `origin.json` (git commit, content hash)

This makes each run self-contained and reproducible.

## Registry Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    CompositeRegistry                     │
│  (combines multiple registries, deduplicates by name)   │
└─────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │   Local     │  │   Remote    │  │   Custom    │
   │  Registry   │  │   Index     │  │  Registry   │
   │ (tools/)    │  │  (future)   │  │             │
   └─────────────┘  └─────────────┘  └─────────────┘
```

### ToolRegistry Protocol

All registries implement this interface:

```python
class ToolRegistry(Protocol):
    def list_tools(self) -> list[ToolInfo]:
        """List all available tools."""
        ...

    def get_tool(self, name: str) -> ToolInfo | None:
        """Get a tool by name."""
        ...

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search tools by description/name."""
        ...
```

### ToolInfo Model

```python
class ToolInfo(BaseModel):
    name: str                          # Tool identifier
    version: str = "1.0.0"             # Semantic version
    description: str = ""              # Searchable description
    source: str = "local"              # "local", "git", "registry"
    path: Path | None = None           # Local filesystem path
    git_url: str | None = None         # Source repository
    git_ref: str | None = None         # Git ref (tag, branch, commit)
    dependencies: list[str] = []       # PEP 723 dependencies
    inputs: list[dict] = []            # Input definitions
    outputs: list[dict] = []           # Output definitions
```

### LocalToolRegistry

Scans `tools/` directory for installed tools:

```python
from raw.discovery.registry import LocalToolRegistry

registry = LocalToolRegistry(Path("tools"))

# List all tools
tools = registry.list_tools()

# Get specific tool
tool = registry.get_tool("coingecko")

# Search
results = registry.search("crypto")
for r in results:
    print(f"{r.tool.name}: {r.score}")
```

### GitToolFetcher

Handles installation from git repositories:

```python
from raw.discovery.git_fetcher import GitToolFetcher

fetcher = GitToolFetcher(Path("tools"))

# Install
result = fetcher.fetch(
    git_url="https://github.com/user/tool",
    name="my_tool",        # Optional: override name
    ref="v1.0.0",          # Optional: pin version
    vendor=True,           # Remove .git directory
)

if result.success:
    print(f"Installed to {result.tool_path}")
else:
    print(f"Error: {result.error}")

# Update (non-vendored tools only)
result = fetcher.update("my_tool", ref="v2.0.0")

# Remove
result = fetcher.remove("my_tool")
```

## Creating Tools

### Using the CLI

```bash
# Create scaffold
raw create my_tool --tool -d "Description of what it does"

# This creates tools/my_tool/config.yaml
# Then implement tool.py, __init__.py, test.py
```

### Tool Implementation Pattern

```python
# tools/my_tool/tool.py
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27"]
# ///
"""Fetch data from MyAPI."""

import httpx

def fetch_data(query: str, limit: int = 10) -> list[dict]:
    """Fetch data from the API.

    Args:
        query: Search query
        limit: Max results

    Returns:
        List of result dictionaries

    Raises:
        ValueError: If query is empty
        httpx.HTTPError: If API request fails
    """
    if not query:
        raise ValueError("query cannot be empty")

    response = httpx.get(
        "https://api.example.com/search",
        params={"q": query, "limit": limit},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["results"]
```

```python
# tools/my_tool/__init__.py
"""Fetch data from MyAPI."""

from .tool import fetch_data

__all__ = ["fetch_data"]
```

### Testing Tools

```bash
# Run tool tests
uv run pytest tools/my_tool/test.py -v
```

## Best Practices

### Tool Design

- **Single responsibility**: One tool does one thing well
- **Pure functions**: Avoid side effects, return JSON-serializable data
- **Input validation**: Check parameters at function entry
- **Timeouts**: Always set `timeout=30` on network calls
- **Documentation**: Include docstrings with Args/Returns/Raises

### Naming

- Use underscores: `fetch_stock`, `parse_csv` (not `fetch-stock`)
- Be specific: `coingecko` not `crypto_api`
- Match the primary function name to the tool name

### Searchability

Write descriptions for discovery:

```yaml
# Good - searchable
description: Fetch cryptocurrency prices, market data, and historical charts from CoinGecko API

# Bad - not searchable
description: A tool for getting crypto data
```

## Global Registry

Access the shared registry instance:

```python
from raw.discovery.registry import get_tool_registry, set_tool_registry

# Get default registry (LocalToolRegistry for tools/)
registry = get_tool_registry()

# Set custom registry
from raw.discovery.registry import CompositeRegistry, LocalToolRegistry

custom = CompositeRegistry([
    LocalToolRegistry(Path("tools")),
    LocalToolRegistry(Path("vendor/tools")),
])
set_tool_registry(custom)
```

## Future: Remote Index Registry

The registry architecture supports remote tool indexes (not yet implemented):

```python
class RemoteIndexRegistry:
    """Fetch tool index from remote URL."""

    def __init__(self, index_url: str):
        self._index_url = index_url

    def list_tools(self) -> list[ToolInfo]:
        # Fetch JSON index from URL
        ...

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        # Search remote index
        ...
```

This would enable a central tool hub where users can discover and install community tools.

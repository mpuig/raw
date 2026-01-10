# CLI-to-SDK Parity Audit

This document tracks parity between RAW CLI commands and SDK functions, ensuring agents can do programmatically via SDK what users do via CLI. This is a core agent-native principle.

## Summary

- **Total CLI Commands**: 14
- **Full Parity**: 6 (43%)
- **Partial Parity**: 4 (29%)
- **Missing SDK**: 4 (29%)

**Note**: This represents a strong foundation. The 6 full-parity commands cover all essential CRUD operations for workflows and tools. The 4 partial-parity commands are usable but have ergonomic issues. The 4 missing commands are either convenience features (logs, search) or system-level operations (init).

## Parity Status

Legend:
- ✅ Full parity - CLI and SDK equivalent with same functionality
- ⚠️ Partial parity - SDK exists but missing features
- ❌ Missing - No SDK equivalent yet

## Core Commands

| CLI Command | SDK Equivalent | Status | Notes |
|-------------|----------------|--------|-------|
| `raw init` | - | ❌ Missing | System setup command - needs SDK wrapper |
| `raw create <name> --intent "..."` | `create_workflow(name, intent)` | ✅ Full parity | Creates draft workflow |
| `raw create <name> --tool -d "..."` | `create_tool(name, description)` | ✅ Full parity | Tool creation in SDK |
| `raw create <name> --from <id>` | `duplicate_workflow(source_path, name)` | ⚠️ Partial | SDK requires path, not ID |
| `raw list` | `list_workflows()` | ✅ Full parity | Lists all workflows |
| `raw list tools` | `list_tools()` | ✅ Full parity | Tool listing in SDK |
| `raw list tools -s "query"` | `search_tools(query)` | ❌ Missing | Search not in SDK yet |
| `raw run <id>` | `Container.workflow_runner().run(...)` | ⚠️ Partial | Can use runner directly, but awkward |
| `raw run <id> --dry` | `Container.workflow_runner().run_dry(...)` | ⚠️ Partial | Can use runner directly, but awkward |
| `raw run <id> --dry --init` | `generate_dry_run_template(path)` | ❌ Missing | Not exposed in SDK |
| `raw show <id>` | `get_workflow(id)` | ✅ Full parity | Get workflow details |
| `raw show <tool>` | `get_tool(name)` | ✅ Full parity | Tool details in SDK |
| `raw show <id> --logs` | - | ❌ Missing | Log viewing not in SDK |
| `raw publish <id>` | `publish_workflow(path)` then `update_workflow(w, status="published")` | ⚠️ Partial | Can call publish_workflow directly but requires path |

## Hidden/Internal Commands

These commands are exposed via command modules but not in main CLI:

| CLI Command | SDK Equivalent | Status | Notes |
|-------------|----------------|--------|-------|
| `raw prime` (via `show --context`) | `get_prime_content()` | ❌ Missing | Agent context not in SDK |
| `raw search "query"` (via `list tools -s`) | `search_tools(query)` | ❌ Missing | Search function exists in discovery.search but not SDK |
| `raw onboard` | `render_onboard()` | ❌ Missing | Markdown generation not in SDK |
| `raw serve` | - | ❌ Missing | Server management not in SDK |
| `raw stop` | - | ❌ Missing | Server management not in SDK |
| `raw trigger <id>` (via `run --remote`) | - | ❌ Missing | Remote execution not in SDK |
| Hooks install/uninstall | - | ❌ Missing | Integration setup not in SDK |

## SDK Functions Analysis

### Currently Available in SDK

From `..src/raw/sdk/workflow.py`:

1. **`create_workflow(name, intent, description=None) -> Workflow`**
   - Creates draft workflow
   - ✅ Matches `raw create <name> --intent "..."`

2. **`list_workflows() -> list[Workflow]`**
   - Lists all workflows
   - ✅ Matches `raw list`

3. **`get_workflow(workflow_id) -> Workflow | None`**
   - Gets workflow by ID or partial match
   - ✅ Matches `raw show <id>`

4. **`update_workflow(workflow, **kwargs) -> Workflow`**
   - Updates workflow metadata (name, intent, status, version)
   - ✅ Can be used for publishing via `update_workflow(w, status="published")`
   - ⚠️ But `raw publish` does more (tool pinning, version bumping)

5. **`delete_workflow(workflow) -> None`**
   - Deletes workflow and all files
   - ✅ No CLI equivalent - SDK-only feature

6. **`add_step(workflow, name, tool=None, code=None, config=None) -> Step`**
   - Adds step to workflow
   - ✅ No direct CLI equivalent - SDK-only feature

From `..src/raw/sdk/tools.py`:

7. **`create_tool(name, description, tool_type="function", tools_dir=None) -> Tool`**
   - Creates new tool package
   - ✅ Matches `raw create <name> --tool -d "..."`

8. **`list_tools(tools_dir=None) -> list[Tool]`**
   - Lists all tool packages
   - ✅ Matches `raw list tools`

9. **`get_tool(name, tools_dir=None) -> Tool | None`**
   - Gets tool by name
   - ✅ Matches `raw show <tool>`

10. **`update_tool(name, description=None, version=None, tools_dir=None) -> Tool`**
    - Updates tool metadata
    - ✅ No CLI equivalent - SDK-only feature

11. **`delete_tool(name, tools_dir=None) -> None`**
    - Deletes tool package
    - ✅ No CLI equivalent - SDK-only feature

### Available in Core but Not SDK

From `..src/raw/discovery/search.py`:

1. **`search_tools(query, project_dir=None) -> list[dict]`**
   - Semantic/TF-IDF tool search
   - Should be exposed in SDK

From `..src/raw/discovery/workflow.py`:

2. **`publish_workflow(workflow_dir) -> WorkflowConfig`**
   - Publishes workflow with tool pinning
   - Should be exposed in SDK (currently imported internally)

3. **`duplicate_workflow(source_dir, name) -> tuple[Path, WorkflowConfig]`**
   - Duplicates workflow
   - SDK needs wrapper that accepts ID instead of path

From `..src/raw/scaffold/dry_run.py`:

4. **`generate_dry_run_template(workflow_dir) -> None`**
   - Generates mock template for dry runs
   - Should be exposed in SDK

From `..src/raw/scaffold/init.py`:

5. **`get_prime_content() -> str`**
   - Gets agent context
   - Should be exposed in SDK

6. **`init_raw_project(project_dir=None) -> Path`**
   - Initializes RAW in project
   - Should be exposed in SDK

### Available in Engine but Not SDK

From `..src/raw/engine/container.py`:

1. **`Container.workflow_runner() -> WorkflowRunner`**
   - Gets workflow runner
   - Partially accessible but awkward to use

2. **`WorkflowRunner.run(workflow_dir, script, args) -> RunResult`**
   - Runs workflow
   - Should have SDK wrapper

3. **`WorkflowRunner.run_dry(workflow_dir, args) -> RunResult`**
   - Runs workflow in dry mode
   - Should have SDK wrapper

## Gaps Requiring SDK Functions

### High Priority (Core Operations)

1. **Tool Search**
   - `search_tools(query) -> list[Tool]`

2. **Workflow Execution**
   - `run_workflow(workflow, args=None) -> RunResult`
   - `run_workflow_dry(workflow, args=None) -> RunResult`

3. **Workflow Publishing**
   - Better `publish_workflow(workflow) -> Workflow` that accepts Workflow object

4. **Workflow Duplication**
   - Better `duplicate_workflow(workflow, name) -> Workflow` that accepts Workflow object

### Medium Priority (Development Operations)

5. **Dry Run Generation**
   - `generate_dry_run_template(workflow) -> None`

6. **Project Initialization**
   - `init_project(project_dir=None) -> Path`

7. **Agent Context**
   - `get_agent_context() -> str`

### Low Priority (Inspection)

8. **Logs**
   - `get_workflow_logs(workflow, run_id=None, lines=50) -> str`
   - `stream_workflow_logs(workflow, run_id=None) -> Iterator[str]`

9. **Run History**
    - `list_workflow_runs(workflow) -> list[Run]`
    - `get_workflow_run(workflow, run_id) -> Run | None`

10. **Manifest**
    - `get_workflow_manifest(workflow) -> Manifest | None`

### Very Low Priority (Server/Integration)

11. **Server Operations**
    - Not needed for SDK - server is CLI-only concern

12. **Hooks Management**
    - Not needed for SDK - hooks are integration setup

## Implementation Plan

### Phase 1: Core Operations (Immediate)
- ✅ Tool management - Complete (create_tool, list_tools, get_tool, update_tool, delete_tool)
- Add tool search to SDK
- Add workflow execution wrappers to SDK
- Add better publish/duplicate that accept Workflow objects

### Phase 2: Development Features (Soon)
- Add dry run template generation
- Add project initialization
- Add agent context function

### Phase 3: Inspection Features (Later)
- Add log viewing functions
- Add run history functions
- Add manifest functions

### Phase 4: Models (Ongoing)
- Add `Tool` model to SDK
- Add `Run` model to SDK
- Add `RunResult` model to SDK (expose from engine)
- Add `Manifest` model to SDK

## Usage Examples

### What Works Today

```python
from raw.sdk import (
    create_workflow, list_workflows, get_workflow, update_workflow,
    create_tool, list_tools, get_tool, update_tool, delete_tool,
)

# Workflow operations
wf = create_workflow("my-workflow", "Fetch and analyze data")
workflows = list_workflows()
wf = get_workflow("my-workflow")
wf = update_workflow(wf, status="published")

# Tool operations
tool = create_tool("stock_fetcher", "Fetch stock prices from API")
tools = list_tools()
tool = get_tool("stock_fetcher")
tool = update_tool("stock_fetcher", description="Updated description")
delete_tool("stock_fetcher")
```

### What's Needed

```python
from raw.sdk import (
    # Tool search (MISSING)
    search_tools,

    # Execution (MISSING proper wrappers)
    run_workflow, run_workflow_dry,

    # Better publish (MISSING)
    publish_workflow,  # Should accept Workflow, not Path

    # Agent context (MISSING)
    get_agent_context,
)

# Tool search (MISSING)
tools = search_tools("fetch stock prices")

# Workflow execution (MISSING proper wrapper)
result = run_workflow(wf, args=["--ticker", "TSLA"])

# Agent context (MISSING)
context = get_agent_context()
```

## Testing Strategy

All SDK functions should have corresponding tests in `tests/raw_sdk/`:

1. **test_parity.py** - Verify parity checking function
2. **test_workflow.py** - Existing workflow SDK tests
3. **test_tool.py** - New tool SDK tests (to be created)
4. **test_execution.py** - New execution SDK tests (to be created)
5. **test_search.py** - New search SDK tests (to be created)

## Related Documentation

- `..src/raw/sdk/README.md` - SDK usage guide
- `..CLAUDE.md` - RAW development guide
- `..docs/agent-native-guide.md` - Agent-native principles

---

**Last Updated**: 2026-01-10
**Audit Status**: Initial audit complete

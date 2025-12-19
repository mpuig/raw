"""RAW project initialization."""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from raw.core.schemas import LibrariesConfig, ToolConfig, WorkflowConfig
from raw.scaffold.template_render import render_tool_template


def is_raw_initialized(project_dir: Path | None = None) -> bool:
    """Check if RAW is initialized in the project."""
    if project_dir is None:
        project_dir = Path.cwd()

    raw_dir = project_dir / ".raw"
    config_file = raw_dir / "config.yaml"

    return raw_dir.exists() and config_file.exists()


def get_raw_dir(project_dir: Path | None = None) -> Path:
    """Get the .raw directory path."""
    if project_dir is None:
        project_dir = Path.cwd()
    return project_dir / ".raw"


def get_workflows_dir(project_dir: Path | None = None) -> Path:
    """Get the workflows directory for the project."""
    return get_raw_dir(project_dir) / "workflows"


def get_tools_dir(project_dir: Path | None = None) -> Path:
    """Get the tools directory for the project.

    Tools live in tools/ at the project root, not in .raw/.
    This makes them importable as a Python package.
    """
    if project_dir is None:
        project_dir = Path.cwd()
    return project_dir / "tools"


def init_raw_project(project_dir: Path | None = None) -> Path:
    """Initialize RAW in a project directory.

    Creates:
    - .raw/ directory
    - .raw/config.yaml
    - .raw/libraries.yaml
    - .raw/README.md (onboarding for AI agents)
    - .raw/workflows/ directory
    - .raw/cache/ directory
    - .raw/logs/ directory
    - tools/ directory (at project root, importable Python package)

    Args:
        project_dir: Project directory (defaults to cwd)

    Returns:
        Path to the .raw directory
    """
    if project_dir is None:
        project_dir = Path.cwd()

    raw_dir = project_dir / ".raw"

    raw_dir.mkdir(exist_ok=True)
    (raw_dir / "workflows").mkdir(exist_ok=True)
    (raw_dir / "cache").mkdir(exist_ok=True)
    (raw_dir / "logs").mkdir(exist_ok=True)

    tools_dir = get_tools_dir(project_dir)
    tools_dir.mkdir(exist_ok=True)
    tools_init = tools_dir / "__init__.py"
    if not tools_init.exists():
        tools_init.write_text('"""RAW Tools - Reusable capabilities for workflows."""\n')

    config = {
        "version": "0.2.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    config_path = raw_dir / "config.yaml"
    if not config_path.exists():
        config_path.write_text(yaml.dump(config, default_flow_style=False))

    libraries_path = raw_dir / "libraries.yaml"
    if not libraries_path.exists():
        default_libs = LibrariesConfig()
        libraries_path.write_text(
            yaml.dump(default_libs.model_dump(), default_flow_style=False, sort_keys=False)
        )

    gitignore_content = """# RAW directory
# Track config and workflows, ignore cache and logs
/cache/
/logs/
"""
    gitignore_path = raw_dir / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(gitignore_content)

    readme_content = """# RAW - Run Agentic Workflows

This directory contains RAW workflow orchestration data.

## Quick Start

```bash
raw show --context   # Get session context for agents
raw list             # View workflows
```

## Contents

- `config.yaml` - RAW configuration
- `libraries.yaml` - Preferred libraries for code generation
- `workflows/` - Workflow definitions
- `cache/` - Cached data
- `logs/` - Execution logs

Note: Tools live in `tools/` at project root (not here).

## Learn More

- Run `raw show --context` for agent session context
- Run `raw init --hooks` for Claude Code integration
- See project README for documentation
"""
    readme_path = raw_dir / "README.md"
    if not readme_path.exists():
        readme_path.write_text(readme_content)

    return raw_dir


def load_libraries_config(project_dir: Path | None = None) -> LibrariesConfig:
    """Load the libraries configuration."""
    raw_dir = get_raw_dir(project_dir)
    libraries_path = raw_dir / "libraries.yaml"

    if not libraries_path.exists():
        return LibrariesConfig()

    try:
        data = yaml.safe_load(libraries_path.read_text())
        return LibrariesConfig(**data) if data else LibrariesConfig()
    except Exception:
        return LibrariesConfig()


def save_workflow_config(workflow_dir: Path, config: WorkflowConfig) -> None:
    """Save workflow configuration to config.yaml."""
    config_path = workflow_dir / "config.yaml"
    data = config.model_dump(mode="json")
    config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def load_workflow_config(workflow_dir: Path) -> WorkflowConfig | None:
    """Load workflow configuration from config.yaml.

    Handles both v0.2.0 format and legacy v0.1.0 format.
    """

    config_path = workflow_dir / "config.yaml"

    if not config_path.exists():
        return None

    try:
        data = yaml.safe_load(config_path.read_text())
        if not data:
            return None

        # Handle legacy v0.1.0 format (description is a string)
        if isinstance(data.get("description"), str):
            data["description"] = {
                "intent": data["description"],
                "inputs": [],
                "outputs": [],
            }
            # Remove legacy fields
            data.pop("short_name", None)

        # Ensure status is set
        if "status" not in data:
            data["status"] = "draft"

        return WorkflowConfig(**data)
    except Exception:
        return None


def save_tool_config(tool_dir: Path, config: ToolConfig) -> None:
    """Save tool configuration to config.yaml."""
    config_path = tool_dir / "config.yaml"
    data = config.model_dump(mode="json")
    config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))


def load_tool_config(tool_dir: Path) -> ToolConfig | None:
    """Load tool configuration from config.yaml."""
    config_path = tool_dir / "config.yaml"

    if not config_path.exists():
        return None

    try:
        data = yaml.safe_load(config_path.read_text())
        return ToolConfig(**data) if data else None
    except Exception:
        return None


def get_onboard_content() -> str:
    """Get the onboarding content for AI agents."""
    from raw.scaffold.markdown import render_onboard

    return render_onboard()


def get_prime_content(project_dir: Path | None = None) -> str:
    """Generate context for AI agents about available workflows and tools.

    This is designed to be injected into Claude Code's context at session start.
    Modeled after bd prime for consistent agent experience.
    """
    from raw.discovery.workflow import list_workflows
    from raw.scaffold.markdown import PrimeContext, ToolSummary, WorkflowSummary, render_prime

    workflow_summaries = []
    for wf in list_workflows(get_workflows_dir(project_dir)):
        intent = ""
        if isinstance(wf.get("description"), dict):
            intent = wf["description"].get("intent", "")
        elif isinstance(wf.get("description"), str):
            intent = wf.get("description", "")

        workflow_summaries.append(
            WorkflowSummary(
                id=wf.get("id", "unknown"),
                name=wf.get("name", wf.get("id", "unknown")),
                status=wf.get("status", "draft"),
                intent=intent,
            )
        )

    tool_summaries = []
    for tool in list_tools(project_dir):
        tool_summaries.append(
            ToolSummary(
                name=tool.get("name", "unknown"),
                version=tool.get("version", "1.0.0"),
                status=tool.get("status", "draft"),
                description=tool.get("description", ""),
            )
        )

    ctx = PrimeContext(workflows=workflow_summaries, tools=tool_summaries)
    return render_prime(ctx)


def list_tools(project_dir: Path | None = None) -> list[dict[str, Any]]:
    """List all tools in the project."""
    tools_dir = get_tools_dir(project_dir)

    if not tools_dir.exists():
        return []

    tools = []
    for path in sorted(tools_dir.iterdir()):
        if not path.is_dir():
            continue

        if path.name.startswith(".") or path.name.startswith("__"):
            continue

        config = load_tool_config(path)
        if config:
            tools.append(
                {
                    "name": config.name,
                    "version": config.version,
                    "status": config.status,
                    "description": config.description,
                    "path": str(path),
                }
            )
        else:
            tools.append(
                {
                    "name": path.name,
                    "version": "-",
                    "status": "unknown",
                    "description": "-",
                    "path": str(path),
                }
            )

    return tools


def find_tool(tool_name: str, project_dir: Path | None = None) -> Path | None:
    """Find a tool by name."""
    tools_dir = get_tools_dir(project_dir)

    if not tools_dir.exists():
        return None

    tool_path = tools_dir / tool_name
    if tool_path.exists() and tool_path.is_dir():
        return tool_path

    return None


def calculate_tool_hash(tool_dir: Path) -> str:
    """Calculate SHA256 hash of all tool files.

    Hashes all files in the tool directory (sorted by name) to create
    a deterministic fingerprint. Used for tool locking/versioning.
    """
    import hashlib

    hasher = hashlib.sha256()

    files = sorted(tool_dir.rglob("*"))
    for file_path in files:
        if file_path.is_file() and not file_path.name.startswith("."):
            # Include relative path in hash for structure sensitivity
            rel_path = file_path.relative_to(tool_dir)
            hasher.update(str(rel_path).encode())
            hasher.update(file_path.read_bytes())

    return hasher.hexdigest()


def verify_tool_hash(tool_dir: Path, expected_hash: str) -> bool:
    """Verify tool files match the expected hash."""
    current_hash = calculate_tool_hash(tool_dir)
    return current_hash == expected_hash


def sanitize_tool_name(name: str) -> str:
    """Sanitize a tool name for use as a Python module name.

    Uses underscores (not hyphens) because tools are imported as Python modules.
    Example: "web-scraper" -> "web_scraper"
    """
    # Replace spaces and hyphens with underscores
    sanitized = re.sub(r"[\s-]+", "_", name.strip())
    # Remove any characters that aren't alphanumeric or underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "", sanitized)
    # Collapse multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    # Remove leading/trailing underscores and lowercase
    return sanitized.strip("_").lower()


def create_tool(
    name: str,
    description: str,
    inputs: list[dict[str, Any]] | None = None,
    outputs: list[dict[str, Any]] | None = None,
    dependencies: list[str] | None = None,
    project_dir: Path | None = None,
) -> tuple[Path, ToolConfig]:
    """Create a new tool scaffold.

    Args:
        name: Tool name (will be sanitized)
        description: Tool description
        inputs: List of input definitions
        outputs: List of output definitions
        dependencies: PEP 723 dependencies
        project_dir: Project directory

    Returns:
        Tuple of (tool directory path, tool config)
    """
    from raw.core.schemas import InputDefinition, OutputDefinition

    tools_dir = get_tools_dir(project_dir)
    tool_name = sanitize_tool_name(name)
    tool_dir = tools_dir / tool_name

    if tool_dir.exists():
        raise ValueError(f"Tool already exists: {tool_name}")

    tool_dir.mkdir(parents=True, exist_ok=True)

    input_defs = []
    if inputs:
        for inp in inputs:
            input_defs.append(InputDefinition(**inp))

    output_defs = []
    if outputs:
        for out in outputs:
            output_defs.append(OutputDefinition(**out))

    config = ToolConfig(
        name=tool_name,
        description=description,
        inputs=input_defs,
        outputs=output_defs,
        dependencies=dependencies or [],
    )

    save_tool_config(tool_dir, config)

    func_name = tool_name.replace("-", "_")
    deps_str = "\n".join(f'#   "{dep}",' for dep in (dependencies or []))
    deps_str = f"\n{deps_str}\n" if deps_str else "\n"

    inputs_params = ", ".join(f"{inp.name}: {inp.type}" for inp in input_defs)
    outputs_types = ", ".join(out.type for out in output_defs)
    if len(output_defs) > 1:
        return_type = f"tuple[{outputs_types}]"
    elif output_defs:
        return_type = output_defs[0].type
    else:
        return_type = "None"

    call_args = ", ".join(f"args.{inp.name}" for inp in input_defs)

    # Only create config.yaml - the skill will create the code files
    # This allows the agent to write complete implementations instead of editing placeholders

    return tool_dir, config

"""Workflow management utilities."""

import json
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from raw.core.schemas import (
    WorkflowConfig,
    WorkflowDescription,
    WorkflowStatus,
)
from raw.scaffold.init import (
    get_workflows_dir,
    load_tool_config,
    load_workflow_config,
    save_workflow_config,
)
from raw.scaffold.template_render import render_workflow_template


def get_git_commit_hash(path: Path | None = None) -> str | None:
    """Get the current git commit hash for a path."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=path or Path.cwd(),
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def find_tool_imports(content: str) -> list[str]:
    """Find tools imports in Python source code.

    Delegates to ToolManager.find_imports for actual implementation.
    """
    from raw.discovery.tools import ToolManager

    return ToolManager.find_imports(content)


def snapshot_tools(workflow_dir: Path) -> dict[str, dict]:
    """Snapshot tools used by a workflow into _tools/ directory.

    Copies the tool code and creates origin.json with git reference.
    Delegates to ToolManager for actual implementation.

    Returns:
        Dict mapping tool name to origin info
    """
    from raw.discovery.tools import get_tool_manager

    manager = get_tool_manager()
    return manager.snapshot(workflow_dir, git_hash=get_git_commit_hash())


def sanitize_name(name: str) -> str:
    """Sanitize a workflow name for use in IDs and paths."""
    # Replace spaces and underscores with hyphens
    sanitized = re.sub(r"[\s_]+", "-", name.strip())
    # Remove any characters that aren't alphanumeric or hyphens
    sanitized = re.sub(r"[^a-zA-Z0-9-]", "", sanitized)
    # Collapse multiple hyphens
    sanitized = re.sub(r"-+", "-", sanitized)
    # Remove leading/trailing hyphens and lowercase
    return sanitized.strip("-").lower()


def to_class_name(name: str) -> str:
    """Convert a workflow name to a valid Python class name (PascalCase)."""
    # Replace non-alphanumeric with spaces for word splitting
    words = re.sub(r"[^a-zA-Z0-9]+", " ", name).split()
    # Capitalize each word and join
    return "".join(word.capitalize() for word in words)


def generate_workflow_id(short_name: str) -> str:
    """Generate a unique workflow ID.

    Format: <yyyymmdd>-<short-name>-<short-uuid>
    """
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:6]
    sanitized = sanitize_name(short_name)
    return f"{date_str}-{sanitized}-{short_uuid}"


def create_workflow_scaffold(
    short_name: str,
    workflows_dir: Path | None = None,
) -> Path:
    """Create a new workflow scaffold.

    Args:
        short_name: Human-readable workflow name
        workflows_dir: Directory to create workflow in

    Returns:
        Path to the created workflow directory
    """
    if workflows_dir is None:
        workflows_dir = get_workflows_dir()

    workflow_id = generate_workflow_id(short_name)
    workflow_dir = workflows_dir / workflow_id

    workflow_dir.mkdir(parents=True, exist_ok=True)
    (workflow_dir / ".raw").mkdir(exist_ok=True)
    (workflow_dir / ".raw" / "cache").mkdir(exist_ok=True)
    (workflow_dir / ".raw" / "logs").mkdir(exist_ok=True)
    (workflow_dir / "results").mkdir(exist_ok=True)

    # Create config.yaml using v0.2.0 format
    config = WorkflowConfig(
        id=workflow_id,
        name=short_name,
        status=WorkflowStatus.DRAFT,
        description=WorkflowDescription(
            intent=f"Scaffold workflow: {short_name}",
        ),
    )
    save_workflow_config(workflow_dir, config)

    ctx = {
        "short_name": short_name,
        "workflow_id": workflow_id,
        "class_name": to_class_name(short_name),
        "description": f"Scaffold workflow: {short_name}",
    }

    (workflow_dir / "run.py").write_text(render_workflow_template("run.py.j2", **ctx))
    (workflow_dir / "test.py").write_text(render_workflow_template("test.py.j2", **ctx))
    (workflow_dir / "dry_run.py").write_text(render_workflow_template("dry_run.py.j2", **ctx))
    (workflow_dir / "README.md").write_text(
        render_workflow_template("readme_scaffold.md.j2", **ctx)
    )

    return workflow_dir


def find_workflow(workflow_id: str, workflows_dir: Path | None = None) -> Path | None:
    """Find a workflow by ID or partial match.

    Args:
        workflow_id: Full or partial workflow ID
        workflows_dir: Directory to search in

    Returns:
        Path to workflow directory or None if not found
    """
    if workflows_dir is None:
        workflows_dir = get_workflows_dir()

    if not workflows_dir.exists():
        return None

    exact_path = workflows_dir / workflow_id
    if exact_path.exists() and exact_path.is_dir():
        return exact_path

    for path in workflows_dir.iterdir():
        if path.is_dir() and workflow_id in path.name:
            return path

    return None


def list_workflows(workflows_dir: Path | None = None) -> list[dict[str, Any]]:
    """List all workflows.

    Args:
        workflows_dir: Directory to search in

    Returns:
        List of workflow info dicts
    """
    if workflows_dir is None:
        workflows_dir = get_workflows_dir()

    if not workflows_dir.exists():
        return []

    workflows = []
    for path in sorted(workflows_dir.iterdir()):
        if not path.is_dir():
            continue

        config_path = path / "config.yaml"
        if config_path.exists():
            try:
                config = yaml.safe_load(config_path.read_text())
                config["path"] = str(path)
                workflows.append(config)
            except yaml.YAMLError:
                workflows.append({"id": path.name, "path": str(path)})
        else:
            workflows.append({"id": path.name, "path": str(path)})

    return workflows


def list_runs(workflow_dir: Path) -> list[dict[str, Any]]:
    """List all runs for a workflow, sorted by timestamp descending.

    Args:
        workflow_dir: Path to workflow directory

    Returns:
        List of run info dicts with run_id, manifest, and path
    """
    runs_dir = workflow_dir / "runs"
    if not runs_dir.exists():
        return []

    runs = []
    for run_path in sorted(runs_dir.iterdir(), reverse=True):
        if not run_path.is_dir():
            continue

        manifest_path = run_path / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
                runs.append(
                    {
                        "run_id": run_path.name,
                        "path": str(run_path),
                        "manifest": manifest,
                    }
                )
            except json.JSONDecodeError:
                runs.append(
                    {
                        "run_id": run_path.name,
                        "path": str(run_path),
                        "manifest": None,
                    }
                )

    return runs


def load_manifest(workflow_dir: Path) -> dict[str, Any] | None:
    """Load the most recent manifest for a workflow.

    Args:
        workflow_dir: Path to workflow directory

    Returns:
        Manifest dict or None if no runs found
    """
    runs = list_runs(workflow_dir)
    if not runs:
        return None

    # Return manifest from most recent run
    return runs[0].get("manifest")


def create_draft_workflow(
    name: str,
    intent: str,
    workflows_dir: Path | None = None,
) -> tuple[Path, WorkflowConfig]:
    """Create a new draft workflow (v0.2.0 prompt-first approach).

    Args:
        name: Human-readable workflow name
        intent: Natural language description of what the workflow does
        workflows_dir: Directory to create workflow in

    Returns:
        Tuple of (workflow directory path, workflow config)
    """
    if workflows_dir is None:
        workflows_dir = get_workflows_dir()

    workflow_id = generate_workflow_id(name)
    workflow_dir = workflows_dir / workflow_id

    workflow_dir.mkdir(parents=True, exist_ok=True)
    (workflow_dir / "mocks").mkdir(exist_ok=True)

    config = WorkflowConfig(
        id=workflow_id,
        name=name,
        description=WorkflowDescription(intent=intent),
    )

    save_workflow_config(workflow_dir, config)

    readme = render_workflow_template(
        "readme_draft.md.j2",
        name=name,
        workflow_id=workflow_id,
        intent=intent,
    )
    (workflow_dir / "README.md").write_text(readme)

    return workflow_dir, config


def publish_workflow(workflow_dir: Path) -> WorkflowConfig:
    """Publish a workflow, making it immutable.

    Args:
        workflow_dir: Path to workflow directory

    Returns:
        Updated workflow config

    Raises:
        ValueError: If workflow cannot be published
    """
    from raw.scaffold.init import get_tools_dir

    config = load_workflow_config(workflow_dir)
    if not config:
        raise ValueError(f"Could not load workflow config from {workflow_dir}")

    if config.status == "published":
        raise ValueError("Workflow is already published")

    run_py = workflow_dir / "run.py"
    if not run_py.exists():
        raise ValueError(
            "Workflow has no generated code (run.py missing). Implement run.py before publishing."
        )

    # Pin tool versions and hashes - fail if any tool cannot be resolved
    from raw.scaffold.init import calculate_tool_hash

    tools_dir = get_tools_dir()
    missing_tools = []
    for step in config.steps:
        if step.tool_version is None or step.tool_hash is None:
            tool_dir = tools_dir / step.tool
            if not tool_dir.exists():
                missing_tools.append(f"{step.tool} (not found)")
                continue
            tool_config = load_tool_config(tool_dir)
            if not tool_config:
                missing_tools.append(f"{step.tool} (invalid config)")
                continue
            step.tool_version = tool_config.version
            step.tool_hash = calculate_tool_hash(tool_dir)

    if missing_tools:
        raise ValueError(
            f"Cannot publish: unresolved tool versions for: {', '.join(missing_tools)}"
        )

    tool_origins = snapshot_tools(workflow_dir)

    config.status = WorkflowStatus.PUBLISHED
    config.published_at = datetime.now(timezone.utc)

    if tool_origins:
        config.tool_snapshots = tool_origins

    save_workflow_config(workflow_dir, config)

    return config


def duplicate_workflow(
    source_workflow_dir: Path,
    new_name: str | None = None,
    workflows_dir: Path | None = None,
) -> tuple[Path, WorkflowConfig]:
    """Duplicate a workflow for modification.

    Args:
        source_workflow_dir: Path to source workflow
        new_name: New workflow name (optional, defaults to original name)
        workflows_dir: Directory to create new workflow in

    Returns:
        Tuple of (new workflow directory path, new workflow config)
    """
    if workflows_dir is None:
        workflows_dir = get_workflows_dir()

    source_config = load_workflow_config(source_workflow_dir)
    if not source_config:
        raise ValueError(f"Could not load workflow config from {source_workflow_dir}")

    name = new_name or source_config.name
    new_id = generate_workflow_id(name)
    new_workflow_dir = workflows_dir / new_id

    shutil.copytree(source_workflow_dir, new_workflow_dir)

    new_config = source_config.model_copy(deep=True)
    new_config.id = new_id
    new_config.name = name
    new_config.status = WorkflowStatus.DRAFT
    new_config.created_at = datetime.now(timezone.utc)
    new_config.published_at = None

    # Clear tool version pins (they'll be re-pinned on publish)
    for step in new_config.steps:
        step.tool_version = None

    save_workflow_config(new_workflow_dir, new_config)

    readme_path = new_workflow_dir / "README.md"
    if readme_path.exists():
        readme_content = readme_path.read_text()
        readme_content = readme_content.replace(source_config.id, new_id)
        readme_path.write_text(readme_content)

    return new_workflow_dir, new_config

"""Provenance tracking - capture git, tools, and environment metadata."""

import hashlib
import os
import platform
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

# Avoid circular import - define version inline
RAW_VERSION = "0.1.0"


def get_git_info() -> dict[str, Any]:
    """Capture git repository info (SHA, branch, dirty status).

    Returns empty dict if not in a git repository or git is unavailable.
    """
    try:
        # Check if in git repo
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode != 0:
            return {}

        # Get SHA
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        sha = sha_result.stdout.strip()

        # Get branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        branch = branch_result.stdout.strip()

        # Check if dirty (uncommitted changes)
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        dirty = bool(status_result.stdout.strip())

        return {
            "git_sha": sha,
            "git_branch": branch,
            "git_dirty": dirty,
        }

    except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
        return {}


def get_workflow_hash(workflow_path: Path) -> str | None:
    """Compute hash of workflow file for version tracking.

    Returns SHA256 hash of workflow run.py file.
    """
    try:
        if not workflow_path.exists():
            return None

        content = workflow_path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:16]

    except (OSError, IOError):
        return None


def get_tool_versions(tools_dir: Path | None = None) -> dict[str, str]:
    """Capture tool versions from tools/ directory.

    Returns dict of tool_name -> version_hash.
    """
    if tools_dir is None:
        tools_dir = Path.cwd() / "tools"

    if not tools_dir.exists():
        return {}

    tool_versions = {}

    for tool_path in tools_dir.iterdir():
        if not tool_path.is_dir():
            continue

        if tool_path.name.startswith("_") or tool_path.name.startswith("."):
            continue

        # Hash tool directory contents for version tracking
        try:
            tool_hash = _hash_directory(tool_path)
            tool_versions[tool_path.name] = tool_hash[:16]
        except (OSError, IOError):
            continue

    return tool_versions


def _hash_directory(directory: Path) -> str:
    """Compute hash of all files in directory."""
    hasher = hashlib.sha256()

    for file_path in sorted(directory.rglob("*")):
        if not file_path.is_file():
            continue

        if file_path.suffix in {".pyc", ".pyo", ".pyd"}:
            continue

        if "__pycache__" in file_path.parts:
            continue

        try:
            hasher.update(file_path.read_bytes())
        except (OSError, IOError):
            continue

    return hasher.hexdigest()


def get_environment_info() -> dict[str, Any]:
    """Capture environment metadata (hostname, Python version, etc.)."""
    return {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "raw_version": RAW_VERSION,
        "hostname": socket.gethostname(),
        "working_directory": str(Path.cwd()),
        "platform": platform.system(),
        "platform_release": platform.release(),
    }


def get_config_snapshot(redact_secrets: bool = True) -> dict[str, Any]:
    """Capture config snapshot (environment variables, redacted).

    Only captures RAW_* environment variables, redacts values if secrets.
    """
    config = {}

    for key, value in os.environ.items():
        if not key.startswith("RAW_"):
            continue

        # Redact secrets (anything with KEY, TOKEN, SECRET, PASSWORD)
        if redact_secrets and any(
            secret_word in key.upper() for secret_word in ["KEY", "TOKEN", "SECRET", "PASSWORD"]
        ):
            config[key] = "***REDACTED***"
        else:
            config[key] = value

    return config


def capture_provenance(workflow_path: Path | None = None) -> dict[str, Any]:
    """Capture all provenance metadata in one call.

    Returns dict suitable for WorkflowProvenanceEvent.
    """
    provenance = {}

    # Git info
    provenance.update(get_git_info())

    # Workflow hash
    if workflow_path:
        provenance["workflow_hash"] = get_workflow_hash(workflow_path)

    # Tool versions
    provenance["tool_versions"] = get_tool_versions()

    # Environment
    env_info = get_environment_info()
    provenance["python_version"] = env_info["python_version"]
    provenance["raw_version"] = env_info["raw_version"]
    provenance["hostname"] = env_info["hostname"]
    provenance["working_directory"] = env_info["working_directory"]

    # Config snapshot
    provenance["config_snapshot"] = get_config_snapshot(redact_secrets=True)

    return provenance


__all__ = [
    "get_git_info",
    "get_workflow_hash",
    "get_tool_versions",
    "get_environment_info",
    "get_config_snapshot",
    "capture_provenance",
]

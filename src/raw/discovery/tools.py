"""Tool dependency management for workflows.

Handles tool discovery, snapshotting, and import rewriting for workflows.
Separates tool management concerns from workflow discovery.
"""

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ToolManager:
    """Manages tool dependencies for workflows.

    Handles:
    - Finding tool imports in source code
    - Snapshotting tools into workflow directories
    - Creating origin metadata for reproducibility
    """

    def __init__(self, tools_dir: Path) -> None:
        """Initialize with the tools directory location.

        Args:
            tools_dir: Path to the tools/ directory
        """
        self._tools_dir = tools_dir

    @staticmethod
    def find_imports(source_code: str) -> list[str]:
        """Find tool imports in Python source code.

        Args:
            source_code: Python source code to scan

        Returns:
            List of unique tool names imported from tools.*
        """
        pattern = r"from\s+tools\.(\w+)\s+import"
        return list(set(re.findall(pattern, source_code)))

    def snapshot(
        self,
        workflow_dir: Path,
        git_hash: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Snapshot tools used by a workflow into _tools/ directory.

        Copies tool code and creates origin.json with git reference.

        Args:
            workflow_dir: Path to workflow directory
            git_hash: Git commit hash for provenance (optional)

        Returns:
            Dict mapping tool name to origin info
        """
        from raw.scaffold.init import calculate_tool_hash, load_tool_config

        snapshot_dir = workflow_dir / "_tools"
        run_py = workflow_dir / "run.py"

        if not run_py.exists():
            return {}

        content = run_py.read_text()
        tool_names = self.find_imports(content)

        if not tool_names:
            return {}

        # Clean and recreate snapshot directory
        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir)
        snapshot_dir.mkdir()
        (snapshot_dir / "__init__.py").write_text(
            '"""Snapshotted tools for this workflow."""\n'
        )

        snapshot_time = datetime.now(timezone.utc).isoformat()
        origins: dict[str, dict[str, Any]] = {}

        for tool_name in tool_names:
            src_tool_dir = self._tools_dir / tool_name
            if not src_tool_dir.exists():
                continue

            dst_tool_dir = snapshot_dir / tool_name

            # Copy tool directory
            shutil.copytree(src_tool_dir, dst_tool_dir)

            tool_config = load_tool_config(src_tool_dir)
            content_hash = calculate_tool_hash(src_tool_dir)

            origin = {
                "tool_name": tool_name,
                "tool_version": tool_config.version if tool_config else "unknown",
                "content_hash": content_hash,
                "git_commit": git_hash,
                "snapshot_time": snapshot_time,
                "source_path": str(src_tool_dir),
            }
            (dst_tool_dir / "origin.json").write_text(json.dumps(origin, indent=2))
            origins[tool_name] = origin

        # Rewrite imports to use _tools
        self._rewrite_imports(run_py, content)

        return origins

    @staticmethod
    def _rewrite_imports(run_py: Path, content: str) -> None:
        """Rewrite tool imports to use _tools directory.

        Args:
            run_py: Path to run.py file
            content: Original source code
        """
        new_content = re.sub(
            r"from\s+tools\.(\w+)\s+import",
            r"from _tools.\1 import",
            content,
        )
        run_py.write_text(new_content)


# Module-level convenience function for backward compatibility
def get_tool_manager(tools_dir: Path | None = None) -> ToolManager:
    """Get a ToolManager instance.

    Args:
        tools_dir: Tools directory path. If None, uses default from scaffold.

    Returns:
        ToolManager instance
    """
    if tools_dir is None:
        from raw.scaffold.init import get_tools_dir

        tools_dir = get_tools_dir()
    return ToolManager(tools_dir)

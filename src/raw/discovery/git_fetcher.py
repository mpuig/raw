"""Git-based tool fetcher for installing tools from remote repositories."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FetchResult:
    """Result of a tool fetch operation."""

    success: bool
    tool_path: Path | None = None
    error: str | None = None
    version: str | None = None


class GitToolFetcher:
    """Fetches tools from git repositories.

    Features:
    - Clone repos to tools/<name>
    - Support version tags, branches, and commits
    - Vendor mode: remove .git directory after clone
    """

    def __init__(self, tools_dir: Path | None = None) -> None:
        self._tools_dir = tools_dir or Path("tools")

    def fetch(
        self,
        git_url: str,
        name: str | None = None,
        ref: str | None = None,
        vendor: bool = True,
    ) -> FetchResult:
        """Fetch a tool from a git repository.

        Args:
            git_url: Git repository URL (https or ssh)
            name: Tool name (derived from URL if not provided)
            ref: Git ref to checkout (tag, branch, or commit). Defaults to HEAD.
            vendor: If True, remove .git directory after clone (default: True)

        Returns:
            FetchResult with success status and tool path
        """
        if not name:
            name = self._derive_name_from_url(git_url)

        tool_path = self._tools_dir / name

        if tool_path.exists():
            return FetchResult(
                success=False,
                error=f"Tool '{name}' already exists at {tool_path}",
            )

        self._tools_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._clone_repo(git_url, tool_path, ref)

            resolved_version = self._get_resolved_version(tool_path, ref)

            if vendor:
                self._vendor(tool_path)

            return FetchResult(
                success=True,
                tool_path=tool_path,
                version=resolved_version,
            )

        except subprocess.CalledProcessError as e:
            if tool_path.exists():
                shutil.rmtree(tool_path)
            return FetchResult(
                success=False,
                error=f"Git clone failed: {e.stderr or e.stdout or str(e)}",
            )
        except Exception as e:
            if tool_path.exists():
                shutil.rmtree(tool_path)
            return FetchResult(
                success=False,
                error=f"Failed to fetch tool: {e}",
            )

    def _derive_name_from_url(self, git_url: str) -> str:
        """Extract tool name from git URL."""
        url = git_url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]
        return url.split("/")[-1]

    def _clone_repo(self, git_url: str, target_path: Path, ref: str | None) -> None:
        """Clone a git repository."""
        clone_cmd = ["git", "clone", "--depth", "1"]

        if ref:
            clone_cmd.extend(["--branch", ref])

        clone_cmd.extend([git_url, str(target_path)])

        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0 and ref:
            clone_cmd = ["git", "clone", git_url, str(target_path)]
            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            checkout_result = subprocess.run(
                ["git", "-C", str(target_path), "checkout", ref],
                capture_output=True,
                text=True,
                check=True,
            )
            if checkout_result.returncode != 0:
                raise subprocess.CalledProcessError(
                    checkout_result.returncode,
                    checkout_result.args,
                    checkout_result.stdout,
                    checkout_result.stderr,
                )
        elif result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode,
                result.args,
                result.stdout,
                result.stderr,
            )

    def _get_resolved_version(self, repo_path: Path, ref: str | None) -> str:
        """Get the resolved version (commit SHA or tag)."""
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        commit_sha = result.stdout.strip()

        if ref:
            return f"{ref} ({commit_sha})"
        return commit_sha

    def _vendor(self, tool_path: Path) -> None:
        """Remove .git directory to vendor the tool."""
        git_dir = tool_path / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir)

    def update(
        self,
        name: str,
        ref: str | None = None,
    ) -> FetchResult:
        """Update an existing tool to a new version.

        For vendored tools (no .git), this removes and re-fetches.
        For non-vendored tools, this performs a git pull/checkout.
        """
        tool_path = self._tools_dir / name
        if not tool_path.exists():
            return FetchResult(
                success=False,
                error=f"Tool '{name}' not found at {tool_path}",
            )

        config_path = tool_path / "config.yaml"
        if not config_path.exists():
            return FetchResult(
                success=False,
                error=f"No config.yaml found in '{name}' - not a valid tool",
            )

        git_dir = tool_path / ".git"
        if not git_dir.exists():
            return FetchResult(
                success=False,
                error=f"Tool '{name}' is vendored. Remove and re-install to update.",
            )

        try:
            if ref:
                subprocess.run(
                    ["git", "-C", str(tool_path), "fetch", "--all"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                subprocess.run(
                    ["git", "-C", str(tool_path), "checkout", ref],
                    capture_output=True,
                    text=True,
                    check=True,
                )
            else:
                subprocess.run(
                    ["git", "-C", str(tool_path), "pull"],
                    capture_output=True,
                    text=True,
                    check=True,
                )

            resolved_version = self._get_resolved_version(tool_path, ref)

            return FetchResult(
                success=True,
                tool_path=tool_path,
                version=resolved_version,
            )
        except subprocess.CalledProcessError as e:
            return FetchResult(
                success=False,
                error=f"Git operation failed: {e.stderr or e.stdout or str(e)}",
            )

    def remove(self, name: str) -> FetchResult:
        """Remove an installed tool."""
        tool_path = self._tools_dir / name
        if not tool_path.exists():
            return FetchResult(
                success=False,
                error=f"Tool '{name}' not found at {tool_path}",
            )

        try:
            shutil.rmtree(tool_path)
            return FetchResult(success=True, tool_path=tool_path)
        except Exception as e:
            return FetchResult(
                success=False,
                error=f"Failed to remove tool: {e}",
            )

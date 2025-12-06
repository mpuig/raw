"""Tool Registry protocol and implementations.

The ToolRegistry provides an abstraction for tool discovery and management,
supporting both local tools and remote registries.
"""

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ToolInfo(BaseModel):
    """Information about a tool."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    source: str = "local"  # "local", "git", "registry"
    path: Path | None = None  # Local path if available
    git_url: str | None = None  # Git URL for remote tools
    git_ref: str | None = None  # Git ref (branch, tag, commit)
    dependencies: list[str] = Field(default_factory=list)
    inputs: list[dict[str, Any]] = Field(default_factory=list)
    outputs: list[dict[str, Any]] = Field(default_factory=list)


class SearchResult(BaseModel):
    """Result from a tool search."""

    tool: ToolInfo
    score: float = 1.0  # Relevance score (0-1)
    source: str = "local"  # Where the result came from


@runtime_checkable
class ToolRegistry(Protocol):
    """Protocol for tool registries.

    Implementations:
    - LocalToolRegistry: Scans tools/ directory
    - RemoteIndexRegistry: Fetches from remote JSON index
    - CompositeRegistry: Combines multiple registries
    """

    def list_tools(self) -> list[ToolInfo]:
        """List all available tools."""
        ...

    def get_tool(self, name: str) -> ToolInfo | None:
        """Get a tool by name."""
        ...

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search tools by description/name."""
        ...


class LocalToolRegistry:
    """Registry for local tools in tools/ directory."""

    def __init__(self, tools_dir: Path | None = None) -> None:
        """Initialize with tools directory path."""
        self._tools_dir = tools_dir or Path("tools")
        self._cache: dict[str, ToolInfo] | None = None

    def _load_tools(self) -> dict[str, ToolInfo]:
        """Load tool metadata from directory."""
        if self._cache is not None:
            return self._cache

        tools: dict[str, ToolInfo] = {}

        if not self._tools_dir.exists():
            self._cache = tools
            return tools

        for tool_dir in self._tools_dir.iterdir():
            if not tool_dir.is_dir() or tool_dir.name.startswith((".", "_")):
                continue

            config_path = tool_dir / "config.yaml"
            if not config_path.exists():
                continue

            try:
                import yaml

                with open(config_path) as f:
                    config = yaml.safe_load(f)

                tools[config["name"]] = ToolInfo(
                    name=config["name"],
                    version=config.get("version", "1.0.0"),
                    description=config.get("description", ""),
                    source="local",
                    path=tool_dir,
                    dependencies=config.get("dependencies", []),
                    inputs=config.get("inputs", []),
                    outputs=config.get("outputs", []),
                )
            except Exception:
                continue

        self._cache = tools
        return tools

    def invalidate_cache(self) -> None:
        """Clear the cached tool list."""
        self._cache = None

    def list_tools(self) -> list[ToolInfo]:
        """List all local tools."""
        return list(self._load_tools().values())

    def get_tool(self, name: str) -> ToolInfo | None:
        """Get a tool by name."""
        return self._load_tools().get(name)

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search tools by description/name (simple substring match)."""
        query_lower = query.lower()
        results: list[SearchResult] = []

        for tool in self._load_tools().values():
            # Simple relevance scoring
            score = 0.0
            if query_lower in tool.name.lower():
                score = 0.9
            elif query_lower in tool.description.lower():
                score = 0.7

            if score > 0:
                results.append(SearchResult(tool=tool, score=score, source="local"))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]


class CompositeRegistry:
    """Combines multiple registries for unified search."""

    def __init__(self, registries: list[ToolRegistry]) -> None:
        """Initialize with list of registries."""
        self._registries = registries

    def list_tools(self) -> list[ToolInfo]:
        """List tools from all registries."""
        seen: set[str] = set()
        tools: list[ToolInfo] = []

        for registry in self._registries:
            for tool in registry.list_tools():
                if tool.name not in seen:
                    seen.add(tool.name)
                    tools.append(tool)

        return tools

    def get_tool(self, name: str) -> ToolInfo | None:
        """Get tool from first registry that has it."""
        for registry in self._registries:
            tool = registry.get_tool(name)
            if tool:
                return tool
        return None

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search all registries and merge results."""
        all_results: list[SearchResult] = []
        seen: set[str] = set()

        for registry in self._registries:
            for result in registry.search(query, limit=limit * 2):
                if result.tool.name not in seen:
                    seen.add(result.tool.name)
                    all_results.append(result)

        all_results.sort(key=lambda r: r.score, reverse=True)
        return all_results[:limit]


# Global registry instance
_tool_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _tool_registry
    if _tool_registry is None:
        # Default to local tools/ registry
        _tool_registry = LocalToolRegistry(Path("tools"))
    return _tool_registry


def set_tool_registry(registry: ToolRegistry | None) -> None:
    """Set the global tool registry."""
    global _tool_registry
    _tool_registry = registry

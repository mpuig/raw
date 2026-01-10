"""Builder tool definitions and handlers."""

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from anthropic.types import ToolParam, ToolUseBlock


def get_builder_tools() -> list[ToolParam]:
    """Get tool definitions for builder agent.

    Returns:
        List of Anthropic tool schemas
    """
    return [
        {
            "name": "read_file",
            "description": "Read the contents of a file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file to read (relative to project root)",
                    },
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "write_file",
            "description": "Write content to a file (creates or overwrites)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file to write (relative to project root)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to file",
                    },
                },
                "required": ["file_path", "content"],
            },
        },
        {
            "name": "edit_file",
            "description": "Edit a file by replacing old_string with new_string",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file to edit",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "String to replace",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "Replacement string",
                    },
                },
                "required": ["file_path", "old_string", "new_string"],
            },
        },
        {
            "name": "run_command",
            "description": "Run a shell command (for git, mkdir, etc.)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory (defaults to project root)",
                    },
                },
                "required": ["command"],
            },
        },
        {
            "name": "list_directory",
            "description": "List files in a directory",
            "input_schema": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory path to list",
                    },
                },
                "required": ["directory"],
            },
        },
        {
            "name": "search_files",
            "description": "Search for files matching a pattern",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g., '**/*.py', '*.md')",
                    },
                    "directory": {
                        "type": "string",
                        "description": "Directory to search (defaults to project root)",
                    },
                },
                "required": ["pattern"],
            },
        },
    ]


async def handle_tool_call(tool_use: ToolUseBlock, workflow_id: str) -> str:
    """Execute a tool call and return result.

    Args:
        tool_use: Tool use block from LLM
        workflow_id: Current workflow being built

    Returns:
        Tool result as string

    Raises:
        ValueError: If tool not found or parameters invalid
    """
    tool_name = tool_use.name
    params = tool_use.input

    # Get project root and workflow directory
    project_root = Path.cwd()
    workflow_dir = project_root / ".raw" / "workflows" / workflow_id

    # Route to appropriate handler
    if tool_name == "read_file":
        return await _read_file(params["file_path"], project_root)

    elif tool_name == "write_file":
        return await _write_file(params["file_path"], params["content"], project_root)

    elif tool_name == "edit_file":
        return await _edit_file(
            params["file_path"],
            params["old_string"],
            params["new_string"],
            project_root,
        )

    elif tool_name == "run_command":
        cwd = params.get("cwd", str(project_root))
        return await _run_command(params["command"], cwd)

    elif tool_name == "list_directory":
        return await _list_directory(params["directory"], project_root)

    elif tool_name == "search_files":
        directory = params.get("directory", str(project_root))
        return await _search_files(params["pattern"], directory)

    else:
        raise ValueError(f"Unknown tool: {tool_name}")


async def _read_file(file_path: str, project_root: Path) -> str:
    """Read file contents."""
    path = project_root / file_path
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = path.read_text()
    return f"Contents of {file_path}:\n\n{content}"


async def _write_file(file_path: str, content: str, project_root: Path) -> str:
    """Write file contents."""
    path = project_root / file_path

    # Create parent directories
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    path.write_text(content)

    return f"Wrote {len(content)} bytes to {file_path}"


async def _edit_file(
    file_path: str,
    old_string: str,
    new_string: str,
    project_root: Path,
) -> str:
    """Edit file by replacing string."""
    path = project_root / file_path
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = path.read_text()

    # Check if old_string exists
    if old_string not in content:
        raise ValueError(f"String not found in {file_path}: {old_string[:100]}...")

    # Replace
    new_content = content.replace(old_string, new_string, 1)
    path.write_text(new_content)

    return f"Replaced text in {file_path}"


async def _run_command(command: str, cwd: str) -> str:
    """Run shell command."""
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )

    stdout, stderr = await process.communicate()

    output = stdout.decode() + stderr.decode()

    if process.returncode != 0:
        raise RuntimeError(f"Command failed (exit {process.returncode}): {output}")

    return f"Command output:\n{output}"


async def _list_directory(directory: str, project_root: Path) -> str:
    """List directory contents."""
    path = project_root / directory
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not path.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    entries = []
    for item in sorted(path.iterdir()):
        prefix = "[DIR]" if item.is_dir() else "[FILE]"
        entries.append(f"{prefix} {item.name}")

    return f"Contents of {directory}:\n" + "\n".join(entries)


async def _search_files(pattern: str, directory: str) -> str:
    """Search for files matching pattern."""
    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    matches = sorted(path.glob(pattern))

    if not matches:
        return f"No files found matching '{pattern}' in {directory}"

    files = [str(m.relative_to(path)) for m in matches]
    return f"Found {len(files)} files matching '{pattern}':\n" + "\n".join(files[:50])

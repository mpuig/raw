"""Tests for builder mode enforcement."""

import pytest

from raw.builder.mode import (
    BuildMode,
    get_mode_description,
    is_destructive_command,
    is_write_operation,
    load_execute_mode_prompt,
    load_plan_mode_prompt,
    validate_tool_call_in_plan_mode,
)


def test_load_plan_mode_prompt():
    """Test loading plan mode prompt."""
    prompt = load_plan_mode_prompt()

    assert "PLAN MODE ACTIVE" in prompt
    assert "READ-ONLY" in prompt
    assert "FORBIDDEN" in prompt
    assert "ALLOWED" in prompt
    assert "REQUIRED OUTPUT" in prompt


def test_load_execute_mode_prompt():
    """Test loading execute mode prompt with context."""
    plan = """
## Steps
1. Update run.py
2. Add tests
"""
    gates = ["validate", "dry", "pytest"]

    prompt = load_execute_mode_prompt(plan, gates)

    assert "EXECUTE MODE" in prompt
    assert "FULL ACCESS" in prompt
    assert "Update run.py" in prompt
    assert "- validate" in prompt
    assert "- dry" in prompt
    assert "- pytest" in prompt


def test_is_write_operation():
    """Test identifying write tools."""
    assert is_write_operation("Write") is True
    assert is_write_operation("Edit") is True
    assert is_write_operation("NotebookEdit") is True
    assert is_write_operation("TodoWrite") is True

    assert is_write_operation("Read") is False
    assert is_write_operation("Bash") is False
    assert is_write_operation("Glob") is False
    assert is_write_operation("Grep") is False


def test_is_destructive_command():
    """Test identifying destructive bash commands."""
    # Destructive commands
    assert is_destructive_command("rm -rf /tmp/file") is True
    assert is_destructive_command("mv old.txt new.txt") is True
    assert is_destructive_command("cp source dest") is True
    assert is_destructive_command("echo 'text' > file.txt") is True
    assert is_destructive_command("echo 'text' >> file.txt") is True
    assert is_destructive_command("git commit -m 'message'") is True
    assert is_destructive_command("git push origin main") is True
    assert is_destructive_command("npm install package") is True
    assert is_destructive_command("pip install requests") is True

    # Read-only commands
    assert is_destructive_command("ls -la") is False
    assert is_destructive_command("cat file.txt") is False
    assert is_destructive_command("grep pattern file") is False
    assert is_destructive_command("find . -name '*.py'") is False
    assert is_destructive_command("git log") is False
    assert is_destructive_command("git status") is False
    assert is_destructive_command("git diff") is False


def test_validate_tool_call_write_tools():
    """Test validating write tool calls in plan mode."""
    # Write tools should be blocked
    allowed, error = validate_tool_call_in_plan_mode("Write", {"file_path": "test.py"})
    assert allowed is False
    assert "write operations" in error.lower()

    allowed, error = validate_tool_call_in_plan_mode("Edit", {"file_path": "test.py"})
    assert allowed is False
    assert "write operations" in error.lower()


def test_validate_tool_call_destructive_bash():
    """Test validating destructive bash commands in plan mode."""
    # Destructive commands should be blocked
    allowed, error = validate_tool_call_in_plan_mode("Bash", {"command": "rm file.txt"})
    assert allowed is False
    assert "destructive" in error.lower()

    allowed, error = validate_tool_call_in_plan_mode(
        "Bash", {"command": "git commit -m 'test'"}
    )
    assert allowed is False
    assert "destructive" in error.lower()


def test_validate_tool_call_read_tools():
    """Test validating read tool calls in plan mode."""
    # Read tools should be allowed
    allowed, error = validate_tool_call_in_plan_mode("Read", {"file_path": "test.py"})
    assert allowed is True
    assert error is None

    allowed, error = validate_tool_call_in_plan_mode("Glob", {"pattern": "*.py"})
    assert allowed is True
    assert error is None

    allowed, error = validate_tool_call_in_plan_mode("Grep", {"pattern": "def "})
    assert allowed is True
    assert error is None


def test_validate_tool_call_safe_bash():
    """Test validating safe bash commands in plan mode."""
    # Safe commands should be allowed
    allowed, error = validate_tool_call_in_plan_mode("Bash", {"command": "ls -la"})
    assert allowed is True
    assert error is None

    allowed, error = validate_tool_call_in_plan_mode("Bash", {"command": "git status"})
    assert allowed is True
    assert error is None

    allowed, error = validate_tool_call_in_plan_mode("Bash", {"command": "cat file.txt"})
    assert allowed is True
    assert error is None


def test_get_mode_description():
    """Test getting mode descriptions."""
    plan_desc = get_mode_description(BuildMode.PLAN)
    assert "PLAN" in plan_desc
    assert "read-only" in plan_desc

    execute_desc = get_mode_description(BuildMode.EXECUTE)
    assert "EXECUTE" in execute_desc
    assert "full access" in execute_desc


def test_build_mode_enum():
    """Test BuildMode enum values."""
    assert BuildMode.PLAN.value == "plan"
    assert BuildMode.EXECUTE.value == "execute"

    # Test enum conversion
    assert BuildMode.PLAN == "plan"
    assert BuildMode.EXECUTE == "execute"

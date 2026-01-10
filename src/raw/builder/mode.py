"""Builder mode management - plan vs execute mode enforcement."""

from enum import Enum
from pathlib import Path


class BuildMode(str, Enum):
    """Builder execution modes."""

    PLAN = "plan"
    EXECUTE = "execute"


def load_plan_mode_prompt() -> str:
    """Load plan mode system prompt.

    Returns:
        Plan mode prompt text with constraints
    """
    prompt_path = Path(__file__).parent / "prompts" / "plan_mode.txt"
    return prompt_path.read_text()


def load_execute_mode_prompt(plan: str, gates: list[str]) -> str:
    """Load execute mode system prompt with plan context.

    Args:
        plan: The approved plan from plan mode
        gates: List of quality gates to run

    Returns:
        Execute mode prompt with plan and gates injected
    """
    prompt_path = Path(__file__).parent / "prompts" / "execute_mode.txt"
    template = prompt_path.read_text()

    # Format gates list
    gate_list = ", ".join(gates) if gates else "validate, dry"

    # Inject plan and gates
    return template.format(
        plan=plan,
        gates="\n".join(f"- {gate}" for gate in gates),
        gate_list=gate_list,
    )


def is_write_operation(tool_name: str) -> bool:
    """Check if a tool performs write operations.

    Args:
        tool_name: Name of the tool being called

    Returns:
        True if tool modifies state
    """
    write_tools = {
        "Write",
        "Edit",
        "NotebookEdit",
        "TodoWrite",
    }

    return tool_name in write_tools


def is_destructive_command(command: str) -> bool:
    """Check if a bash command is destructive.

    Args:
        command: Shell command to check

    Returns:
        True if command modifies state
    """
    # Destructive command patterns
    destructive_patterns = [
        "rm ",
        "mv ",
        "cp ",
        "dd ",
        "mkfs",
        "format",
        "> ",  # Redirect (overwrite)
        ">> ",  # Redirect (append)
        "git commit",
        "git push",
        "git merge",
        "git rebase",
        "npm install",
        "pip install",
        "apt install",
        "brew install",
        "cargo install",
    ]

    command_lower = command.lower().strip()

    for pattern in destructive_patterns:
        if pattern in command_lower:
            return True

    return False


def validate_tool_call_in_plan_mode(tool_name: str, arguments: dict) -> tuple[bool, str | None]:
    """Validate if a tool call is allowed in plan mode.

    Args:
        tool_name: Name of tool being called
        arguments: Tool arguments

    Returns:
        Tuple of (allowed, error_message)
    """
    # Check write operations
    if is_write_operation(tool_name):
        return False, f"Tool '{tool_name}' performs write operations (forbidden in PLAN mode)"

    # Check bash commands
    if tool_name == "Bash":
        command = arguments.get("command", "")
        if is_destructive_command(command):
            return (
                False,
                f"Command '{command}' is destructive (forbidden in PLAN mode)",
            )

    # Allow by default
    return True, None


def get_mode_description(mode: BuildMode) -> str:
    """Get human-readable description of mode.

    Args:
        mode: Build mode

    Returns:
        Description string
    """
    if mode == BuildMode.PLAN:
        return "PLAN mode (read-only, creating numbered plan with gates)"
    else:
        return "EXECUTE mode (full access, implementing approved plan)"

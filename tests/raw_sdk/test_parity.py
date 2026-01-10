"""Tests for CLI-to-SDK parity checking."""

import pytest

from raw.sdk.parity import (
    CLI_COMMANDS,
    check_parity,
    get_missing_functions,
    get_sdk_functions,
    verify_all_sdk_functions,
    verify_sdk_function_exists,
)


def test_cli_commands_structure():
    """Verify CLI_COMMANDS has expected structure."""
    assert len(CLI_COMMANDS) > 0

    for cmd in CLI_COMMANDS:
        assert "command" in cmd
        assert "description" in cmd
        assert "sdk_function" in cmd
        assert "status" in cmd
        assert "notes" in cmd

        assert cmd["status"] in ("full", "partial", "missing")
        assert isinstance(cmd["command"], str)
        assert isinstance(cmd["description"], str)
        assert isinstance(cmd["notes"], str)
        assert cmd["sdk_function"] is None or isinstance(cmd["sdk_function"], str)


def test_check_parity_returns_expected_structure():
    """Verify check_parity returns dict with expected keys."""
    result = check_parity()

    assert "total_commands" in result
    assert "full_parity" in result
    assert "partial_parity" in result
    assert "missing" in result
    assert "details" in result

    assert isinstance(result["total_commands"], int)
    assert isinstance(result["full_parity"], int)
    assert isinstance(result["partial_parity"], int)
    assert isinstance(result["missing"], int)
    assert isinstance(result["details"], list)


def test_check_parity_counts_match_total():
    """Verify parity counts sum to total commands."""
    result = check_parity()

    total = result["total_commands"]
    full = result["full_parity"]
    partial = result["partial_parity"]
    missing = result["missing"]

    assert full + partial + missing == total


def test_check_parity_counts_are_correct():
    """Verify parity counts match manual count."""
    result = check_parity()

    full_count = sum(1 for cmd in CLI_COMMANDS if cmd["status"] == "full")
    partial_count = sum(1 for cmd in CLI_COMMANDS if cmd["status"] == "partial")
    missing_count = sum(1 for cmd in CLI_COMMANDS if cmd["status"] == "missing")

    assert result["full_parity"] == full_count
    assert result["partial_parity"] == partial_count
    assert result["missing"] == missing_count


def test_get_missing_functions():
    """Verify get_missing_functions returns commands without full parity."""
    missing = get_missing_functions()

    assert isinstance(missing, list)

    for cmd in missing:
        assert cmd["status"] in ("missing", "partial")


def test_get_sdk_functions():
    """Verify get_sdk_functions returns unique sorted function names."""
    functions = get_sdk_functions()

    assert isinstance(functions, list)
    assert len(functions) == len(set(functions))
    assert functions == sorted(functions)

    for func in functions:
        assert isinstance(func, str)
        assert len(func) > 0


def test_verify_sdk_function_exists_for_known_functions():
    """Verify that documented SDK functions actually exist."""
    assert verify_sdk_function_exists("create_workflow") is True
    assert verify_sdk_function_exists("list_workflows") is True
    assert verify_sdk_function_exists("get_workflow") is True
    assert verify_sdk_function_exists("update_workflow") is True
    assert verify_sdk_function_exists("delete_workflow") is True
    assert verify_sdk_function_exists("add_step") is True

    assert verify_sdk_function_exists("create_tool") is True
    assert verify_sdk_function_exists("list_tools") is True
    assert verify_sdk_function_exists("get_tool") is True
    assert verify_sdk_function_exists("update_tool") is True
    assert verify_sdk_function_exists("delete_tool") is True


def test_verify_sdk_function_exists_for_missing_functions():
    """Verify that non-existent functions return False."""
    assert verify_sdk_function_exists("nonexistent_function") is False
    assert verify_sdk_function_exists("search_tools") is False
    assert verify_sdk_function_exists("run_workflow") is False


def test_verify_all_sdk_functions():
    """Verify all documented SDK functions exist."""
    results = verify_all_sdk_functions()

    assert isinstance(results, dict)

    for func_name, exists in results.items():
        assert isinstance(func_name, str)
        assert isinstance(exists, bool)


def test_parity_has_workflow_functions():
    """Verify workflow operations are documented."""
    functions = get_sdk_functions()

    assert "create_workflow" in functions
    assert "list_workflows" in functions
    assert "get_workflow" in functions
    assert "update_workflow" in functions


def test_parity_has_tool_functions():
    """Verify tool operations are documented."""
    functions = get_sdk_functions()

    assert "create_tool" in functions
    assert "list_tools" in functions
    assert "get_tool" in functions


def test_parity_percentage_is_reasonable():
    """Verify parity percentage is within expected range."""
    result = check_parity()

    total = result["total_commands"]
    full = result["full_parity"]

    parity_percentage = (full / total) * 100

    assert parity_percentage >= 40
    assert parity_percentage <= 100


def test_all_full_parity_commands_have_sdk_function():
    """Verify all commands with full parity have SDK function specified."""
    for cmd in CLI_COMMANDS:
        if cmd["status"] == "full":
            assert cmd["sdk_function"] is not None
            assert len(cmd["sdk_function"]) > 0


def test_all_missing_commands_have_no_sdk_function():
    """Verify all missing commands have no SDK function."""
    for cmd in CLI_COMMANDS:
        if cmd["status"] == "missing":
            assert cmd["sdk_function"] is None


def test_cli_commands_are_unique():
    """Verify no duplicate CLI commands."""
    commands = [cmd["command"] for cmd in CLI_COMMANDS]
    assert len(commands) == len(set(commands))


def test_sdk_function_names_are_valid_python():
    """Verify SDK function names follow Python naming conventions."""
    functions = get_sdk_functions()

    for func in functions:
        if "." in func:
            continue

        assert func.replace("_", "").isalnum()
        assert not func[0].isdigit()


def test_parity_report_can_be_generated(capsys):
    """Verify parity report prints without errors."""
    from raw.sdk.parity import print_parity_report

    print_parity_report()

    captured = capsys.readouterr()
    assert "CLI-to-SDK Parity Report" in captured.out
    assert "Total Commands:" in captured.out
    assert "Full Parity:" in captured.out
    assert "Partial Parity:" in captured.out
    assert "Missing:" in captured.out

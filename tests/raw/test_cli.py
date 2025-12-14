"""Tests for RAW CLI."""

import pytest
from pathlib import Path

from typer.testing import CliRunner

from raw.cli import app
from raw.scaffold.init import sanitize_tool_name


def test_version() -> None:
    """Test --version flag."""
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_help() -> None:
    """Test --help flag."""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "RAW - Run Agentic Workflows" in result.output


def test_init_command(tmp_path: Path) -> None:
    """Test init command."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "Initialized RAW" in result.output

        raw_dir = Path(".raw")
        assert raw_dir.exists()
        assert (raw_dir / "config.yaml").exists()
        assert (raw_dir / "libraries.yaml").exists()
        assert (raw_dir / "workflows").exists()
        assert (raw_dir / "cache").exists()
        assert (raw_dir / "logs").exists()

        # Tools live in tools/ at project root (not in .raw/)
        tools_dir = Path("tools")
        assert tools_dir.exists()
        assert (tools_dir / "__init__.py").exists()

        readme = raw_dir / "README.md"
        assert readme.exists()
        content = readme.read_text()
        assert "raw onboard" in content
        assert "raw prime" in content


def test_init_command_already_initialized(tmp_path: Path) -> None:
    """Test init command when already initialized."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "already initialized" in result.output


def test_onboard_command(tmp_path: Path) -> None:
    """Test onboard command creates AGENTS.md with agent integration instructions."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Provide 'y' input to confirm creation
        result = runner.invoke(app, ["onboard"], input="y\n")
        assert result.exit_code == 0
        assert "AGENTS.md" in result.output

        # Check AGENTS.md was created with expected content
        agents_md = Path("AGENTS.md")
        assert agents_md.exists()
        content = agents_md.read_text()
        assert "RAW (Run Agentic Workflows)" in content
        assert "SEARCH FIRST" in content
        assert "tools/" in content


def test_prime_command_not_initialized(tmp_path: Path) -> None:
    """Test prime command when not initialized."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(app, ["prime"])
        assert result.exit_code == 1
        assert "not initialized" in result.output


def test_prime_command_empty(tmp_path: Path) -> None:
    """Test prime command with no workflows or tools."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["prime"])
        assert result.exit_code == 0
        assert "RAW Context" in result.output
        assert "Quick Reference" in result.output
        assert "SEARCH FIRST" in result.output


def test_prime_command_with_content(tmp_path: Path) -> None:
    """Test prime command with workflows and tools."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(app, ["init"])
        runner.invoke(app, ["create", "test-wf", "-i", "Test workflow intent"])
        runner.invoke(app, ["create", "test-tool", "--tool", "-d", "Test tool"])

        result = runner.invoke(app, ["prime"])
        assert result.exit_code == 0
        assert "Workflows (1)" in result.output
        assert "test-wf" in result.output
        assert "Tools (1)" in result.output
        assert "test_tool" in result.output  # Tool name sanitized to underscore


def test_create_command(tmp_path: Path) -> None:
    """Test create command with v0.2.0 prompt-first approach."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(app, ["init"])

        # v0.2.0: create draft workflow with intent
        result = runner.invoke(
            app,
            ["create", "test-workflow", "--intent", "Analyze stock prices"],
        )
        assert result.exit_code == 0
        assert "Draft workflow created" in result.output
        assert "test-workflow" in result.output

        workflows_dir = Path(".raw/workflows")
        assert workflows_dir.exists()
        workflow_dirs = list(workflows_dir.iterdir())
        assert len(workflow_dirs) == 1
        workflow_dir = workflow_dirs[0]
        assert (workflow_dir / "config.yaml").exists()
        assert (workflow_dir / "README.md").exists()
        assert (workflow_dir / "mocks").exists()


def test_create_command_scaffold(tmp_path: Path) -> None:
    """Test create command with legacy scaffold mode."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(app, ["init"])

        result = runner.invoke(app, ["create", "test-workflow", "--scaffold"])
        assert result.exit_code == 0
        assert "Workflow created successfully" in result.output

        workflows_dir = Path(".raw/workflows")
        workflow_dirs = list(workflows_dir.iterdir())
        workflow_dir = workflow_dirs[0]
        assert (workflow_dir / "run.py").exists()
        assert (workflow_dir / "test.py").exists()
        assert (workflow_dir / "dry_run.py").exists()


def test_run_command_not_found() -> None:
    """Test run command with non-existent workflow."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["run", "nonexistent-id"])
        assert result.exit_code == 1
        assert "Workflow not found" in result.output


def test_show_runs_command_not_found() -> None:
    """Test show --runs command with non-existent workflow."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["show", "nonexistent-id", "--runs"])
        assert result.exit_code == 1
        assert "Workflow not found" in result.output


def test_list_command_empty() -> None:
    """Test list command with no workflows."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No workflows found" in result.output


def test_list_command_with_workflows(tmp_path: Path) -> None:
    """Test list command with workflows."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Init and create a workflow
        runner.invoke(app, ["init"])
        runner.invoke(app, ["create", "my-workflow", "-i", "Test workflow"])

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "my-workflow" in result.output


def test_run_dry_command(tmp_path: Path) -> None:
    """Test run --dry command (scaffold mode)."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Init and create workflow using scaffold mode (has dry_run.py)
        runner.invoke(app, ["init"])
        create_result = runner.invoke(app, ["create", "test-wf", "--scaffold"])
        assert create_result.exit_code == 0

        workflows_dir = Path(".raw/workflows")
        workflow_dirs = list(workflows_dir.iterdir())
        workflow_id = workflow_dirs[0].name

        dry_run_result = runner.invoke(app, ["run", workflow_id, "--dry"])
        # Should complete (even if script has issues, the command itself should work)
        assert "Dry-run workflow" in dry_run_result.output


def test_create_and_show_runs_no_history(tmp_path: Path) -> None:
    """Test show --runs command on workflow with no execution history."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Init and create workflow
        runner.invoke(app, ["init"])
        runner.invoke(app, ["create", "test-wf", "-i", "Test intent"])

        workflows_dir = Path(".raw/workflows")
        workflow_dirs = list(workflows_dir.iterdir())
        workflow_id = workflow_dirs[0].name

        status_result = runner.invoke(app, ["show", workflow_id, "--runs"])
        assert status_result.exit_code == 0
        assert "No execution history" in status_result.output


def test_create_tool_command(tmp_path: Path) -> None:
    """Test create --tool command creates scaffold only."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(app, ["init"])

        # Input name uses hyphen, but tool directory uses underscore (Python module)
        result = runner.invoke(
            app,
            ["create", "my-tool", "--tool", "-d", "A test tool"],
        )
        assert result.exit_code == 0
        assert "scaffold created" in result.output
        assert "my_tool" in result.output  # Sanitized to underscore

        tool_dir = Path("tools/my_tool")
        assert tool_dir.exists()
        # Only config.yaml is created - skill implements the rest
        assert (tool_dir / "config.yaml").exists()
        assert not (tool_dir / "tool.py").exists()
        assert not (tool_dir / "test.py").exists()
        assert not (tool_dir / "README.md").exists()


def test_create_tool_duplicate(tmp_path: Path) -> None:
    """Test create --tool fails for duplicate tool name."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(app, ["init"])
        runner.invoke(app, ["create", "my_tool", "--tool", "-d", "First tool"])

        result = runner.invoke(
            app,
            ["create", "my_tool", "--tool", "-d", "Duplicate tool"],
        )
        assert result.exit_code == 1
        assert "already exists" in result.output


@pytest.mark.parametrize(
    "input_name,expected",
    [
        ("web-scraper", "web_scraper"),
        ("llm-client", "llm_client"),
        ("slack-notifier", "slack_notifier"),
        ("my_tool", "my_tool"),
        ("MyTool", "mytool"),
        ("web scraper", "web_scraper"),
        ("web--scraper", "web_scraper"),
        ("web__scraper", "web_scraper"),
        ("-leading", "leading"),
        ("trailing-", "trailing"),
        ("special!@#chars", "specialchars"),
    ],
)
def test_sanitize_tool_name(input_name: str, expected: str) -> None:
    """Test tool name sanitization uses underscores for Python module compatibility."""
    assert sanitize_tool_name(input_name) == expected


def test_list_tools_command(tmp_path: Path) -> None:
    """Test list tools command."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(app, ["init"])
        runner.invoke(app, ["create", "tool-one", "--tool", "-d", "First tool"])
        runner.invoke(app, ["create", "tool-two", "--tool", "-d", "Second tool"])

        result = runner.invoke(app, ["list", "tools"])
        assert result.exit_code == 0
        assert "tool_one" in result.output
        assert "tool_two" in result.output


def test_publish_command(tmp_path: Path) -> None:
    """Test publish command."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(app, ["init"])
        runner.invoke(app, ["create", "test-wf", "--scaffold"])

        workflows_dir = Path(".raw/workflows")
        workflow_id = list(workflows_dir.iterdir())[0].name

        result = runner.invoke(app, ["publish", workflow_id])
        assert result.exit_code == 0
        assert "Workflow published" in result.output


def test_publish_fails_without_code(tmp_path: Path) -> None:
    """Test publish fails for draft workflow without generated code."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(app, ["init"])
        runner.invoke(app, ["create", "test-wf", "-i", "Test intent"])

        workflows_dir = Path(".raw/workflows")
        workflow_id = list(workflows_dir.iterdir())[0].name

        result = runner.invoke(app, ["publish", workflow_id])
        assert result.exit_code == 1
        assert "no generated code" in result.output


def test_create_from_command(tmp_path: Path) -> None:
    """Test create --from command (duplicates workflow)."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(app, ["init"])
        runner.invoke(app, ["create", "test-wf", "--scaffold"])

        workflows_dir = Path(".raw/workflows")
        original_id = list(workflows_dir.iterdir())[0].name

        runner.invoke(app, ["publish", original_id])

        result = runner.invoke(app, ["create", "new-wf", "--from", original_id])
        assert result.exit_code == 0
        assert "Workflow duplicated" in result.output

        assert len(list(workflows_dir.iterdir())) == 2


def test_run_dry_init(tmp_path: Path) -> None:
    """Test run --dry --init generates template."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(app, ["init"])
        runner.invoke(app, ["create", "test-wf", "-i", "Test intent"])

        workflows_dir = Path(".raw/workflows")
        workflow_id = list(workflows_dir.iterdir())[0].name
        workflow_dir = workflows_dir / workflow_id

        assert not (workflow_dir / "dry_run.py").exists()

        result = runner.invoke(app, ["run", workflow_id, "--dry", "--init"])
        assert result.exit_code == 0
        assert "Generated dry_run.py" in result.output

        assert (workflow_dir / "dry_run.py").exists()
        assert (workflow_dir / "mocks").exists()
        assert (workflow_dir / "mocks" / "example.json").exists()


def test_run_dry_no_script_error(tmp_path: Path) -> None:
    """Test run --dry without dry_run.py shows helpful error."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(app, ["init"])
        runner.invoke(app, ["create", "test-wf", "-i", "Test intent"])

        workflows_dir = Path(".raw/workflows")
        workflow_id = list(workflows_dir.iterdir())[0].name

        result = runner.invoke(app, ["run", workflow_id, "--dry"])
        assert result.exit_code == 1
        assert "dry_run.py not found" in result.output
        assert "--init" in result.output

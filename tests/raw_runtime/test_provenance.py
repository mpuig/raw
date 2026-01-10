"""Tests for provenance tracking."""

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from raw_runtime.provenance import (
    capture_provenance,
    get_config_snapshot,
    get_environment_info,
    get_git_info,
    get_tool_versions,
    get_workflow_hash,
)


class TestGetGitInfo:
    """Tests for get_git_info()."""

    def test_get_git_info_in_repo(self) -> None:
        """Test git info capture in a real repo."""
        git_info = get_git_info()

        # Should return dict (may be empty if not in git repo)
        assert isinstance(git_info, dict)

        # If in git repo, should have SHA and branch
        if git_info:
            assert "git_sha" in git_info
            assert "git_branch" in git_info
            assert "git_dirty" in git_info
            assert isinstance(git_info["git_sha"], str)
            assert isinstance(git_info["git_branch"], str)
            assert isinstance(git_info["git_dirty"], bool)

    @patch("subprocess.run")
    def test_get_git_info_not_in_repo(self, mock_run) -> None:
        """Test git info when not in a repo."""
        mock_run.return_value.returncode = 1
        git_info = get_git_info()
        assert git_info == {}

    @patch("subprocess.run")
    def test_get_git_info_timeout(self, mock_run) -> None:
        """Test git info handles timeout gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 2)
        git_info = get_git_info()
        assert git_info == {}


class TestGetWorkflowHash:
    """Tests for get_workflow_hash()."""

    def test_get_workflow_hash(self, tmp_path: Path) -> None:
        """Test workflow hash generation."""
        workflow_file = tmp_path / "run.py"
        workflow_file.write_text("# Test workflow\n")

        hash_result = get_workflow_hash(workflow_file)
        assert hash_result is not None
        assert len(hash_result) == 16  # First 16 chars of SHA256

    def test_get_workflow_hash_missing_file(self, tmp_path: Path) -> None:
        """Test workflow hash when file doesn't exist."""
        workflow_file = tmp_path / "missing.py"
        hash_result = get_workflow_hash(workflow_file)
        assert hash_result is None


class TestGetToolVersions:
    """Tests for get_tool_versions()."""

    def test_get_tool_versions_empty_dir(self, tmp_path: Path) -> None:
        """Test tool versions with empty tools dir."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        versions = get_tool_versions(tools_dir)
        assert versions == {}

    def test_get_tool_versions_with_tools(self, tmp_path: Path) -> None:
        """Test tool versions with actual tools."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        # Create tool1
        tool1_dir = tools_dir / "tool1"
        tool1_dir.mkdir()
        (tool1_dir / "tool.py").write_text("# Tool 1\n")

        # Create tool2
        tool2_dir = tools_dir / "tool2"
        tool2_dir.mkdir()
        (tool2_dir / "tool.py").write_text("# Tool 2\n")

        versions = get_tool_versions(tools_dir)
        assert len(versions) == 2
        assert "tool1" in versions
        assert "tool2" in versions
        assert len(versions["tool1"]) == 16
        assert len(versions["tool2"]) == 16

    def test_get_tool_versions_ignores_pycache(self, tmp_path: Path) -> None:
        """Test tool versions ignores __pycache__ files."""
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()

        tool_dir = tools_dir / "tool1"
        tool_dir.mkdir()
        (tool_dir / "tool.py").write_text("# Tool 1\n")

        # Add __pycache__ (should be ignored)
        pycache_dir = tool_dir / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "tool.cpython-310.pyc").write_bytes(b"bytecode")

        versions = get_tool_versions(tools_dir)
        assert len(versions) == 1
        assert "tool1" in versions

    def test_get_tool_versions_nonexistent_dir(self, tmp_path: Path) -> None:
        """Test tool versions with non-existent tools dir."""
        tools_dir = tmp_path / "nonexistent"
        versions = get_tool_versions(tools_dir)
        assert versions == {}


class TestGetEnvironmentInfo:
    """Tests for get_environment_info()."""

    def test_get_environment_info(self) -> None:
        """Test environment info capture."""
        env_info = get_environment_info()

        assert "python_version" in env_info
        assert "raw_version" in env_info
        assert "hostname" in env_info
        assert "working_directory" in env_info
        assert "platform" in env_info
        assert "platform_release" in env_info

        # Validate types
        assert isinstance(env_info["python_version"], str)
        assert isinstance(env_info["raw_version"], str)
        assert isinstance(env_info["hostname"], str)
        assert isinstance(env_info["working_directory"], str)


class TestGetConfigSnapshot:
    """Tests for get_config_snapshot()."""

    def test_get_config_snapshot_no_raw_vars(self) -> None:
        """Test config snapshot with no RAW_ env vars."""
        # Clear RAW_ vars
        original_env = dict(os.environ)
        for key in list(os.environ.keys()):
            if key.startswith("RAW_"):
                del os.environ[key]

        try:
            config = get_config_snapshot()
            assert config == {}
        finally:
            os.environ.update(original_env)

    def test_get_config_snapshot_with_vars(self) -> None:
        """Test config snapshot captures RAW_ vars."""
        # Set RAW_ vars
        original_env = dict(os.environ)
        os.environ["RAW_DEBUG"] = "true"
        os.environ["RAW_TIMEOUT"] = "30"
        os.environ["OTHER_VAR"] = "ignored"

        try:
            config = get_config_snapshot()
            assert "RAW_DEBUG" in config
            assert "RAW_TIMEOUT" in config
            assert "OTHER_VAR" not in config
            assert config["RAW_DEBUG"] == "true"
            assert config["RAW_TIMEOUT"] == "30"
        finally:
            os.environ.clear()
            os.environ.update(original_env)

    def test_get_config_snapshot_redacts_secrets(self) -> None:
        """Test config snapshot redacts secret values."""
        original_env = dict(os.environ)
        os.environ["RAW_API_KEY"] = "secret123"
        os.environ["RAW_TOKEN"] = "token456"
        os.environ["RAW_PASSWORD"] = "pass789"
        os.environ["RAW_SECRET"] = "secret999"
        os.environ["RAW_DEBUG"] = "true"

        try:
            config = get_config_snapshot(redact_secrets=True)
            assert config["RAW_API_KEY"] == "***REDACTED***"
            assert config["RAW_TOKEN"] == "***REDACTED***"
            assert config["RAW_PASSWORD"] == "***REDACTED***"
            assert config["RAW_SECRET"] == "***REDACTED***"
            assert config["RAW_DEBUG"] == "true"  # Not a secret
        finally:
            os.environ.clear()
            os.environ.update(original_env)

    def test_get_config_snapshot_no_redaction(self) -> None:
        """Test config snapshot without redaction."""
        original_env = dict(os.environ)
        os.environ["RAW_API_KEY"] = "secret123"

        try:
            config = get_config_snapshot(redact_secrets=False)
            assert config["RAW_API_KEY"] == "secret123"
        finally:
            os.environ.clear()
            os.environ.update(original_env)


class TestCaptureProvenance:
    """Tests for capture_provenance()."""

    def test_capture_provenance(self, tmp_path: Path) -> None:
        """Test complete provenance capture."""
        workflow_file = tmp_path / "run.py"
        workflow_file.write_text("# Test workflow\n")

        provenance = capture_provenance(workflow_file)

        # Should have all required fields
        assert "python_version" in provenance
        assert "raw_version" in provenance
        assert "hostname" in provenance
        assert "working_directory" in provenance
        assert "tool_versions" in provenance
        assert "config_snapshot" in provenance
        assert "workflow_hash" in provenance

        # Validate types
        assert isinstance(provenance["python_version"], str)
        assert isinstance(provenance["raw_version"], str)
        assert isinstance(provenance["hostname"], str)
        assert isinstance(provenance["working_directory"], str)
        assert isinstance(provenance["tool_versions"], dict)
        assert isinstance(provenance["config_snapshot"], dict)

    def test_capture_provenance_no_workflow(self) -> None:
        """Test provenance capture without workflow file."""
        provenance = capture_provenance()

        # Should still capture environment info
        assert "python_version" in provenance
        assert "raw_version" in provenance
        assert "hostname" in provenance

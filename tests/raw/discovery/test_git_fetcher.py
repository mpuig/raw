"""Tests for GitToolFetcher."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from raw.discovery.git_fetcher import FetchResult, GitToolFetcher


class TestGitToolFetcher:
    """Tests for GitToolFetcher class."""

    @pytest.fixture
    def tools_dir(self, tmp_path: Path) -> Path:
        """Create a temporary tools directory."""
        tools = tmp_path / "tools"
        tools.mkdir()
        return tools

    @pytest.fixture
    def fetcher(self, tools_dir: Path) -> GitToolFetcher:
        """Create a GitToolFetcher instance."""
        return GitToolFetcher(tools_dir)

    def test_derive_name_from_https_url(self, fetcher: GitToolFetcher) -> None:
        """Test name derivation from HTTPS URL."""
        url = "https://github.com/user/my-tool.git"
        assert fetcher._derive_name_from_url(url) == "my-tool"

    def test_derive_name_from_url_without_git_suffix(
        self, fetcher: GitToolFetcher
    ) -> None:
        """Test name derivation from URL without .git suffix."""
        url = "https://github.com/user/my-tool"
        assert fetcher._derive_name_from_url(url) == "my-tool"

    def test_derive_name_from_ssh_url(self, fetcher: GitToolFetcher) -> None:
        """Test name derivation from SSH URL."""
        url = "git@github.com:user/my-tool.git"
        assert fetcher._derive_name_from_url(url) == "my-tool"

    def test_derive_name_trailing_slash(self, fetcher: GitToolFetcher) -> None:
        """Test name derivation handles trailing slash."""
        url = "https://github.com/user/my-tool/"
        assert fetcher._derive_name_from_url(url) == "my-tool"

    @patch("raw.discovery.git_fetcher.subprocess.run")
    def test_fetch_success(
        self,
        mock_run: MagicMock,
        fetcher: GitToolFetcher,
        tools_dir: Path,
    ) -> None:
        """Test successful fetch creates tool directory."""
        mock_run.return_value = MagicMock(returncode=0, stdout="abc1234\n", stderr="")

        result = fetcher.fetch(
            git_url="https://github.com/user/test-tool.git",
            vendor=False,
        )

        assert result.success
        assert result.tool_path == tools_dir / "test-tool"
        assert result.version is not None

    @patch("raw.discovery.git_fetcher.subprocess.run")
    def test_fetch_with_custom_name(
        self,
        mock_run: MagicMock,
        fetcher: GitToolFetcher,
        tools_dir: Path,
    ) -> None:
        """Test fetch with custom tool name."""
        mock_run.return_value = MagicMock(returncode=0, stdout="abc1234\n", stderr="")

        result = fetcher.fetch(
            git_url="https://github.com/user/some-repo.git",
            name="custom-name",
            vendor=False,
        )

        assert result.success
        assert result.tool_path == tools_dir / "custom-name"

    @patch("raw.discovery.git_fetcher.subprocess.run")
    def test_fetch_with_ref(
        self,
        mock_run: MagicMock,
        fetcher: GitToolFetcher,
    ) -> None:
        """Test fetch with specific git ref (tag/branch)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="abc1234\n", stderr="")

        result = fetcher.fetch(
            git_url="https://github.com/user/test-tool.git",
            ref="v1.0.0",
            vendor=False,
        )

        assert result.success
        assert "v1.0.0" in (result.version or "")

    def test_fetch_existing_tool_fails(
        self,
        fetcher: GitToolFetcher,
        tools_dir: Path,
    ) -> None:
        """Test fetch fails if tool already exists."""
        existing_tool = tools_dir / "existing-tool"
        existing_tool.mkdir()

        result = fetcher.fetch(
            git_url="https://github.com/user/existing-tool.git",
        )

        assert not result.success
        assert "already exists" in (result.error or "")

    @patch("raw.discovery.git_fetcher.subprocess.run")
    def test_fetch_clone_failure(
        self,
        mock_run: MagicMock,
        fetcher: GitToolFetcher,
        tools_dir: Path,
    ) -> None:
        """Test fetch handles clone failures."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "git clone", stderr="fatal: repository not found"
        )

        result = fetcher.fetch(
            git_url="https://github.com/user/nonexistent.git",
        )

        assert not result.success
        assert result.error is not None
        assert tools_dir / "nonexistent" not in list(tools_dir.iterdir())

    def test_vendor_removes_git_dir(
        self,
        fetcher: GitToolFetcher,
        tools_dir: Path,
    ) -> None:
        """Test vendor mode removes .git directory."""
        tool_path = tools_dir / "test-tool"
        git_dir = tool_path / ".git"
        tool_path.mkdir()
        git_dir.mkdir()

        fetcher._vendor(tool_path)

        assert not git_dir.exists()
        assert tool_path.exists()

    def test_remove_existing_tool(
        self,
        fetcher: GitToolFetcher,
        tools_dir: Path,
    ) -> None:
        """Test removing an existing tool."""
        tool_path = tools_dir / "to-remove"
        tool_path.mkdir()
        (tool_path / "config.yaml").touch()

        result = fetcher.remove("to-remove")

        assert result.success
        assert not tool_path.exists()

    def test_remove_nonexistent_tool(
        self,
        fetcher: GitToolFetcher,
    ) -> None:
        """Test removing a nonexistent tool fails."""
        result = fetcher.remove("does-not-exist")

        assert not result.success
        assert "not found" in (result.error or "")


class TestFetchResult:
    """Tests for FetchResult dataclass."""

    def test_success_result(self) -> None:
        """Test creating a success result."""
        result = FetchResult(
            success=True,
            tool_path=Path("/tools/my-tool"),
            version="v1.0.0 (abc1234)",
        )
        assert result.success
        assert result.tool_path == Path("/tools/my-tool")
        assert result.version == "v1.0.0 (abc1234)"
        assert result.error is None

    def test_failure_result(self) -> None:
        """Test creating a failure result."""
        result = FetchResult(
            success=False,
            error="Clone failed",
        )
        assert not result.success
        assert result.tool_path is None
        assert result.error == "Clone failed"

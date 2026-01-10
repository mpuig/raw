"""Tests for builder loop controller."""

import tempfile
from pathlib import Path

import pytest

from raw.builder.config import BuilderConfig
from raw.builder.loop import BuildResult, builder_loop


def create_test_workflow(workflows_dir: Path, workflow_id: str) -> Path:
    """Create a minimal test workflow."""
    workflow_dir = workflows_dir / workflow_id
    workflow_dir.mkdir(parents=True)

    # Create valid run.py
    run_py = workflow_dir / "run.py"
    run_py.write_text(
        """#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "rich>=13.0"]
# ///
from pydantic import BaseModel
from raw_runtime import BaseWorkflow

class TestParams(BaseModel):
    pass

class TestWorkflow(BaseWorkflow[TestParams]):
    def run(self) -> int:
        print("Test workflow")
        return 0

if __name__ == "__main__":
    TestWorkflow.main()
"""
    )

    # Create dry_run.py
    dry_run = workflow_dir / "dry_run.py"
    dry_run.write_text(
        """#!/usr/bin/env python3
from raw_runtime import DryRunContext

def mock_test_workflow(ctx: DryRunContext):
    return 0
"""
    )

    # Create config.yaml
    config = workflow_dir / "config.yaml"
    config.write_text(
        f"""id: {workflow_id}
name: test-workflow
status: draft
description:
  intent: Test workflow for builder
"""
    )

    return workflow_dir


@pytest.mark.asyncio
async def test_build_result():
    """Test BuildResult class."""
    result = BuildResult("success", "build-123", 3)
    assert result.status == "success"
    assert result.build_id == "build-123"
    assert result.iterations == 3
    assert result.exit_code() == 0

    result = BuildResult("failed", "build-456", 2, "Error message")
    assert result.status == "failed"
    assert result.exit_code() == 1

    result = BuildResult("stuck", "build-789", 10, "Max iterations")
    assert result.status == "stuck"
    assert result.exit_code() == 2


@pytest.mark.asyncio
async def test_builder_loop_workflow_not_found():
    """Test builder loop with non-existent workflow."""
    config = BuilderConfig()

    with pytest.raises(ValueError, match="Workflow not found"):
        await builder_loop("nonexistent-workflow", None, config)


@pytest.mark.asyncio
async def test_builder_loop_max_iterations():
    """Test builder loop hits max iterations budget."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create .raw structure
        raw_dir = tmpdir_path / ".raw"
        raw_dir.mkdir()
        workflows_dir = raw_dir / "workflows"
        workflows_dir.mkdir()
        builds_dir = raw_dir / "builds"
        builds_dir.mkdir()

        # Create test workflow
        workflow_id = "test-workflow"
        create_test_workflow(workflows_dir, workflow_id)

        # Configure with very low max iterations
        config = BuilderConfig()
        config.budgets.max_iterations = 1

        # Mock cwd to tmpdir
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir_path)

            # Run builder (will hit max iterations since gates always fail in mock)
            result = await builder_loop(workflow_id, None, config)

            # Should be stuck due to max iterations
            assert result.status == "stuck"
            assert result.iterations <= 2  # May complete 1 or 2 iterations

        finally:
            os.chdir(original_cwd)


@pytest.mark.asyncio
async def test_builder_loop_creates_journal():
    """Test that builder loop creates journal."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create .raw structure
        raw_dir = tmpdir_path / ".raw"
        raw_dir.mkdir()
        workflows_dir = raw_dir / "workflows"
        workflows_dir.mkdir()
        builds_dir = raw_dir / "builds"
        builds_dir.mkdir()

        # Create test workflow
        workflow_id = "test-workflow"
        create_test_workflow(workflows_dir, workflow_id)

        # Configure
        config = BuilderConfig()
        config.budgets.max_iterations = 1

        # Mock cwd
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir_path)

            # Run builder
            result = await builder_loop(workflow_id, None, config)

            # Check journal exists
            build_dirs = list(builds_dir.iterdir())
            assert len(build_dirs) > 0

            journal_path = build_dirs[0] / "events.jsonl"
            assert journal_path.exists()

            # Check journal has events
            lines = journal_path.read_text().strip().split("\n")
            assert len(lines) > 0

        finally:
            os.chdir(original_cwd)

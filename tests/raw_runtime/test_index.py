"""Tests for run index."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from raw_runtime.index import (
    RunIndexEntry,
    RunIndexReader,
    RunIndexWriter,
    rebuild_index_from_journals,
)
from raw_runtime.journal import LocalJournalWriter
from raw_runtime.models import RunStatus


class TestRunIndexWriter:
    """Tests for RunIndexWriter."""

    def test_append_run(self, tmp_path: Path) -> None:
        """Test appending run to index."""
        index_path = tmp_path / "index.jsonl"
        writer = RunIndexWriter(index_path)

        entry = RunIndexEntry(
            run_id="run_123",
            workflow_id="workflow_abc",
            workflow_name="TestWorkflow",
            status=RunStatus.SUCCESS,
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            duration_seconds=10.5,
        )

        writer.append_run(entry)

        # Verify file created and contains entry
        assert index_path.exists()
        content = index_path.read_text()
        assert "run_123" in content
        assert "workflow_abc" in content
        assert "success" in content  # Lowercase in JSON serialization

    def test_append_multiple_runs(self, tmp_path: Path) -> None:
        """Test appending multiple runs."""
        index_path = tmp_path / "index.jsonl"
        writer = RunIndexWriter(index_path)

        for i in range(5):
            entry = RunIndexEntry(
                run_id=f"run_{i}",
                workflow_id="workflow_test",
                workflow_name="Test",
                status=RunStatus.SUCCESS,
                started_at=datetime.now(timezone.utc),
            )
            writer.append_run(entry)

        # Verify all entries written
        lines = index_path.read_text().strip().split("\n")
        assert len(lines) == 5
        for i, line in enumerate(lines):
            assert f"run_{i}" in line

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test writer creates parent directories."""
        index_path = tmp_path / "subdir" / "another" / "index.jsonl"
        writer = RunIndexWriter(index_path)

        entry = RunIndexEntry(
            run_id="run_test",
            workflow_id="workflow_test",
            workflow_name="Test",
            status=RunStatus.SUCCESS,
            started_at=datetime.now(timezone.utc),
        )

        writer.append_run(entry)

        assert index_path.exists()
        assert index_path.parent.exists()


class TestRunIndexReader:
    """Tests for RunIndexReader."""

    def test_list_runs_empty_index(self, tmp_path: Path) -> None:
        """Test listing runs from empty/missing index."""
        index_path = tmp_path / "index.jsonl"
        reader = RunIndexReader(index_path)

        runs = reader.list_runs()
        assert runs == []

    def test_list_runs_all(self, tmp_path: Path) -> None:
        """Test listing all runs."""
        index_path = tmp_path / "index.jsonl"
        writer = RunIndexWriter(index_path)

        # Create 3 runs
        for i in range(3):
            entry = RunIndexEntry(
                run_id=f"run_{i}",
                workflow_id="workflow_test",
                workflow_name="Test",
                status=RunStatus.SUCCESS,
                started_at=datetime.now(timezone.utc),
            )
            writer.append_run(entry)

        reader = RunIndexReader(index_path)
        runs = reader.list_runs()

        assert len(runs) == 3
        assert runs[0].run_id == "run_0"
        assert runs[1].run_id == "run_1"
        assert runs[2].run_id == "run_2"

    def test_list_runs_filter_by_status(self, tmp_path: Path) -> None:
        """Test filtering runs by status."""
        index_path = tmp_path / "index.jsonl"
        writer = RunIndexWriter(index_path)

        # Create runs with different statuses
        writer.append_run(
            RunIndexEntry(
                run_id="run_success",
                workflow_id="workflow_test",
                workflow_name="Test",
                status=RunStatus.SUCCESS,
                started_at=datetime.now(timezone.utc),
            )
        )
        writer.append_run(
            RunIndexEntry(
                run_id="run_failed",
                workflow_id="workflow_test",
                workflow_name="Test",
                status=RunStatus.FAILED,
                started_at=datetime.now(timezone.utc),
                error="Something went wrong",
            )
        )
        writer.append_run(
            RunIndexEntry(
                run_id="run_crashed",
                workflow_id="workflow_test",
                workflow_name="Test",
                status=RunStatus.CRASHED,
                started_at=datetime.now(timezone.utc),
            )
        )

        reader = RunIndexReader(index_path)

        # Filter by SUCCESS
        success_runs = reader.list_runs(status=RunStatus.SUCCESS)
        assert len(success_runs) == 1
        assert success_runs[0].run_id == "run_success"

        # Filter by FAILED
        failed_runs = reader.list_runs(status=RunStatus.FAILED)
        assert len(failed_runs) == 1
        assert failed_runs[0].run_id == "run_failed"

        # Filter by CRASHED
        crashed_runs = reader.list_runs(status=RunStatus.CRASHED)
        assert len(crashed_runs) == 1
        assert crashed_runs[0].run_id == "run_crashed"

    def test_list_runs_filter_by_workflow_id(self, tmp_path: Path) -> None:
        """Test filtering runs by workflow ID."""
        index_path = tmp_path / "index.jsonl"
        writer = RunIndexWriter(index_path)

        # Create runs for different workflows
        for workflow_num in range(2):
            for run_num in range(3):
                writer.append_run(
                    RunIndexEntry(
                        run_id=f"run_{workflow_num}_{run_num}",
                        workflow_id=f"workflow_{workflow_num}",
                        workflow_name=f"Workflow{workflow_num}",
                        status=RunStatus.SUCCESS,
                        started_at=datetime.now(timezone.utc),
                    )
                )

        reader = RunIndexReader(index_path)

        # Filter by workflow_0
        workflow0_runs = reader.list_runs(workflow_id="workflow_0")
        assert len(workflow0_runs) == 3
        assert all(r.workflow_id == "workflow_0" for r in workflow0_runs)

        # Filter by workflow_1
        workflow1_runs = reader.list_runs(workflow_id="workflow_1")
        assert len(workflow1_runs) == 3
        assert all(r.workflow_id == "workflow_1" for r in workflow1_runs)

    def test_list_runs_pagination(self, tmp_path: Path) -> None:
        """Test pagination with offset and limit."""
        index_path = tmp_path / "index.jsonl"
        writer = RunIndexWriter(index_path)

        # Create 10 runs
        for i in range(10):
            writer.append_run(
                RunIndexEntry(
                    run_id=f"run_{i:02d}",
                    workflow_id="workflow_test",
                    workflow_name="Test",
                    status=RunStatus.SUCCESS,
                    started_at=datetime.now(timezone.utc),
                )
            )

        reader = RunIndexReader(index_path)

        # First page (0-4)
        page1 = reader.list_runs(offset=0, limit=5)
        assert len(page1) == 5
        assert page1[0].run_id == "run_00"
        assert page1[4].run_id == "run_04"

        # Second page (5-9)
        page2 = reader.list_runs(offset=5, limit=5)
        assert len(page2) == 5
        assert page2[0].run_id == "run_05"
        assert page2[4].run_id == "run_09"

        # Offset beyond end
        page3 = reader.list_runs(offset=20, limit=5)
        assert len(page3) == 0

    def test_get_run(self, tmp_path: Path) -> None:
        """Test getting specific run by ID."""
        index_path = tmp_path / "index.jsonl"
        writer = RunIndexWriter(index_path)

        # Create several runs
        for i in range(5):
            writer.append_run(
                RunIndexEntry(
                    run_id=f"run_{i}",
                    workflow_id="workflow_test",
                    workflow_name="Test",
                    status=RunStatus.SUCCESS,
                    started_at=datetime.now(timezone.utc),
                )
            )

        reader = RunIndexReader(index_path)

        # Get specific run
        run = reader.get_run("run_2")
        assert run is not None
        assert run.run_id == "run_2"

        # Get nonexistent run
        missing = reader.get_run("run_99")
        assert missing is None

    def test_count_runs(self, tmp_path: Path) -> None:
        """Test counting runs with filters."""
        index_path = tmp_path / "index.jsonl"
        writer = RunIndexWriter(index_path)

        # Create runs with different statuses
        for i in range(5):
            writer.append_run(
                RunIndexEntry(
                    run_id=f"run_{i}",
                    workflow_id="workflow_test",
                    workflow_name="Test",
                    status=RunStatus.SUCCESS if i % 2 == 0 else RunStatus.FAILED,
                    started_at=datetime.now(timezone.utc),
                )
            )

        reader = RunIndexReader(index_path)

        # Count all runs
        total = reader.count_runs()
        assert total == 5

        # Count success runs
        success_count = reader.count_runs(status=RunStatus.SUCCESS)
        assert success_count == 3

        # Count failed runs
        failed_count = reader.count_runs(status=RunStatus.FAILED)
        assert failed_count == 2

    def test_skips_corrupt_lines(self, tmp_path: Path) -> None:
        """Test reader skips corrupt JSON lines."""
        index_path = tmp_path / "index.jsonl"

        # Write mix of valid and corrupt lines
        with open(index_path, "w") as f:
            # Valid entry
            entry1 = RunIndexEntry(
                run_id="run_1",
                workflow_id="workflow_test",
                workflow_name="Test",
                status=RunStatus.SUCCESS,
                started_at=datetime.now(timezone.utc),
            )
            f.write(entry1.model_dump_json() + "\n")

            # Corrupt line
            f.write("this is not valid json\n")

            # Valid entry
            entry2 = RunIndexEntry(
                run_id="run_2",
                workflow_id="workflow_test",
                workflow_name="Test",
                status=RunStatus.SUCCESS,
                started_at=datetime.now(timezone.utc),
            )
            f.write(entry2.model_dump_json() + "\n")

        reader = RunIndexReader(index_path)
        runs = reader.list_runs()

        # Should only return valid entries
        assert len(runs) == 2
        assert runs[0].run_id == "run_1"
        assert runs[1].run_id == "run_2"


class TestRebuildIndex:
    """Tests for rebuild_index_from_journals()."""

    def test_rebuild_from_empty_directory(self, tmp_path: Path) -> None:
        """Test rebuilding index from empty workflows directory."""
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        index_path = tmp_path / "index.jsonl"

        count = rebuild_index_from_journals(workflows_dir, index_path)

        assert count == 0
        assert not index_path.exists()

    def test_rebuild_from_journals(self, tmp_path: Path) -> None:
        """Test rebuilding index from actual journals."""
        from raw_runtime.events import (
            StepCompletedEvent,
            StepStartedEvent,
            WorkflowCompletedEvent,
            WorkflowStartedEvent,
        )

        workflows_dir = tmp_path / "workflows"
        workflow_dir = workflows_dir / "test_workflow" / "runs"
        workflow_dir.mkdir(parents=True)

        # Create 2 run journals
        for i in range(2):
            run_dir = workflow_dir / f"run_{i}"
            run_dir.mkdir()
            journal_path = run_dir / "events.jsonl"

            with LocalJournalWriter(journal_path) as writer:
                writer.write_event(
                    WorkflowStartedEvent(
                        workflow_id="test_workflow",
                        run_id=f"run_{i}",
                        workflow_name="TestWorkflow",
                    )
                )
                writer.write_event(
                    StepStartedEvent(
                        workflow_id="test_workflow",
                        run_id=f"run_{i}",
                        step_name="step1",
                    )
                )
                writer.write_event(
                    StepCompletedEvent(
                        workflow_id="test_workflow",
                        run_id=f"run_{i}",
                        step_name="step1",
                        duration_seconds=1.0,
                        result_type="str",
                    )
                )
                writer.write_event(
                    WorkflowCompletedEvent(
                        workflow_id="test_workflow",
                        run_id=f"run_{i}",
                        duration_seconds=1.0,
                        step_count=1,
                    )
                )

        # Rebuild index
        index_path = tmp_path / "index.jsonl"
        count = rebuild_index_from_journals(workflows_dir, index_path)

        assert count == 2
        assert index_path.exists()

        # Verify index contains both runs
        reader = RunIndexReader(index_path)
        runs = reader.list_runs()
        assert len(runs) == 2

        # Sort by run_id for consistent ordering
        runs_sorted = sorted(runs, key=lambda r: r.run_id)
        assert runs_sorted[0].run_id == "run_0"
        assert runs_sorted[1].run_id == "run_1"
        assert all(r.status == RunStatus.SUCCESS for r in runs)

    def test_rebuild_skips_corrupt_journals(self, tmp_path: Path) -> None:
        """Test rebuild skips runs with corrupt journals."""
        workflows_dir = tmp_path / "workflows"
        workflow_dir = workflows_dir / "test_workflow" / "runs"
        workflow_dir.mkdir(parents=True)

        # Valid run
        run1_dir = workflow_dir / "run_1"
        run1_dir.mkdir()
        journal1 = run1_dir / "events.jsonl"

        from raw_runtime.events import WorkflowStartedEvent

        with LocalJournalWriter(journal1) as writer:
            writer.write_event(
                WorkflowStartedEvent(
                    workflow_id="test_workflow",
                    run_id="run_1",
                    workflow_name="TestWorkflow",
                )
            )

        # Corrupt run
        run2_dir = workflow_dir / "run_2"
        run2_dir.mkdir()
        journal2 = run2_dir / "events.jsonl"
        journal2.write_text("corrupt json\n")

        # Rebuild
        index_path = tmp_path / "index.jsonl"
        count = rebuild_index_from_journals(workflows_dir, index_path)

        # Only valid run indexed
        assert count == 1

        reader = RunIndexReader(index_path)
        runs = reader.list_runs()
        assert len(runs) == 1
        assert runs[0].run_id == "run_1"

    def test_rebuild_clears_existing_index(self, tmp_path: Path) -> None:
        """Test rebuild clears existing index before rebuilding."""
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        index_path = tmp_path / "index.jsonl"

        # Create existing index with old entries
        writer = RunIndexWriter(index_path)
        writer.append_run(
            RunIndexEntry(
                run_id="old_run",
                workflow_id="old_workflow",
                workflow_name="Old",
                status=RunStatus.SUCCESS,
                started_at=datetime.now(timezone.utc),
            )
        )

        # Rebuild (should clear old entries)
        count = rebuild_index_from_journals(workflows_dir, index_path)

        assert count == 0

        # Index should be empty or not exist
        reader = RunIndexReader(index_path)
        runs = reader.list_runs()
        assert len(runs) == 0

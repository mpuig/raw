"""Run index for fast queries without scanning all journals.

Maintains an append-only JSONL index of run metadata to support fast:
- Listing runs with filters (status, workflow_id)
- Pagination with cursors (offset-based)
- Queries without scanning all run directories

Index is crash-safe (append-only) and rebuildable from journals.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from raw_runtime.models import RunStatus


class RunIndexEntry(BaseModel):
    """Metadata for a single run in the index."""

    run_id: str = Field(..., description="Unique run ID")
    workflow_id: str = Field(..., description="Workflow ID")
    workflow_name: str = Field(..., description="Human-readable workflow name")
    status: RunStatus = Field(..., description="Run status")
    started_at: datetime = Field(..., description="When run started")
    ended_at: datetime | None = Field(default=None, description="When run ended")
    duration_seconds: float | None = Field(default=None, description="Run duration")
    error: str | None = Field(default=None, description="Error message if failed/crashed")
    git_sha: str | None = Field(default=None, description="Git commit SHA")
    git_branch: str | None = Field(default=None, description="Git branch")
    resumed_from: str | None = Field(default=None, description="Previous run ID if resumed")


class RunIndexWriter:
    """Append-only writer for run index."""

    def __init__(self, index_path: Path) -> None:
        """Initialize index writer.

        Args:
            index_path: Path to index.jsonl file
        """
        self._index_path = index_path

        # Ensure parent directory exists
        self._index_path.parent.mkdir(parents=True, exist_ok=True)

    def append_run(self, entry: RunIndexEntry) -> None:
        """Append a run entry to the index.

        Args:
            entry: Run metadata to append
        """
        with open(self._index_path, "a", encoding="utf-8") as f:
            line = entry.model_dump_json() + "\n"
            f.write(line)
            f.flush()


class RunIndexReader:
    """Reader for querying run index."""

    def __init__(self, index_path: Path) -> None:
        """Initialize index reader.

        Args:
            index_path: Path to index.jsonl file
        """
        self._index_path = index_path

    def list_runs(
        self,
        status: RunStatus | None = None,
        workflow_id: str | None = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[RunIndexEntry]:
        """List runs with optional filters and pagination.

        Args:
            status: Filter by status (None = all statuses)
            workflow_id: Filter by workflow ID (None = all workflows)
            offset: Skip first N runs (for pagination)
            limit: Return at most N runs (None = unlimited)

        Returns:
            List of run entries matching filters
        """
        if not self._index_path.exists():
            return []

        entries: list[RunIndexEntry] = []
        current_offset = 0

        with open(self._index_path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    entry = RunIndexEntry.model_validate_json(line)
                except Exception:
                    # Skip corrupt lines
                    continue

                # Apply filters
                if status is not None and entry.status != status:
                    continue

                if workflow_id is not None and entry.workflow_id != workflow_id:
                    continue

                # Apply pagination - skip until we reach offset
                if current_offset < offset:
                    current_offset += 1
                    continue

                # Add to results
                entries.append(entry)

                # Stop if we hit the limit
                if limit is not None and len(entries) >= limit:
                    break

        return entries

    def get_run(self, run_id: str) -> RunIndexEntry | None:
        """Get a specific run by ID.

        Args:
            run_id: Run ID to find

        Returns:
            Run entry if found, None otherwise
        """
        if not self._index_path.exists():
            return None

        # Scan from end (most recent runs first)
        with open(self._index_path, encoding="utf-8") as f:
            lines = f.readlines()

        for line in reversed(lines):
            if not line.strip():
                continue

            try:
                entry = RunIndexEntry.model_validate_json(line)
                if entry.run_id == run_id:
                    return entry
            except Exception:
                continue

        return None

    def count_runs(
        self,
        status: RunStatus | None = None,
        workflow_id: str | None = None,
    ) -> int:
        """Count runs matching filters.

        Args:
            status: Filter by status (None = all statuses)
            workflow_id: Filter by workflow ID (None = all workflows)

        Returns:
            Number of runs matching filters
        """
        if not self._index_path.exists():
            return 0

        count = 0

        with open(self._index_path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    entry = RunIndexEntry.model_validate_json(line)
                except Exception:
                    continue

                # Apply filters
                if status is not None and entry.status != status:
                    continue

                if workflow_id is not None and entry.workflow_id != workflow_id:
                    continue

                count += 1

        return count


def rebuild_index_from_journals(
    workflows_dir: Path,
    index_path: Path,
) -> int:
    """Rebuild run index from all run journals.

    Scans all run directories, reads journals, and rebuilds the index.
    Useful for recovering from index corruption or initializing index.

    Args:
        workflows_dir: Path to .raw/workflows directory
        index_path: Path to index.jsonl file

    Returns:
        Number of runs indexed
    """
    from raw_runtime.reducer import ManifestReducer

    # Clear existing index
    if index_path.exists():
        index_path.unlink()

    writer = RunIndexWriter(index_path)
    count = 0

    if not workflows_dir.exists():
        return 0

    # Scan all workflows and runs
    for workflow_dir in workflows_dir.iterdir():
        if not workflow_dir.is_dir():
            continue

        runs_dir = workflow_dir / "runs"
        if not runs_dir.exists():
            continue

        for run_dir in runs_dir.iterdir():
            if not run_dir.is_dir():
                continue

            journal_path = run_dir / "events.jsonl"
            if not journal_path.exists():
                continue

            # Read journal and create index entry
            try:
                reducer = ManifestReducer()
                manifest = reducer.reduce_from_file(journal_path)

                # Extract provenance
                git_sha = None
                git_branch = None
                if manifest.provenance:
                    git_sha = manifest.provenance.git_sha
                    git_branch = manifest.provenance.git_branch

                # Create index entry
                entry = RunIndexEntry(
                    run_id=manifest.run.run_id,
                    workflow_id=manifest.workflow.id,
                    workflow_name=manifest.workflow.short_name,
                    status=manifest.run.status,
                    started_at=manifest.run.started_at,
                    ended_at=manifest.run.ended_at,
                    duration_seconds=manifest.run.duration_seconds,
                    error=manifest.error,
                    git_sha=git_sha,
                    git_branch=git_branch,
                    resumed_from=None,  # TODO: Extract from provenance if available
                )

                writer.append_run(entry)
                count += 1

            except Exception:
                # Skip runs with corrupt journals
                continue

    return count


__all__ = [
    "RunIndexEntry",
    "RunIndexWriter",
    "RunIndexReader",
    "rebuild_index_from_journals",
]

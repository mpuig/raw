"""Append-only run journal for crash recovery and provenance.

The journal writes all workflow events to .raw/runs/{run_id}/events.jsonl
in real-time, providing:
- Crash recovery: reconstruct manifest from events
- Provenance: complete audit trail of what happened
- Resume: identify where to restart after interruption
- Observability: external tools can tail the journal

Design principles:
- Append-only: events are never modified or deleted
- Versioned: schema evolution via version field
- Flushed: fsync after each write for durability
- Incremental: written during execution, not at finalize
"""

import json
from pathlib import Path
from typing import Protocol

from raw_runtime.events import Event


class JournalWriter(Protocol):
    """Protocol for journal persistence.

    Implementations handle where/how events are written:
    - LocalJournalWriter: Local filesystem with fsync
    - Future: RemoteJournalWriter for distributed runs
    """

    def write_event(self, event: Event) -> None:
        """Write an event to the journal."""
        ...

    def flush(self) -> None:
        """Ensure all events are durably persisted."""
        ...


class LocalJournalWriter:
    """Writes events to local filesystem journal with immediate flush.

    Events are written to .raw/runs/{run_id}/events.jsonl in JSONL format.
    Each line is a versioned event with:
    - version: schema version (1 for initial release)
    - event: serialized event data

    Files are flushed after each write to ensure durability even if the
    process crashes.
    """

    def __init__(self, journal_path: Path, schema_version: int = 1) -> None:
        """Initialize journal writer.

        Args:
            journal_path: Path to events.jsonl file
            schema_version: Journal schema version (default: 1)
        """
        self._journal_path = journal_path
        self._schema_version = schema_version
        self._file_handle: object | None = None

        # Ensure parent directory exists
        journal_path.parent.mkdir(parents=True, exist_ok=True)

    def write_event(self, event: Event) -> None:
        """Write event to journal with immediate flush.

        Events are written as JSONL with schema version wrapper:
        {"version": 1, "event": {...}}

        File is flushed after each write for crash safety.
        """
        # Open file in append mode if not already open
        if self._file_handle is None:
            self._file_handle = open(self._journal_path, "a", encoding="utf-8")  # noqa: SIM115

        # Serialize event with version wrapper
        journal_entry = {
            "version": self._schema_version,
            "event": json.loads(event.model_dump_json()),
        }

        # Write and flush immediately
        line = json.dumps(journal_entry, default=str) + "\n"
        self._file_handle.write(line)  # type: ignore[attr-defined]
        self._file_handle.flush()  # type: ignore[attr-defined]

    def flush(self) -> None:
        """Flush and sync file to disk.

        Ensures all data is written to disk, not just OS buffers.
        """
        if self._file_handle is not None:
            self._file_handle.flush()  # type: ignore[attr-defined]
            # Force OS to write to disk
            import os
            os.fsync(self._file_handle.fileno())  # type: ignore[attr-defined]

    def close(self) -> None:
        """Close the journal file."""
        if self._file_handle is not None:
            self.flush()
            self._file_handle.close()  # type: ignore[attr-defined]
            self._file_handle = None

    def __enter__(self) -> "LocalJournalWriter":
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        """Close on context exit."""
        self.close()


class JournalReader:
    """Reads events from journal file.

    Handles:
    - Schema versioning (currently only v1)
    - Corrupt/incomplete trailing lines (graceful skip)
    - Line-by-line iteration without loading entire file
    """

    def __init__(self, journal_path: Path) -> None:
        """Initialize journal reader.

        Args:
            journal_path: Path to events.jsonl file
        """
        self._journal_path = journal_path

    def read_events(self) -> list[dict]:
        """Read all events from journal.

        Returns list of event dictionaries (not deserialized to Event objects).
        Skips corrupt or incomplete lines with a warning.
        """
        if not self._journal_path.exists():
            return []

        events = []
        with open(self._journal_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                    version = entry.get("version", 1)

                    if version != 1:
                        # Future: handle schema migration
                        print(f"Warning: Unknown journal version {version} at line {line_num}")
                        continue

                    events.append(entry["event"])
                except json.JSONDecodeError as e:
                    # Corrupt/incomplete line - likely crash during write
                    print(f"Warning: Corrupt journal line {line_num}: {e}")
                    continue

        return events

    def iter_events(self):
        """Iterate events one at a time (memory efficient for large journals)."""
        if not self._journal_path.exists():
            return

        with open(self._journal_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                    version = entry.get("version", 1)

                    if version != 1:
                        print(f"Warning: Unknown journal version {version} at line {line_num}")
                        continue

                    yield entry["event"]
                except json.JSONDecodeError as e:
                    print(f"Warning: Corrupt journal line {line_num}: {e}")
                    continue


__all__ = [
    "JournalWriter",
    "LocalJournalWriter",
    "JournalReader",
]

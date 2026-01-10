"""Builder journal - append-only JSONL event log."""

import json
import logging
from pathlib import Path
from typing import Any

from raw.builder.events import BuildEvent, BuildEventType

logger = logging.getLogger(__name__)


class BuilderJournal:
    """Append-only journal for builder runs.

    Writes events to .raw/builds/<build_id>/events.jsonl
    Each line is a JSON object with event data.
    File is flushed after each write for crash safety.

    Usage:
        journal = BuilderJournal(build_id="build-abc123")
        journal.write(BuildStartedEvent(...))
        journal.write(GateCompletedEvent(...))
        journal.close()
    """

    def __init__(self, build_id: str, builds_dir: Path | None = None) -> None:
        """Initialize journal writer.

        Args:
            build_id: Unique build identifier
            builds_dir: Directory for builds (defaults to .raw/builds)
        """
        self.build_id = build_id

        if builds_dir is None:
            builds_dir = Path.cwd() / ".raw" / "builds"

        self.build_dir = builds_dir / build_id
        self.journal_path = self.build_dir / "events.jsonl"

        # Create directory
        self.build_dir.mkdir(parents=True, exist_ok=True)

        # Open file handle (append mode)
        self._file_handle = open(self.journal_path, "a", encoding="utf-8")

        # Track current iteration for convenience
        self.current_iteration = 0

    def write(self, event: BuildEvent) -> None:
        """Write event to journal with immediate flush.

        Args:
            event: Event to write
        """
        # Serialize event to JSON
        line = event.model_dump_json() + "\n"

        # Write and flush
        self._file_handle.write(line)
        self._file_handle.flush()

    def close(self) -> None:
        """Close journal file handle."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

    def __enter__(self) -> "BuilderJournal":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - ensure file is closed."""
        self.close()


class BuilderJournalReader:
    """Reader for builder journal files.

    Reads events.jsonl and parses into BuildEvent objects.
    Skips corrupt lines with warnings.

    Usage:
        reader = BuilderJournalReader(journal_path)
        events = reader.read_events()
        for event in events:
            print(event.event_type, event.timestamp)
    """

    def __init__(self, journal_path: Path) -> None:
        """Initialize journal reader.

        Args:
            journal_path: Path to events.jsonl file
        """
        self.journal_path = journal_path

    def read_events(self) -> list[dict[str, Any]]:
        """Read all events from journal.

        Returns:
            List of event dictionaries (not parsed into Pydantic models)

        Raises:
            FileNotFoundError: If journal file doesn't exist
        """
        if not self.journal_path.exists():
            raise FileNotFoundError(f"Journal not found: {self.journal_path}")

        events: list[dict[str, Any]] = []

        with open(self.journal_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)
                    events.append(event)
                except json.JSONDecodeError as e:
                    # Skip corrupt line with warning
                    logger.warning("Corrupt line %d in %s: %s", line_num, self.journal_path, e)
                    continue

        return events

    def read_typed_events(self) -> list[BuildEvent]:
        """Read and parse events into Pydantic models.

        Returns:
            List of typed BuildEvent objects

        Note:
            This is more expensive than read_events() due to validation.
            Use read_events() if you only need dict access.
        """
        from raw.builder.events import (
            BuildCompletedEvent,
            BuildFailedEvent,
            BuildStartedEvent,
            BuildStuckEvent,
            FileChangeAppliedEvent,
            GateCompletedEvent,
            GateStartedEvent,
            IterationCompletedEvent,
            IterationStartedEvent,
            ModeSwitchedEvent,
            PlanUpdatedEvent,
            ToolCallCompletedEvent,
            ToolCallStartedEvent,
        )

        # Map event types to classes
        event_classes = {
            BuildEventType.BUILD_STARTED: BuildStartedEvent,
            BuildEventType.BUILD_COMPLETED: BuildCompletedEvent,
            BuildEventType.BUILD_FAILED: BuildFailedEvent,
            BuildEventType.BUILD_STUCK: BuildStuckEvent,
            BuildEventType.ITERATION_STARTED: IterationStartedEvent,
            BuildEventType.ITERATION_COMPLETED: IterationCompletedEvent,
            BuildEventType.MODE_SWITCHED: ModeSwitchedEvent,
            BuildEventType.PLAN_UPDATED: PlanUpdatedEvent,
            BuildEventType.TOOL_CALL_STARTED: ToolCallStartedEvent,
            BuildEventType.TOOL_CALL_COMPLETED: ToolCallCompletedEvent,
            BuildEventType.FILE_CHANGE_APPLIED: FileChangeAppliedEvent,
            BuildEventType.GATE_STARTED: GateStartedEvent,
            BuildEventType.GATE_COMPLETED: GateCompletedEvent,
        }

        raw_events = self.read_events()
        typed_events: list[BuildEvent] = []

        for event_data in raw_events:
            event_type_str = event_data.get("event_type")
            if not event_type_str:
                continue

            try:
                event_type = BuildEventType(event_type_str)
                event_class = event_classes.get(event_type)

                if event_class:
                    typed_events.append(event_class.model_validate(event_data))
                else:
                    logger.warning("Unknown event type: %s", event_type_str)

            except ValueError as e:
                logger.warning("Invalid event data: %s", e)
                continue

        return typed_events


def list_builds(builds_dir: Path | None = None) -> list[dict[str, Any]]:
    """List all builder runs, sorted by modification time (newest first).

    Args:
        builds_dir: Directory containing builds (defaults to .raw/builds)

    Returns:
        List of build info dicts with build_id, path, and event count
    """
    if builds_dir is None:
        builds_dir = Path.cwd() / ".raw" / "builds"

    if not builds_dir.exists():
        return []

    builds = []

    for build_path in builds_dir.iterdir():
        if not build_path.is_dir():
            continue

        journal_path = build_path / "events.jsonl"
        if not journal_path.exists():
            continue

        # Count events
        event_count = 0
        with open(journal_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    event_count += 1

        builds.append(
            {
                "build_id": build_path.name,
                "path": str(build_path),
                "journal_path": str(journal_path),
                "event_count": event_count,
                "mtime": journal_path.stat().st_mtime,
            }
        )

    # Sort by modification time (newest first)
    builds.sort(key=lambda b: b["mtime"], reverse=True)

    # Remove mtime from output (internal use only)
    for build in builds:
        del build["mtime"]

    return builds


def get_last_build(builds_dir: Path | None = None) -> dict[str, Any] | None:
    """Get the most recent build.

    Args:
        builds_dir: Directory containing builds (defaults to .raw/builds)

    Returns:
        Build info dict or None if no builds found
    """
    builds = list_builds(builds_dir)
    return builds[0] if builds else None

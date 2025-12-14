"""Manifest building and persistence.

Separates manifest construction from file I/O for better testability.
"""

import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from raw_runtime.models import (
    Artifact,
    EnvironmentInfo,
    LogsInfo,
    Manifest,
    RunInfo,
    RunStatus,
    StepResult,
    WorkflowInfo,
)


class ManifestWriter(Protocol):
    """Protocol for manifest persistence.

    Implementations handle where/how manifests are saved:
    - LocalManifestWriter: Local filesystem
    - Future: S3ManifestWriter, etc.
    """

    def write(self, manifest: Manifest, path: Path) -> None:
        """Write manifest to the specified path."""
        ...


class LocalManifestWriter:
    """Writes manifests to local filesystem as JSON."""

    def write(self, manifest: Manifest, path: Path) -> None:
        """Write manifest to a local JSON file."""
        path.write_text(manifest.model_dump_json(indent=2, exclude_none=True))


class ManifestBuilder:
    """Builds workflow manifests from execution data.

    Separates manifest construction from context management,
    making it easier to test and extend.
    """

    def __init__(
        self,
        workflow_id: str,
        short_name: str,
        started_at: datetime,
        run_id: str,
        parameters: dict[str, Any] | None = None,
        workflow_dir: Path | None = None,
    ) -> None:
        """Initialize builder with workflow metadata."""
        self.workflow_id = workflow_id
        self.short_name = short_name
        self.started_at = started_at
        self.run_id = run_id
        self.parameters = parameters or {}
        self.workflow_dir = workflow_dir

        self._environment = EnvironmentInfo(
            hostname=socket.gethostname(),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            raw_version="0.1.0",
            working_directory=str(Path.cwd()),
        )

    def build(
        self,
        steps: list[StepResult],
        artifacts: list[Artifact],
        status: RunStatus,
        error: str | None = None,
    ) -> Manifest:
        """Build a complete manifest from execution data.

        Args:
            steps: List of step execution results
            artifacts: List of produced artifacts
            status: Final run status
            error: Error message if failed

        Returns:
            Complete Manifest object
        """
        now = datetime.now(timezone.utc)
        duration = (now - self.started_at).total_seconds()

        workflow_info = WorkflowInfo(
            id=self.workflow_id,
            short_name=self.short_name,
            version="1.0.0",
            created_at=self.started_at,
        )

        run_info = RunInfo(
            run_id=self.run_id,
            workflow_id=self.workflow_id,
            started_at=self.started_at,
            ended_at=now,
            status=status,
            duration_seconds=duration,
            parameters=self.parameters,
            environment=self._environment,
        )

        logs = LogsInfo()
        if self.workflow_dir:
            log_path = self.workflow_dir / "output.log"
            logs.stdout = str(log_path)

        return Manifest(
            schema_version="1.0.0",
            workflow=workflow_info,
            run=run_info,
            steps=steps,
            artifacts=artifacts,
            logs=logs,
            error=error,
        )


# Backward-compatible accessors
# Note: Can't import RuntimeContainer here due to circular import.
# These functions are kept for backward compatibility but the globals
# are managed here directly. RuntimeContainer imports from this module.

_default_writer: ManifestWriter | None = None


def get_manifest_writer() -> ManifestWriter:
    """Get the default manifest writer."""
    global _default_writer
    if _default_writer is None:
        _default_writer = LocalManifestWriter()
    return _default_writer


def set_manifest_writer(writer: ManifestWriter | None) -> None:
    """Set the default manifest writer (useful for testing)."""
    global _default_writer
    _default_writer = writer

"""Mock implementations for testing.

Provides in-memory implementations of runtime protocols that can be
used in tests without filesystem, network, or subprocess side effects.
"""

import uuid
from datetime import datetime, timezone

from raw_runtime.protocols.orchestrator import (
    Orchestrator,
    OrchestratorRunInfo,
    OrchestratorRunStatus,
)
from raw_runtime.protocols.secrets import SecretProvider


class MemoryOrchestrator:
    """In-memory orchestrator for testing.

    Stores workflow runs in memory without actually executing anything.
    Useful for testing workflow coordination logic without subprocess overhead.
    """

    def __init__(self) -> None:
        self._runs: dict[str, OrchestratorRunInfo] = {}
        self._trigger_count: int = 0

    def trigger(
        self,
        workflow_id: str,
        args: list[str] | None = None,
        wait: bool = False,
        timeout_seconds: float | None = None,
    ) -> OrchestratorRunInfo:
        """Record a trigger without actually running the workflow."""
        self._trigger_count += 1
        run_id = f"test-{uuid.uuid4().hex[:8]}"

        run = OrchestratorRunInfo(
            run_id=run_id,
            workflow_id=workflow_id,
            status=OrchestratorRunStatus.COMPLETED if wait else OrchestratorRunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc) if wait else None,
            exit_code=0 if wait else None,
            metadata={"args": args or [], "triggered_by": "MemoryOrchestrator"},
        )
        self._runs[run_id] = run
        return run

    def get_status(self, run_id: str) -> OrchestratorRunInfo:
        """Get status of a recorded run."""
        if run_id not in self._runs:
            raise ValueError(f"Run not found: {run_id}")
        return self._runs[run_id]

    def wait_for_completion(
        self,
        run_id: str,
        timeout_seconds: float | None = None,
        poll_interval: float = 1.0,
    ) -> OrchestratorRunInfo:
        """Immediately return the run as completed."""
        if run_id not in self._runs:
            raise ValueError(f"Run not found: {run_id}")

        run = self._runs[run_id]
        run.status = OrchestratorRunStatus.COMPLETED
        run.completed_at = datetime.now(timezone.utc)
        run.exit_code = 0
        return run

    def list_runs(
        self,
        workflow_id: str | None = None,
        status: OrchestratorRunStatus | None = None,
        limit: int = 100,
    ) -> list[OrchestratorRunInfo]:
        """List recorded runs with optional filtering."""
        runs = list(self._runs.values())

        if workflow_id:
            runs = [r for r in runs if r.workflow_id == workflow_id]
        if status:
            runs = [r for r in runs if r.status == status]

        return runs[:limit]

    @property
    def trigger_count(self) -> int:
        """Number of times trigger() was called."""
        return self._trigger_count

    def set_run_status(self, run_id: str, status: OrchestratorRunStatus) -> None:
        """Manually set run status for testing scenarios."""
        if run_id in self._runs:
            self._runs[run_id].status = status


class MemorySecretProvider:
    """In-memory secret provider for testing.

    Stores secrets in a dictionary. Useful for testing code that
    requires secrets without environment variables or .env files.
    """

    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        self._secrets: dict[str, str] = secrets or {}

    def get_secret(self, key: str, default: str | None = None) -> str | None:
        """Get a secret from memory."""
        return self._secrets.get(key, default)

    def has_secret(self, key: str) -> bool:
        """Check if a secret exists."""
        return key in self._secrets

    def require_secret(self, key: str) -> str:
        """Get a required secret, raising if not found."""
        value = self._secrets.get(key)
        if value is None:
            raise KeyError(f"Required secret not found: {key}")
        return value

    def set_secret(self, key: str, value: str) -> None:
        """Set a secret for testing."""
        self._secrets[key] = value

    def clear(self) -> None:
        """Clear all secrets."""
        self._secrets.clear()


# Verify protocol compliance at import time
assert isinstance(MemoryOrchestrator(), Orchestrator)
assert isinstance(MemorySecretProvider(), SecretProvider)

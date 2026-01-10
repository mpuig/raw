"""Orchestrator implementations."""

import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from raw_runtime.protocols.orchestrator import OrchestratorRunInfo, OrchestratorRunStatus

if TYPE_CHECKING:
    import httpx


class LocalOrchestrator:
    """Orchestrator that runs workflows locally via subprocess.

    Executes workflows using `uv run` in a subprocess.
    """

    def __init__(self, workflows_dir: Path | str | None = None) -> None:
        """Initialize with workflows directory.

        Args:
            workflows_dir: Path to workflows directory
                          (defaults to .raw/workflows)
        """
        if workflows_dir is None:
            workflows_dir = Path.cwd() / ".raw" / "workflows"
        self._workflows_dir = Path(workflows_dir)
        self._runs: dict[str, OrchestratorRunInfo] = {}

    def trigger(
        self,
        workflow_id: str,
        args: list[str] | None = None,
        wait: bool = False,
        timeout_seconds: float | None = None,
    ) -> OrchestratorRunInfo:
        """Trigger a workflow execution."""
        workflow_dir = self._workflows_dir / workflow_id
        run_py = workflow_dir / "run.py"

        if not workflow_dir.exists():
            raise ValueError(f"Workflow not found: {workflow_id}")
        if not run_py.exists():
            raise ValueError(f"Workflow has no run.py: {workflow_id}")

        run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        started_at = datetime.now(timezone.utc)

        info = OrchestratorRunInfo(
            run_id=run_id,
            workflow_id=workflow_id,
            status=OrchestratorRunStatus.RUNNING,
            started_at=started_at,
        )
        self._runs[run_id] = info

        cmd = ["uv", "run", "python", str(run_py)] + (args or [])

        if wait:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=workflow_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
                info.status = (
                    OrchestratorRunStatus.COMPLETED
                    if result.returncode == 0
                    else OrchestratorRunStatus.FAILED
                )
                info.completed_at = datetime.now(timezone.utc)
                info.exit_code = result.returncode
            except subprocess.TimeoutExpired:
                info.status = OrchestratorRunStatus.TIMEOUT
                info.completed_at = datetime.now(timezone.utc)
        else:
            subprocess.Popen(
                cmd,
                cwd=workflow_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        return info

    def get_status(self, run_id: str) -> OrchestratorRunInfo:
        """Get the current status of a workflow run."""
        if run_id not in self._runs:
            raise KeyError(f"Run not found: {run_id}")
        return self._runs[run_id]

    def wait_for_completion(
        self,
        run_id: str,
        timeout_seconds: float | None = None,
        poll_interval: float = 1.0,
    ) -> OrchestratorRunInfo:
        """Wait for a workflow run to complete."""
        if run_id not in self._runs:
            raise KeyError(f"Run not found: {run_id}")

        start = time.time()
        while True:
            info = self._runs[run_id]
            if info.status in (
                OrchestratorRunStatus.COMPLETED,
                OrchestratorRunStatus.FAILED,
                OrchestratorRunStatus.TIMEOUT,
            ):
                return info

            if timeout_seconds and (time.time() - start) > timeout_seconds:
                info.status = OrchestratorRunStatus.TIMEOUT
                raise TimeoutError(f"Run {run_id} did not complete within {timeout_seconds}s")

            time.sleep(poll_interval)

    def list_runs(
        self,
        workflow_id: str | None = None,
        status: OrchestratorRunStatus | None = None,
        limit: int = 100,
    ) -> list[OrchestratorRunInfo]:
        """List workflow runs with optional filtering."""
        runs = list(self._runs.values())

        if workflow_id:
            runs = [r for r in runs if r.workflow_id == workflow_id]
        if status:
            runs = [r for r in runs if r.status == status]

        runs.sort(key=lambda r: r.started_at or datetime.min, reverse=True)
        return runs[:limit]


class HttpOrchestrator:
    """Orchestrator that communicates with a RAW server via HTTP.

    Used when workflows need to be triggered remotely.
    Uses a persistent httpx.Client for connection reuse across requests.
    """

    def __init__(self, server_url: str | None = None) -> None:
        """Initialize with server URL.

        Args:
            server_url: Base URL of the RAW server (e.g., "http://localhost:8000").
                        Falls back to RAW_SERVER_URL environment variable.

        Raises:
            ValueError: If no server URL provided and RAW_SERVER_URL not set.
        """
        if server_url is None:
            server_url = os.environ.get("RAW_SERVER_URL")
        if server_url is None:
            raise ValueError("RAW_SERVER_URL not set and no server_url provided")
        self._server_url = server_url.rstrip("/")
        self._client: httpx.Client | None = None

    def _get_client(self) -> "httpx.Client":
        """Get or create the HTTP client.

        Lazy initialization allows the orchestrator to be created without
        importing httpx until actually needed. Reusing the client enables
        HTTP connection pooling for better performance.
        """
        if self._client is None:
            import httpx
            self._client = httpx.Client(timeout=30.0)
        return self._client

    def close(self) -> None:
        """Close the HTTP client and release connections."""
        if self._client is not None:
            self._client.close()
            self._client = None

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _request_with_retry(
        self, method: str, url: str, **kwargs: dict
    ) -> "httpx.Response":
        """Make HTTP request with automatic retry on transient failures.

        Uses exponential backoff: 1s, 2s, 4s (max 10s) between retries.
        Retries up to 3 times on any exception (network errors, timeouts).
        """
        client = self._get_client()
        if method == "GET":
            return client.get(url, **kwargs)
        elif method == "POST":
            return client.post(url, **kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

    @property
    def server_url(self) -> str:
        """Get the server URL."""
        return self._server_url

    def _map_status(self, status: str | None) -> OrchestratorRunStatus:
        """Map server status string to OrchestratorRunStatus."""
        if status is None:
            return OrchestratorRunStatus.UNKNOWN
        mapping = {
            "pending": OrchestratorRunStatus.PENDING,
            "running": OrchestratorRunStatus.RUNNING,
            "waiting": OrchestratorRunStatus.WAITING,
            "completed": OrchestratorRunStatus.COMPLETED,
            "success": OrchestratorRunStatus.COMPLETED,
            "failed": OrchestratorRunStatus.FAILED,
            "timeout": OrchestratorRunStatus.TIMEOUT,
        }
        return mapping.get(status, OrchestratorRunStatus.UNKNOWN)

    def trigger(
        self,
        workflow_id: str,
        args: list[str] | None = None,
        wait: bool = False,
        timeout_seconds: float | None = None,
    ) -> OrchestratorRunInfo:
        """Trigger a workflow via HTTP webhook."""
        import httpx

        url = f"{self._server_url}/webhook/{workflow_id}"
        payload = {"args": args or []}

        try:
            response = self._request_with_retry("POST", url, json=payload)
            response.raise_for_status()
            data = response.json()

            info = OrchestratorRunInfo(
                run_id=data.get("run_id", "unknown"),
                workflow_id=workflow_id,
                status=OrchestratorRunStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
            )

            if wait:
                return self.wait_for_completion(
                    info.run_id,
                    timeout_seconds=timeout_seconds,
                )

            return info

        except httpx.HTTPStatusError as e:
            raise ValueError(f"Failed to trigger workflow: {e.response.text}") from e

    def get_status(self, run_id: str) -> OrchestratorRunInfo:
        """Get run status from server."""
        url = f"{self._server_url}/runs"
        response = self._request_with_retry("GET", url)
        response.raise_for_status()

        for run in response.json():
            if run.get("run_id") == run_id:
                return OrchestratorRunInfo(
                    run_id=run["run_id"],
                    workflow_id=run.get("workflow_id", "unknown"),
                    status=OrchestratorRunStatus(run.get("status", "unknown")),
                    started_at=datetime.fromisoformat(run["started_at"])
                    if run.get("started_at")
                    else None,
                )

        raise ValueError(f"Run not found: {run_id}")

    def wait_for_completion(
        self,
        run_id: str,
        timeout_seconds: float | None = None,
        poll_interval: float = 1.0,
    ) -> OrchestratorRunInfo:
        """Poll server until run completes."""
        start = time.time()
        while True:
            info = self.get_status(run_id)
            if info.status in (
                OrchestratorRunStatus.COMPLETED,
                OrchestratorRunStatus.FAILED,
                OrchestratorRunStatus.TIMEOUT,
            ):
                return info

            if timeout_seconds and (time.time() - start) > timeout_seconds:
                raise TimeoutError(f"Run {run_id} did not complete within {timeout_seconds}s")

            time.sleep(poll_interval)

    def list_runs(
        self,
        workflow_id: str | None = None,
        status: OrchestratorRunStatus | None = None,
        limit: int = 100,
    ) -> list[OrchestratorRunInfo]:
        """List runs from server."""
        url = f"{self._server_url}/runs"
        response = self._request_with_retry("GET", url)
        response.raise_for_status()

        runs = []
        for run in response.json():
            info = OrchestratorRunInfo(
                run_id=run["run_id"],
                workflow_id=run.get("workflow_id", "unknown"),
                status=OrchestratorRunStatus(run.get("status", "unknown")),
                started_at=datetime.fromisoformat(run["started_at"])
                if run.get("started_at")
                else None,
            )
            if workflow_id and info.workflow_id != workflow_id:
                continue
            if status and info.status != status:
                continue
            runs.append(info)

        return runs[:limit]

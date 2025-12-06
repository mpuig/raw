"""Server connection for connected workflow mode.

When RAW_SERVER_URL is set, workflows connect to the server for:
- Registration (server tracks active runs)
- Event polling (approvals, webhooks)
- Heartbeat (server detects stale runs)

Without RAW_SERVER_URL, workflows run in local mode with console I/O.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Literal

import httpx
from rich.console import Console

console = Console()


class ServerConnection:
    """Connection to RAW server for event-driven workflows."""

    def __init__(self, server_url: str | None = None) -> None:
        self.server_url = server_url or os.environ.get("RAW_SERVER_URL")
        self.run_id: str | None = None
        self.workflow_id: str | None = None
        self._connected = False
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_stop = threading.Event()
        self._client: httpx.Client | None = None

    @property
    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self._connected

    def connect(self, run_id: str, workflow_id: str) -> bool:
        """Register with the server.

        Returns True if connected, False if server unreachable.
        """
        if not self.server_url:
            return False

        self.run_id = run_id
        self.workflow_id = workflow_id
        self._client = httpx.Client(base_url=self.server_url, timeout=10.0)

        try:
            response = self._client.post(
                "/runs/register",
                json={
                    "run_id": run_id,
                    "workflow_id": workflow_id,
                    "pid": os.getpid(),
                },
            )
            if response.status_code == 200:
                self._connected = True
                self._start_heartbeat()
                return True
            else:
                console.print(f"[yellow]![/] Server registration failed: {response.status_code}")
                return False
        except httpx.RequestError as e:
            console.print(f"[yellow]![/] Server unreachable: {e}")
            return False

    def disconnect(self, status: Literal["success", "failed"] = "success") -> None:
        """Disconnect from server and cleanup."""
        self._stop_heartbeat()

        if self._connected and self._client and self.run_id:
            try:
                self._client.post(
                    f"/runs/{self.run_id}/complete",
                    json={"status": status},
                )
            except httpx.RequestError:
                pass  # Best effort

        if self._client:
            self._client.close()
            self._client = None

        self._connected = False

    def mark_waiting(
        self,
        event_type: Literal["approval", "webhook"],
        step_name: str,
        prompt: str | None = None,
        options: list[str] | None = None,
        context: dict[str, Any] | None = None,
        timeout_seconds: float = 300,
    ) -> None:
        """Tell server we're waiting for an event."""
        if not self._connected or not self._client or not self.run_id:
            return

        try:
            self._client.post(
                f"/runs/{self.run_id}/waiting",
                json={
                    "event_type": event_type,
                    "step_name": step_name,
                    "prompt": prompt,
                    "options": options,
                    "context": context or {},
                    "timeout_seconds": timeout_seconds,
                },
            )
        except httpx.RequestError:
            pass  # Best effort

    def poll_events(self) -> list[dict[str, Any]]:
        """Poll for pending events (non-blocking)."""
        if not self._connected or not self._client or not self.run_id:
            return []

        try:
            response = self._client.get(f"/runs/{self.run_id}/events")
            if response.status_code == 200:
                return response.json()
        except httpx.RequestError:
            pass

        return []

    def wait_for_event(
        self,
        event_type: Literal["approval", "webhook"],
        step_name: str,
        prompt: str | None = None,
        options: list[str] | None = None,
        context: dict[str, Any] | None = None,
        timeout_seconds: float = 300,
        poll_interval: float = 1.0,
    ) -> dict[str, Any]:
        """Block until an event is received or timeout.

        Args:
            event_type: Type of event to wait for
            step_name: Name of the step waiting
            prompt: Human-readable prompt (for approvals)
            options: Available choices (for approvals)
            context: Additional context to show
            timeout_seconds: Maximum wait time (default 5 min)
            poll_interval: Seconds between polls (default 1s)

        Returns:
            Event payload dict

        Raises:
            TimeoutError: If no event received within timeout
            RuntimeError: If not connected to server
        """
        if not self._connected:
            raise RuntimeError(
                "Cannot wait for event: not connected to RAW server. "
                "Set RAW_SERVER_URL and ensure server is running."
            )

        # Notify server we're waiting
        self.mark_waiting(
            event_type=event_type,
            step_name=step_name,
            prompt=prompt,
            options=options,
            context=context,
            timeout_seconds=timeout_seconds,
        )

        # Poll until event or timeout
        start_time = time.monotonic()
        while True:
            events = self.poll_events()
            for event in events:
                if event.get("event_type") == event_type and event.get("step_name") == step_name:
                    return event.get("payload", {})

            # Check timeout
            elapsed = time.monotonic() - start_time
            if elapsed >= timeout_seconds:
                raise TimeoutError(f"Timed out waiting for {event_type} after {timeout_seconds}s")

            time.sleep(poll_interval)

    def _start_heartbeat(self) -> None:
        """Start background heartbeat thread."""
        if self._heartbeat_thread is not None:
            return

        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="raw-heartbeat",
        )
        self._heartbeat_thread.start()

    def _stop_heartbeat(self) -> None:
        """Stop heartbeat thread."""
        self._heartbeat_stop.set()
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=2.0)
            self._heartbeat_thread = None

    def _heartbeat_loop(self) -> None:
        """Send heartbeat every 30s."""
        while not self._heartbeat_stop.is_set():
            if self._client and self.run_id:
                try:
                    self._client.post(f"/runs/{self.run_id}/heartbeat")
                except httpx.RequestError:
                    pass  # Best effort

            # Sleep in small increments to allow quick shutdown
            for _ in range(30):
                if self._heartbeat_stop.is_set():
                    break
                time.sleep(1)


# Global connection instance
_connection: ServerConnection | None = None


def get_connection() -> ServerConnection | None:
    """Get the current server connection."""
    return _connection


def set_connection(connection: ServerConnection | None) -> None:
    """Set the global server connection."""
    global _connection
    _connection = connection


def init_connection(run_id: str, workflow_id: str) -> ServerConnection:
    """Initialize and connect to server if RAW_SERVER_URL is set.

    Returns a ServerConnection (connected or not).
    """
    global _connection
    _connection = ServerConnection()
    if _connection.server_url:
        if _connection.connect(run_id, workflow_id):
            console.print(f"[dim]Connected to {_connection.server_url}[/]")
        else:
            console.print("[dim]Running in local mode (server unavailable)[/]")
    return _connection

"""EventBus protocol and implementations.

The EventBus is the central communication mechanism for RAW workflows.
All state changes flow through events, enabling decoupled handlers for:
- Console output (raw run)
- File logging (raw serve)
- Human-in-the-loop approvals
- External integrations

Two modes:
- LocalEventBus: Synchronous, in-process bus for simple `raw run`
- AsyncEventBus: Async-native bus using asyncio.Queue for `raw serve`

Note: Protocol is in raw_runtime.protocols.bus,
      Implementations are in raw_runtime.drivers.bus.
      This module re-exports for backwards compatibility.
"""

import asyncio
from collections.abc import Awaitable, Callable

from raw_runtime.drivers.bus import (
    AsyncEventBus,
    LocalEventBus,
    NullEventBus,
)
from raw_runtime.events import Event
from raw_runtime.protocols.bus import EventBus

SyncHandler = Callable[[Event], None]
AsyncHandler = Callable[[Event], Awaitable[None]]


class ApprovalRegistry:
    """Registry for pending approval requests using asyncio.Future.

    Used by `raw serve` to track workflows waiting for human approval.
    When an approval request is made, a Future is created.
    When the approval is received (via API), the Future is resolved.

    Usage:
        registry = ApprovalRegistry()

        # Workflow requests approval
        future = registry.request("workflow-123", "deploy")
        decision = await future  # Blocks until resolved

        # API receives approval
        registry.resolve("workflow-123", "deploy", "approve")
    """

    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Future[str]] = {}

    def _make_key(self, workflow_id: str, step_name: str, run_id: str | None = None) -> str:
        if run_id:
            return f"{workflow_id}:{run_id}:{step_name}"
        return f"{workflow_id}:{step_name}"

    def request(
        self, workflow_id: str, step_name: str, run_id: str | None = None
    ) -> asyncio.Future[str]:
        """Create a pending approval request.

        Args:
            workflow_id: The workflow identifier
            step_name: The step requesting approval
            run_id: Optional run identifier for concurrent run support

        Returns a Future that resolves when approval is received.
        """
        key = self._make_key(workflow_id, step_name, run_id)
        if key in self._pending:
            raise ValueError(f"Approval already pending for {key}")

        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        self._pending[key] = future
        return future

    def resolve(
        self, workflow_id: str, step_name: str, decision: str, run_id: str | None = None
    ) -> bool:
        """Resolve a pending approval request.

        Returns True if the approval was found and resolved.
        """
        key = self._make_key(workflow_id, step_name, run_id)
        future = self._pending.pop(key, None)
        if future is None:
            return False
        future.set_result(decision)
        return True

    def cancel(
        self, workflow_id: str, step_name: str, reason: str = "Cancelled", run_id: str | None = None
    ) -> bool:
        """Cancel a pending approval request."""
        key = self._make_key(workflow_id, step_name, run_id)
        future = self._pending.pop(key, None)
        if future is None:
            return False
        if not future.done():
            future.set_exception(asyncio.CancelledError(reason))
        return True

    def is_pending(self, workflow_id: str, step_name: str, run_id: str | None = None) -> bool:
        """Check if an approval is pending."""
        key = self._make_key(workflow_id, step_name, run_id)
        return key in self._pending

    def list_pending(self) -> list[tuple[str, str, str | None]]:
        """List all pending approvals as (workflow_id, run_id, step_name) tuples."""
        result: list[tuple[str, str, str | None]] = []
        for key in self._pending:
            parts = key.split(":")
            if len(parts) == 3:
                result.append((parts[0], parts[1], parts[2]))
            else:
                result.append((parts[0], None, parts[1]))
        return result


__all__ = [
    "EventBus",
    "LocalEventBus",
    "AsyncEventBus",
    "NullEventBus",
    "ApprovalRegistry",
    "SyncHandler",
    "AsyncHandler",
]

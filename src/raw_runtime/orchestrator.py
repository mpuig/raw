"""Orchestrator abstraction for workflow triggering and management.

Provides a protocol for triggering workflows and tracking their status,
enabling:
- Local subprocess execution (default for `raw run`)
- HTTP-based orchestration (for `raw serve`)
- Future: Kubernetes, AWS Step Functions, etc.

Note: Protocol is in raw_runtime.protocols.orchestrator,
      Implementations are in raw_runtime.drivers.orchestrator.
      This module re-exports for backwards compatibility.
"""

from raw_runtime.container import RuntimeContainer
from raw_runtime.drivers.orchestrator import HttpOrchestrator, LocalOrchestrator
from raw_runtime.protocols.orchestrator import (
    Orchestrator,
    OrchestratorRunInfo,
    OrchestratorRunStatus,
)


# Backward-compatible accessors that delegate to RuntimeContainer


def get_orchestrator() -> Orchestrator:
    """Get the current orchestrator.

    Auto-creates an orchestrator if none is set:
    - HttpOrchestrator if RAW_SERVER_URL is set
    - LocalOrchestrator otherwise
    """
    return RuntimeContainer.orchestrator()


def set_orchestrator(orchestrator: Orchestrator | None) -> None:
    """Set the global orchestrator."""
    RuntimeContainer.set_orchestrator(orchestrator)


__all__ = [
    "OrchestratorRunStatus",
    "OrchestratorRunInfo",
    "Orchestrator",
    "LocalOrchestrator",
    "HttpOrchestrator",
    "get_orchestrator",
    "set_orchestrator",
]

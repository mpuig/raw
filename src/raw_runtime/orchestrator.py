"""Orchestrator abstraction for workflow triggering and management.

This module re-exports the Orchestrator protocol and its implementations.
Accessor functions delegate to RuntimeContainer for centralized DI.
"""

from pathlib import Path

from raw_runtime.container import RuntimeContainer
from raw_runtime.drivers.orchestrator import HttpOrchestrator, LocalOrchestrator
from raw_runtime.protocols.orchestrator import (
    Orchestrator,
    OrchestratorRunInfo,
    OrchestratorRunStatus,
)


def get_orchestrator(workflows_dir: Path | None = None) -> Orchestrator:
    """Get the current orchestrator."""
    return RuntimeContainer.orchestrator(workflows_dir)


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
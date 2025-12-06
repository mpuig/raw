"""RAW Runtime Protocols - Interface definitions.

This package contains Protocol classes (interfaces) that define contracts
for the various abstractions in raw_runtime. Implementations are in
raw_runtime.drivers.

Protocols:
- StorageBackend: Artifact and manifest persistence
- SecretProvider: Credential and secret management
- Orchestrator: Workflow triggering and status
- TelemetrySink: Metrics and event logging
- EventBus: Event pub/sub system
- ApprovalHandler: Human-in-the-loop approval
- HumanInterface: General human interaction channel

Import protocols directly from their modules to avoid circular imports:
    from raw_runtime.protocols.storage import StorageBackend
"""

__all__ = [
    "ApprovalHandler",
    "AsyncHumanInterface",
    "EventBus",
    "EventSeverity",
    "HumanInterface",
    "Orchestrator",
    "OrchestratorRunInfo",
    "OrchestratorRunStatus",
    "SecretProvider",
    "StorageBackend",
    "TelemetrySink",
]


def __getattr__(name: str) -> type:
    """Lazy imports to avoid circular dependencies."""
    if name == "ApprovalHandler":
        from raw_runtime.protocols.approval import ApprovalHandler

        return ApprovalHandler
    if name == "EventBus":
        from raw_runtime.protocols.bus import EventBus

        return EventBus
    if name in ("HumanInterface", "AsyncHumanInterface"):
        from raw_runtime.protocols import human

        return getattr(human, name)
    if name in ("Orchestrator", "OrchestratorRunInfo", "OrchestratorRunStatus"):
        from raw_runtime.protocols import orchestrator

        return getattr(orchestrator, name)
    if name == "SecretProvider":
        from raw_runtime.protocols.secrets import SecretProvider

        return SecretProvider
    if name == "StorageBackend":
        from raw_runtime.protocols.storage import StorageBackend

        return StorageBackend
    if name in ("TelemetrySink", "EventSeverity"):
        from raw_runtime.protocols import telemetry

        return getattr(telemetry, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

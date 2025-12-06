"""RAW Runtime Drivers - Protocol implementations.

This package contains concrete implementations of the protocols
defined in raw_runtime.protocols.

Drivers:
- Storage: FileSystemStorage, MemoryStorage
- Secrets: EnvVarSecretProvider, DotEnvSecretProvider, ChainedSecretProvider, CachingSecretProvider
- Orchestrator: LocalOrchestrator, HttpOrchestrator
- Telemetry: NullSink, ConsoleSink, JsonFileSink, MemorySink, CompositeSink
- Bus: LocalEventBus, AsyncEventBus, NullEventBus
- Approval: ConsoleApprovalHandler, AutoApprovalHandler
- Human: ConsoleInterface, AutoInterface, ServerInterface
"""

from raw_runtime.drivers.approval import AutoApprovalHandler, ConsoleApprovalHandler
from raw_runtime.drivers.bus import AsyncEventBus, LocalEventBus, NullEventBus
from raw_runtime.drivers.human import AutoInterface, ConsoleInterface, ServerInterface
from raw_runtime.drivers.orchestrator import HttpOrchestrator, LocalOrchestrator
from raw_runtime.drivers.secrets import (
    CachingSecretProvider,
    ChainedSecretProvider,
    DotEnvSecretProvider,
    EnvVarSecretProvider,
)
from raw_runtime.drivers.storage import FileSystemStorage, MemoryStorage
from raw_runtime.drivers.telemetry import (
    CompositeSink,
    ConsoleSink,
    JsonFileSink,
    MemorySink,
    NullSink,
)

__all__ = [
    # Approval
    "AutoApprovalHandler",
    "ConsoleApprovalHandler",
    # Bus
    "AsyncEventBus",
    "LocalEventBus",
    "NullEventBus",
    # Human
    "AutoInterface",
    "ConsoleInterface",
    "ServerInterface",
    # Orchestrator
    "HttpOrchestrator",
    "LocalOrchestrator",
    # Secrets
    "CachingSecretProvider",
    "ChainedSecretProvider",
    "DotEnvSecretProvider",
    "EnvVarSecretProvider",
    # Storage
    "FileSystemStorage",
    "MemoryStorage",
    # Telemetry
    "CompositeSink",
    "ConsoleSink",
    "JsonFileSink",
    "MemorySink",
    "NullSink",
]

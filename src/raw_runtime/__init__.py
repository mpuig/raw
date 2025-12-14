"""RAW Runtime - Core library for workflow execution.

This module provides the BaseWorkflow class and decorators for RAW workflows.

Usage:
    from pydantic import BaseModel, Field
    from raw_runtime import BaseWorkflow, step

    class MyParams(BaseModel):
        name: str = Field(..., description="Name to greet")

    class MyWorkflow(BaseWorkflow[MyParams]):
        @step("greet")
        def greet(self) -> str:
            return f"Hello, {self.params.name}!"

        def run(self) -> int:
            message = self.greet()
            self.save("greeting.txt", message)
            return 0

    if __name__ == "__main__":
        MyWorkflow.main()
"""

from raw_runtime.approval import (
    ApprovalHandler,
    AutoApprovalHandler,
    ConsoleApprovalHandler,
    get_approval_handler,
    get_approval_registry,
    set_approval_handler,
    set_approval_registry,
    wait_for_approval,
    wait_for_approval_async,
    wait_for_webhook,
)
from raw_runtime.base import BaseWorkflow, cache, retry, step
from raw_runtime.bus import (
    ApprovalRegistry,
    AsyncEventBus,
    EventBus,
    LocalEventBus,
    NullEventBus,
)
from raw_runtime.connection import (
    ServerConnection,
    get_connection,
    init_connection,
    set_connection,
)
from raw_runtime.context import (
    WorkflowContext,
    get_workflow_context,
    set_workflow_context,
)
from raw_runtime.manifest import (
    LocalManifestWriter,
    ManifestBuilder,
    ManifestWriter,
    get_manifest_writer,
    set_manifest_writer,
)
from raw_runtime.decorators import cache_step, conditional, raw_step
from raw_runtime.env import (
    ensure_env_loaded,
    get_available_llm_providers,
    get_available_providers,
    get_preferred_llm_provider,
    load_dotenv,
    require_provider,
)
from raw_runtime.events import (
    ApprovalReceivedEvent,
    ApprovalRequestedEvent,
    ApprovalTimeoutEvent,
    ArtifactCreatedEvent,
    BaseEvent,
    CacheHitEvent,
    CacheMissEvent,
    Event,
    EventType,
    StepCompletedEvent,
    StepFailedEvent,
    StepRetryEvent,
    StepSkippedEvent,
    StepStartedEvent,
    WorkflowCompletedEvent,
    WorkflowFailedEvent,
    WorkflowStartedEvent,
    WorkflowTriggeredEvent,
)
from raw_runtime.handlers import ConsoleEventHandler
from raw_runtime.models import (
    Artifact,
    EnvironmentInfo,
    LogsInfo,
    Manifest,
    RunInfo,
    RunStatus,
    StepResult,
    StepStatus,
    WorkflowInfo,
)
from raw_runtime.orchestrator import (
    HttpOrchestrator,
    LocalOrchestrator,
    Orchestrator,
    OrchestratorRunInfo,
    OrchestratorRunStatus,
    get_orchestrator,
    set_orchestrator,
)
from raw_runtime.secrets import (
    CachingSecretProvider,
    ChainedSecretProvider,
    DotEnvSecretProvider,
    EnvVarSecretProvider,
    SecretProvider,
    get_secret,
    get_secret_provider,
    require_secret,
    set_secret_provider,
)
from raw_runtime.storage import (
    FileSystemStorage,
    MemoryStorage,
    StorageBackend,
    get_storage,
    set_storage,
)
from raw_runtime.telemetry import (
    CompositeSink,
    ConsoleSink,
    EventSeverity,
    JsonFileSink,
    MemorySink,
    NullSink,
    TelemetrySink,
    get_telemetry_sink,
    log_event,
    log_metric,
    set_telemetry_sink,
)

__version__ = "0.1.0"

__all__ = [
    # Base class (primary API)
    "BaseWorkflow",
    # Decorators (clean aliases)
    "step",
    "cache",
    "retry",
    "conditional",
    # Decorators (legacy names)
    "raw_step",
    "cache_step",
    # Context
    "WorkflowContext",
    "get_workflow_context",
    "set_workflow_context",
    # Manifest
    "ManifestBuilder",
    "ManifestWriter",
    "LocalManifestWriter",
    "get_manifest_writer",
    "set_manifest_writer",
    # EventBus
    "EventBus",
    "LocalEventBus",
    "AsyncEventBus",
    "NullEventBus",
    "ApprovalRegistry",
    # Event handlers
    "ConsoleEventHandler",
    # Events
    "Event",
    "EventType",
    "BaseEvent",
    "WorkflowTriggeredEvent",
    "WorkflowStartedEvent",
    "WorkflowCompletedEvent",
    "WorkflowFailedEvent",
    "StepStartedEvent",
    "StepCompletedEvent",
    "StepFailedEvent",
    "StepSkippedEvent",
    "StepRetryEvent",
    "ApprovalRequestedEvent",
    "ApprovalReceivedEvent",
    "ApprovalTimeoutEvent",
    "ArtifactCreatedEvent",
    "CacheHitEvent",
    "CacheMissEvent",
    # Approval (human-in-the-loop)
    "wait_for_approval",
    "wait_for_approval_async",
    "wait_for_webhook",
    "ApprovalHandler",
    "ConsoleApprovalHandler",
    "AutoApprovalHandler",
    "get_approval_handler",
    "set_approval_handler",
    "ApprovalRegistry",
    "get_approval_registry",
    "set_approval_registry",
    # Models
    "StepResult",
    "StepStatus",
    "WorkflowInfo",
    "RunInfo",
    "RunStatus",
    "Artifact",
    "Manifest",
    "EnvironmentInfo",
    "LogsInfo",
    # Environment & Providers
    "load_dotenv",
    "ensure_env_loaded",
    "get_available_providers",
    "get_available_llm_providers",
    "get_preferred_llm_provider",
    "require_provider",
    # Server Connection
    "ServerConnection",
    "get_connection",
    "set_connection",
    "init_connection",
    # Storage
    "StorageBackend",
    "FileSystemStorage",
    "MemoryStorage",
    "get_storage",
    "set_storage",
    # Orchestrator
    "Orchestrator",
    "LocalOrchestrator",
    "HttpOrchestrator",
    "OrchestratorRunInfo",
    "OrchestratorRunStatus",
    "get_orchestrator",
    "set_orchestrator",
    # Secrets
    "SecretProvider",
    "EnvVarSecretProvider",
    "DotEnvSecretProvider",
    "ChainedSecretProvider",
    "CachingSecretProvider",
    "get_secret_provider",
    "set_secret_provider",
    "get_secret",
    "require_secret",
    # Telemetry
    "TelemetrySink",
    "NullSink",
    "ConsoleSink",
    "JsonFileSink",
    "MemorySink",
    "CompositeSink",
    "EventSeverity",
    "get_telemetry_sink",
    "set_telemetry_sink",
    "log_metric",
    "log_event",
]

"""RAW Core - Foundation protocols, events, errors, and DI container.

This package provides the core abstractions shared across the RAW Platform:
- Protocols: Interface definitions for loose coupling
- Events: Immutable event types for streaming output
- Errors: Structured error hierarchy for handling
"""

__version__ = "0.1.0"

# Re-export commonly used items at package level
from raw_core.errors import (
    ConfigurationError,
    ErrorAction,
    ErrorDecision,
    ErrorPolicy,
    LLMServiceError,
    MissingAPIKeyError,
    PlatformError,
    ServiceError,
    STTServiceError,
    TTSServiceError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolTimeoutError,
)
from raw_core.events import (
    Event,
    StepCompleted,
    StepStarted,
    TextChunk,
    ToolCallEvent,
    ToolResultEvent,
    TurnComplete,
    WorkflowCompleted,
    WorkflowStarted,
)
from raw_core.protocols import (
    EventBus,
    LLMChunk,
    LLMDriver,
    StorageBackend,
    ToolExecutor,
)

__all__ = [
    # Protocols
    "EventBus",
    "LLMChunk",
    "LLMDriver",
    "StorageBackend",
    "ToolExecutor",
    # Events
    "Event",
    "StepCompleted",
    "StepStarted",
    "TextChunk",
    "ToolCallEvent",
    "ToolResultEvent",
    "TurnComplete",
    "WorkflowCompleted",
    "WorkflowStarted",
    # Errors
    "ConfigurationError",
    "ErrorAction",
    "ErrorDecision",
    "ErrorPolicy",
    "LLMServiceError",
    "MissingAPIKeyError",
    "PlatformError",
    "ServiceError",
    "STTServiceError",
    "TTSServiceError",
    "ToolExecutionError",
    "ToolNotFoundError",
    "ToolTimeoutError",
]

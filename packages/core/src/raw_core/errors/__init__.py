"""Error definitions for RAW Platform.

Structured error hierarchy for differentiated handling.
"""

from raw_core.errors.base import (
    ErrorAction,
    ErrorDecision,
    ErrorPolicy,
    PlatformError,
)
from raw_core.errors.execution import (
    ConfigurationError,
    MissingAPIKeyError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolTimeoutError,
)
from raw_core.errors.service import (
    LLMServiceError,
    ServiceError,
    STTServiceError,
    TTSServiceError,
)

__all__ = [
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

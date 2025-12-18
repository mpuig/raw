"""Base error classes for RAW Platform."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol


class ErrorAction(Enum):
    """Action to take when an error occurs."""

    RETRY = auto()
    ESCALATE = auto()
    LOG_AND_CONTINUE = auto()


class PlatformError(Exception):
    """Base exception for all RAW Platform errors."""

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


@dataclass
class ErrorDecision:
    """Decision from error policy."""

    action: ErrorAction
    reason: str
    retry_delay: float = 0.0


class ErrorPolicy(Protocol):
    """Strategy for handling different error types."""

    def decide(self, error: Exception, retry_count: int) -> ErrorDecision:
        """Decide how to handle an error."""
        ...

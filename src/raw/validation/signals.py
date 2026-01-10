"""Completion signals for agent-native workflows.

Explicit completion signals replace implicit integer exit codes, making
workflow results clear and actionable for agents.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CompletionSignal(str, Enum):
    """Completion signal for workflow execution.

    Following agent-native principles, workflows should explicitly signal
    their completion state rather than relying on implicit exit codes.
    """

    SUCCESS = "success"  # Workflow succeeded, can continue execution
    ERROR = "error"  # Workflow failed, can retry with different inputs
    COMPLETE = "complete"  # Workflow completed, stop execution chain


class WorkflowResult(BaseModel):
    """Result of a workflow execution with explicit completion signal.

    Attributes:
        signal: The completion signal (success, error, or complete)
        message: Human-readable description of the result
        data: Optional structured data returned by the workflow
        exit_code: Legacy integer exit code for backward compatibility
    """

    signal: CompletionSignal = Field(..., description="Completion signal")
    message: str = Field(..., description="Human-readable result message")
    data: Any = Field(default=None, description="Optional result data")
    exit_code: int = Field(default=0, description="Legacy exit code (0=success, non-zero=error)")

    @classmethod
    def success(cls, message: str, data: Any = None) -> "WorkflowResult":
        """Create a success result.

        Indicates the workflow completed successfully and execution can continue.

        Args:
            message: Description of what succeeded
            data: Optional result data

        Returns:
            WorkflowResult with SUCCESS signal

        Example:
            return WorkflowResult.success("Fetched 42 items", data={"count": 42})
        """
        return cls(signal=CompletionSignal.SUCCESS, message=message, data=data, exit_code=0)

    @classmethod
    def error(cls, message: str, exit_code: int = 1) -> "WorkflowResult":
        """Create an error result.

        Indicates the workflow failed but can be retried with different inputs
        or configuration. The error is recoverable.

        Args:
            message: Description of what failed
            exit_code: Non-zero exit code for legacy compatibility

        Returns:
            WorkflowResult with ERROR signal

        Example:
            return WorkflowResult.error("API rate limit exceeded, retry in 60s")
        """
        return cls(signal=CompletionSignal.ERROR, message=message, data=None, exit_code=exit_code)

    @classmethod
    def complete(cls, message: str, data: Any = None) -> "WorkflowResult":
        """Create a complete result.

        Indicates the workflow has fully completed and no further execution
        is needed. This is a terminal state that stops execution chains.

        Args:
            message: Description of completion
            data: Optional final result data

        Returns:
            WorkflowResult with COMPLETE signal

        Example:
            return WorkflowResult.complete("All tasks processed", data={"total": 100})
        """
        return cls(signal=CompletionSignal.COMPLETE, message=message, data=data, exit_code=0)

    def is_success(self) -> bool:
        """Check if result indicates success."""
        return self.signal in (CompletionSignal.SUCCESS, CompletionSignal.COMPLETE)

    def is_error(self) -> bool:
        """Check if result indicates error."""
        return self.signal == CompletionSignal.ERROR

    def is_complete(self) -> bool:
        """Check if result indicates completion (terminal state)."""
        return self.signal == CompletionSignal.COMPLETE

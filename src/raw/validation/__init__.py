"""Workflow validation with explicit completion signals.

This module provides validation for workflow structure and dependencies,
as well as explicit completion signals for agent-native workflow execution.

Following the agent-native principle: workflows should return .success(),
.error(), or .complete() instead of just integers.
"""

from raw.validation.signals import CompletionSignal, WorkflowResult
from raw.validation.validator import ValidationResult, WorkflowValidator

__all__ = [
    "CompletionSignal",
    "WorkflowResult",
    "ValidationResult",
    "WorkflowValidator",
]

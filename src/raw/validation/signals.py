"""Completion signals for agent-native workflows.

DEPRECATED: This module now re-exports from raw_runtime.signals for backward compatibility.
New code should import directly from raw_runtime.signals.
"""

# Re-export from raw_runtime to maintain backward compatibility
from raw_runtime.signals import CompletionSignal, WorkflowResult

__all__ = ["CompletionSignal", "WorkflowResult"]

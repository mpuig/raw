"""Protocol definitions for RAW Platform.

Protocols define contracts between components, enabling loose coupling
and easy testing through mock implementations.
"""

from raw_core.protocols.bus import EventBus
from raw_core.protocols.executor import ToolExecutor
from raw_core.protocols.llm import LLMChunk, LLMDriver
from raw_core.protocols.storage import StorageBackend

__all__ = [
    "EventBus",
    "LLMChunk",
    "LLMDriver",
    "StorageBackend",
    "ToolExecutor",
]

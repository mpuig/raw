"""RAW Bot - Transport-agnostic conversation engine.

Provides the core conversation engine that manages LLM interactions,
tool execution, and conversation state independent of transport layer.
"""

__version__ = "0.1.0"

from raw_bot.context import ContextManager
from raw_bot.engine import BotConfig, ConversationEngine, EngineMiddleware

__all__ = [
    "BotConfig",
    "ContextManager",
    "ConversationEngine",
    "EngineMiddleware",
]

"""Conversation context management.

Manages message history, token tracking, and compaction for LLM context windows.
"""

from __future__ import annotations

import json
from typing import Any


class ContextManager:
    """Manages conversation history and context for LLM interactions.

    Handles message storage, token estimation, and provides methods for
    adding different message types (user, assistant, tool calls/results).
    """

    def __init__(self, max_tokens: int = 8000) -> None:
        self.messages: list[dict[str, Any]] = []
        self.max_tokens = max_tokens
        self._system_message: dict[str, Any] | None = None
        self._estimated_tokens = 0

    def initialize(self, system_prompt: str) -> None:
        """Initialize context with system prompt."""
        self._system_message = {"role": "system", "content": system_prompt}
        self.messages = [self._system_message]
        self._estimated_tokens = self._estimate_tokens(system_prompt)

    def add_user_message(self, content: str) -> None:
        """Add a user message to the context."""
        self.messages.append({"role": "user", "content": content})
        self._estimated_tokens += self._estimate_tokens(content)

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the context."""
        self.messages.append({"role": "assistant", "content": content})
        self._estimated_tokens += self._estimate_tokens(content)

    def add_tool_call(self, message: dict[str, Any]) -> None:
        """Add a tool call message to the context."""
        self.messages.append(message)
        self._estimated_tokens += self._estimate_tokens(json.dumps(message))

    def add_tool_result(
        self, tool_call_id: str, result: Any, truncate: bool = True
    ) -> None:
        """Add a tool result to the context."""
        result_str = json.dumps(result, default=str)
        if truncate and len(result_str) > 2000:
            result_str = result_str[:2000] + "... [truncated]"

        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result_str,
        })
        self._estimated_tokens += self._estimate_tokens(result_str)

    def get_messages(self) -> list[dict[str, Any]]:
        """Get a copy of all messages."""
        return self.messages.copy()

    def update_last_assistant_message(self, content: str) -> bool:
        """Update the last assistant message (for interruption handling)."""
        for msg in reversed(self.messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                msg["content"] = content
                return True
        return False

    def should_compact(self) -> bool:
        """Check if context needs compaction."""
        return self._estimated_tokens > self.max_tokens * 0.8

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token)."""
        return len(text) // 4

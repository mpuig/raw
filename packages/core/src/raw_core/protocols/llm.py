"""LLM driver protocol for multi-provider support."""

from collections.abc import AsyncIterator
from typing import Any, Protocol

from pydantic import BaseModel, Field


class LLMChunk(BaseModel):
    """A chunk from streaming LLM response.

    Value object representing a single piece of a streaming LLM response.
    Frozen for safe concurrent handling in async pipelines.
    """

    model_config = {"frozen": True}

    content: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    finish_reason: str | None = None


class LLMDriver(Protocol):
    """Protocol for LLM providers.

    Implementations wrap different LLM APIs (OpenAI, Anthropic, etc.)
    behind a unified streaming interface.
    """

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[LLMChunk]:
        """Stream a chat completion.

        Args:
            messages: Conversation history in OpenAI format.
            model: Model identifier (e.g., "gpt-4o", "claude-3-opus").
            tools: Tool definitions in OpenAI format.
            temperature: Sampling temperature.

        Yields:
            LLMChunk events with content deltas and tool calls.
        """
        ...

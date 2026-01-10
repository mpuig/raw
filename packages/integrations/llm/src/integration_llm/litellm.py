"""LiteLLM driver implementation for multi-provider LLM support."""

from collections.abc import AsyncIterator
from typing import Any

import litellm
from raw_core import LLMChunk, LLMServiceError


def _accumulate_tool_call_delta(
    accumulated: list[dict[str, Any]],
    tool_call_delta: Any,
) -> None:
    """Accumulate a tool call delta into the accumulated list.

    Why: Streaming tool calls arrive in fragments that must be reassembled.
    We maintain a list indexed by tool call position, accumulating fragments
    until the stream completes.
    """
    idx = tool_call_delta.index
    while idx >= len(accumulated):
        accumulated.append({"id": "", "name": "", "arguments": ""})

    if tool_call_delta.id:
        accumulated[idx]["id"] = tool_call_delta.id
    if tool_call_delta.function:
        if tool_call_delta.function.name:
            accumulated[idx]["name"] = tool_call_delta.function.name
        if tool_call_delta.function.arguments:
            accumulated[idx]["arguments"] += tool_call_delta.function.arguments


class LiteLLMDriver:
    """LLM driver using LiteLLM for multi-provider support.

    Supports 100+ providers including:
    - OpenAI (gpt-4o, gpt-4-turbo, etc.)
    - Anthropic (claude-3-opus, claude-3-sonnet, etc.)
    - Azure OpenAI
    - AWS Bedrock
    - Google Vertex AI
    - Ollama (local models)
    - And many more...

    Model names follow LiteLLM conventions:
    - OpenAI: "gpt-4o", "gpt-4-turbo"
    - Anthropic: "claude-3-opus-20240229", "claude-3-sonnet-20240229"
    - Azure: "azure/deployment-name"
    - Bedrock: "bedrock/anthropic.claude-3-sonnet"
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        default_headers: dict[str, str] | None = None,
    ):
        """Initialize the LiteLLM driver.

        Args:
            api_key: Optional API key (uses env vars by default).
            api_base: Optional custom API base URL.
            default_headers: Optional headers for all requests.
        """
        self._api_key = api_key
        self._api_base = api_base
        self._default_headers = default_headers or {}

    def _build_completion_kwargs(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None,
        temperature: float,
    ) -> dict[str, Any]:
        """Build kwargs for litellm.acompletion.

        Why: Centralizes the construction of LiteLLM request parameters,
        ensuring consistent handling of optional authentication and configuration.
        """
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._api_base:
            kwargs["api_base"] = self._api_base
        if self._default_headers:
            kwargs["extra_headers"] = self._default_headers
        return kwargs

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[LLMChunk]:
        """Stream a chat completion using LiteLLM.

        Implements the LLMDriver protocol, providing a unified streaming
        interface across multiple LLM providers.

        Args:
            messages: Conversation history in OpenAI format.
            model: Model identifier (e.g., "gpt-4o", "claude-3-opus").
            tools: Tool definitions in OpenAI format.
            temperature: Sampling temperature.

        Yields:
            LLMChunk events with content deltas and tool calls.

        Raises:
            LLMServiceError: If completion request or streaming fails.
        """
        kwargs = self._build_completion_kwargs(messages, model, tools, temperature)

        try:
            response = await litellm.acompletion(**kwargs)
        except Exception as e:
            raise LLMServiceError(f"LLM completion failed: {e}", cause=e) from e

        accumulated_tool_calls: list[dict[str, Any]] = []

        try:
            async for chunk in response:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason

                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    for tc in delta.tool_calls:
                        _accumulate_tool_call_delta(accumulated_tool_calls, tc)

                yield LLMChunk(
                    content=delta.content if hasattr(delta, "content") else None,
                    tool_calls=accumulated_tool_calls.copy() if finish_reason else [],
                    finish_reason=finish_reason,
                )
        except LLMServiceError:
            raise
        except Exception as e:
            raise LLMServiceError(f"LLM streaming failed: {e}", cause=e) from e

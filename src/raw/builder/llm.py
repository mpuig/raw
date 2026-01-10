"""LLM client for builder agent."""

import os
from typing import Any

from anthropic import Anthropic
from anthropic.types import MessageParam


class BuilderLLM:
    """LLM client for builder plan and execute modes.

    Wraps Anthropic API with builder-specific configuration.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
    ) -> None:
        """Initialize LLM client.

        Args:
            model: Claude model to use
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.model = model
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def generate(
        self,
        system: str,
        messages: list[MessageParam],
        max_tokens: int = 8192,
        temperature: float = 1.0,
    ) -> str:
        """Generate completion from messages.

        Args:
            system: System prompt
            messages: Conversation messages
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text response
        """
        response = self.client.messages.create(
            model=self.model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Extract text from response
        text_blocks = [block.text for block in response.content if hasattr(block, "text")]
        return "\n".join(text_blocks)

    def generate_with_thinking(
        self,
        system: str,
        messages: list[MessageParam],
        max_tokens: int = 8192,
        temperature: float = 1.0,
    ) -> tuple[str, str]:
        """Generate completion with extended thinking enabled.

        Args:
            system: System prompt
            messages: Conversation messages
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Tuple of (thinking, response) text
        """
        response = self.client.messages.create(
            model=self.model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            thinking={
                "type": "enabled",
                "budget_tokens": 10000,
            },
        )

        # Extract thinking and text blocks
        thinking_blocks = [
            block.thinking for block in response.content if hasattr(block, "thinking")
        ]
        text_blocks = [block.text for block in response.content if hasattr(block, "text")]

        thinking = "\n".join(thinking_blocks)
        text = "\n".join(text_blocks)

        return thinking, text

"""Summarize capability - Text summarization.

LLM-powered text summarization for documents, articles, and conversations.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.capability import Capability, CapabilityEvent


class SummarizeCapability(Capability):
    """Text summarization capability.

    Usage:
        result = await self.capability("summarize").call(
            text="Long document text here...",
            max_length=100,  # words
            style="bullet_points",
        )
        summary = result.data["summary"]
    """

    name: ClassVar[str] = "summarize"
    description: ClassVar[str] = "Summarize text using LLMs"
    triggers: ClassVar[list[str]] = []

    async def run(self, **config: Any) -> AsyncIterator[CapabilityEvent]:
        """Summarize text.

        Args:
            text: Text to summarize
            max_length: Maximum summary length in words
            style: Summary style ("paragraph", "bullet_points", "tldr")
            focus: Optional focus area for the summary
            model: LLM model to use (default from config)

        Yields:
            CapabilityEvent with types: started, completed (with summary), failed
        """
        raise NotImplementedError(
            "Summarize capability not implemented. "
            "Configure LLM API credentials to use this capability."
        )
        yield

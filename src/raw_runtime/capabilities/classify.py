"""Classify capability - Text classification.

LLM-powered text classification for sentiment, intent, categories, etc.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.capability import Capability, CapabilityEvent


class ClassifyCapability(Capability):
    """Text classification capability.

    Usage:
        # Sentiment analysis
        result = await self.capability("classify").call(
            text="I love this product!",
            categories=["positive", "negative", "neutral"],
        )
        sentiment = result.data["category"]  # "positive"
        confidence = result.data["confidence"]

        # Intent classification
        result = await self.capability("classify").call(
            text="I want to cancel my subscription",
            categories=["billing", "support", "cancellation", "sales"],
        )
    """

    name: ClassVar[str] = "classify"
    description: ClassVar[str] = "Classify text into categories using LLMs"
    triggers: ClassVar[list[str]] = []

    async def run(self, **config: Any) -> AsyncIterator[CapabilityEvent]:
        """Classify text into categories.

        Args:
            text: Text to classify
            categories: List of possible categories
            multi_label: Allow multiple categories (default: False)
            model: LLM model to use (default from config)

        Yields:
            CapabilityEvent with types: started, completed (with classification), failed
        """
        raise NotImplementedError(
            "Classify capability not implemented. "
            "Configure LLM API credentials to use this capability."
        )
        yield

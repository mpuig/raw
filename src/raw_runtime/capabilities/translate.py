"""Translate capability - Text translation.

Supports Google Translate, DeepL, AWS Translate, and LLM-based translation.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.capability import Capability, CapabilityEvent


class TranslateCapability(Capability):
    """Text translation capability.

    Usage:
        result = await self.capability("translate").call(
            text="Hello, how are you?",
            target_language="es",
            source_language="en",  # optional, auto-detected
        )
        translated = result.data["text"]  # "Hola, cómo estás?"
    """

    name: ClassVar[str] = "translate"
    description: ClassVar[str] = "Translate text between languages"
    triggers: ClassVar[list[str]] = []

    async def run(self, **config: Any) -> AsyncIterator[CapabilityEvent]:
        """Translate text.

        Args:
            text: Text to translate
            target_language: Target language code (e.g., "es", "fr", "de")
            source_language: Source language code (auto-detected if not provided)
            provider: Provider ("google", "deepl", "aws", "llm")

        Yields:
            CapabilityEvent with types: started, completed (with translation), failed
        """
        raise NotImplementedError(
            "Translate capability not implemented. "
            "Configure translation API credentials to use this capability."
        )
        yield

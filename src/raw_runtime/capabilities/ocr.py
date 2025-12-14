"""OCR capability - Optical character recognition.

Extract text from images and scanned documents.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.capability import Capability, CapabilityEvent


class OcrCapability(Capability):
    """OCR text extraction capability.

    Usage:
        result = await self.capability("ocr").call(
            image_path="/tmp/receipt.jpg",
            language="eng",
        )
        text = result.data["text"]
        confidence = result.data["confidence"]
    """

    name: ClassVar[str] = "ocr"
    description: ClassVar[str] = "Extract text from images (Tesseract, Google Vision)"
    triggers: ClassVar[list[str]] = []

    async def run(self, **config: Any) -> AsyncIterator[CapabilityEvent]:
        """Extract text from an image.

        Args:
            image_path: Path to image file
            image_url: URL of image (alternative to path)
            image_bytes: Raw image bytes (alternative to path)
            language: OCR language code (default: "eng")
            provider: Provider ("tesseract", "google", "aws")

        Yields:
            CapabilityEvent with types: started, completed (with text), failed
        """
        raise NotImplementedError(
            "OCR capability not implemented. "
            "Install OCR libraries or configure cloud OCR to use this capability."
        )
        yield

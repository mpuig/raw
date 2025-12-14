"""PDF capability - Generate and process PDFs.

Create PDFs from HTML/templates or extract data from existing PDFs.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.capability import Capability, CapabilityEvent


class PdfCapability(Capability):
    """PDF generation and processing capability.

    Usage:
        # Generate PDF from HTML
        result = await self.capability("pdf").call(
            action="generate",
            html="<h1>Invoice</h1><p>Total: $100</p>",
            output_path="/tmp/invoice.pdf",
        )

        # Extract text from PDF
        result = await self.capability("pdf").call(
            action="extract_text",
            input_path="/tmp/document.pdf",
        )
        text = result.data["text"]
    """

    name: ClassVar[str] = "pdf"
    description: ClassVar[str] = "PDF generation and text extraction"
    triggers: ClassVar[list[str]] = []

    async def run(self, **config: Any) -> AsyncIterator[CapabilityEvent]:
        """Generate or process PDFs.

        Args:
            action: Operation ("generate", "extract_text", "merge", "split")
            html: HTML content for generation
            template: Template name for generation
            template_data: Data for template rendering
            input_path: Path to input PDF
            output_path: Path for output PDF
            pages: Page range (for split operation)

        Yields:
            CapabilityEvent with types: started, completed, failed
        """
        raise NotImplementedError(
            "PDF capability not implemented. "
            "Install PDF processing libraries to use this capability."
        )
        yield

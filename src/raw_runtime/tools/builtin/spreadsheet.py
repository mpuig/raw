"""Spreadsheet capability - Read and write spreadsheets.

Supports Google Sheets, Excel files, and CSV.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.tools.base import Tool, ToolEvent


class SpreadsheetTool(Tool):
    """Spreadsheet operations capability.

    Usage:
        # Read from Google Sheets
        result = await self.capability("spreadsheet").call(
            action="read",
            spreadsheet_id="1abc...",
            range="Sheet1!A1:D10",
        )

        # Write to a sheet
        result = await self.capability("spreadsheet").call(
            action="write",
            spreadsheet_id="1abc...",
            range="Sheet1!A1",
            values=[["Name", "Email"], ["John", "john@example.com"]],
        )
    """

    name: ClassVar[str] = "spreadsheet"
    description: ClassVar[str] = "Read and write to spreadsheets"
    triggers: ClassVar[list[str]] = []

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        """Perform spreadsheet operations.

        Args:
            action: Operation ("read", "write", "append", "clear")
            spreadsheet_id: Google Sheets ID or file path
            range: Cell range (e.g., "Sheet1!A1:D10")
            values: Data to write (for write/append actions)
            provider: Provider ("google", "excel", "csv") - default "google"

        Yields:
            ToolEvent with types: started, completed, failed
        """
        raise NotImplementedError(
            "Spreadsheet capability not implemented. "
            "Configure Google Sheets API or file access to use this capability."
        )
        yield

"""Calendar capability - Manage calendar events.

Supports Google Calendar, Outlook Calendar, and iCal.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.tools.base import Tool, ToolEvent


class CalendarTool(Tool):
    """Calendar operations capability.

    Usage:
        # Create an event
        result = await self.capability("calendar").call(
            action="create",
            summary="Team Meeting",
            start="2024-01-15T10:00:00",
            end="2024-01-15T11:00:00",
            attendees=["alice@example.com", "bob@example.com"],
        )

        # List events
        result = await self.capability("calendar").call(
            action="list",
            start="2024-01-15",
            end="2024-01-22",
        )
    """

    name: ClassVar[str] = "calendar"
    description: ClassVar[str] = "Calendar management (Google, Outlook)"
    triggers: ClassVar[list[str]] = [
        "calendar.event.created",
        "calendar.event.updated",
        "calendar.reminder",
    ]

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        """Perform calendar operations.

        Args:
            action: Operation ("create", "update", "delete", "list", "get")
            summary: Event title
            start: Start datetime (ISO format)
            end: End datetime (ISO format)
            attendees: List of attendee emails
            calendar_id: Calendar ID (default: primary)
            provider: Provider ("google", "outlook", "ical")

        Yields:
            ToolEvent with types: started, completed, failed
        """
        raise NotImplementedError(
            "Calendar capability not implemented. "
            "Configure calendar API credentials to use this capability."
        )
        yield

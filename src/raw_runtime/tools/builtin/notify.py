"""Notify capability - Push notifications.

Send push notifications to mobile apps and browsers.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.tools.base import Tool, ToolEvent


class NotifyTool(Tool):
    """Push notification capability.

    Usage:
        result = await self.capability("notify").call(
            title="Order Shipped",
            body="Your order #12345 has been shipped!",
            user_id="user_123",
            data={"order_id": "12345", "tracking_url": "..."},
        )
    """

    name: ClassVar[str] = "notify"
    description: ClassVar[str] = "Send push notifications (Firebase, OneSignal)"
    triggers: ClassVar[list[str]] = []

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        """Send a push notification.

        Args:
            title: Notification title
            body: Notification body text
            user_id: Target user ID
            device_token: Specific device token (alternative to user_id)
            data: Custom data payload
            image_url: Optional image URL
            provider: Provider ("firebase", "onesignal", "apns")

        Yields:
            ToolEvent with types: started, completed, failed
        """
        raise NotImplementedError(
            "Notify capability not implemented. "
            "Configure push notification service to use this capability."
        )
        yield

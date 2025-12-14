"""SMS capability - Send SMS and MMS messages.

Supports Twilio, Vonage, and other SMS providers.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.capability import Capability, CapabilityEvent


class SmsCapability(Capability):
    """SMS/MMS messaging capability.

    Usage:
        result = await self.capability("sms").call(
            to="+15551234567",
            body="Your verification code is 123456",
        )
    """

    name: ClassVar[str] = "sms"
    description: ClassVar[str] = "Send SMS and MMS messages"
    triggers: ClassVar[list[str]] = ["sms.received", "sms.status.updated"]

    async def run(self, **config: Any) -> AsyncIterator[CapabilityEvent]:
        """Send an SMS message.

        Args:
            to: Recipient phone number (E.164 format)
            body: Message text
            from_number: Optional sender number (uses default if not provided)
            media_urls: Optional list of media URLs for MMS

        Yields:
            CapabilityEvent with types: started, completed, failed
        """
        raise NotImplementedError(
            "SMS capability not implemented. "
            "Configure Twilio or another SMS provider to use this capability."
        )
        yield

"""Email capability - Send and receive emails.

Supports multiple providers: SMTP, SendGrid, Mailgun, SES.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.capability import Capability, CapabilityEvent


class EmailCapability(Capability):
    """Email sending capability.

    Usage:
        result = await self.capability("email").call(
            to="user@example.com",
            subject="Hello",
            body="World",
            html="<h1>World</h1>",  # optional
        )
    """

    name: ClassVar[str] = "email"
    description: ClassVar[str] = "Send emails via SMTP or email service providers"
    triggers: ClassVar[list[str]] = []

    async def run(self, **config: Any) -> AsyncIterator[CapabilityEvent]:
        """Send an email.

        Args:
            to: Recipient email address (or list of addresses)
            subject: Email subject
            body: Plain text body
            html: Optional HTML body
            from_email: Optional sender address (uses default if not provided)
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            attachments: Optional list of attachment paths

        Yields:
            CapabilityEvent with types: started, completed, failed
        """
        raise NotImplementedError(
            "Email capability not implemented. "
            "Configure SMTP or an email provider to use this capability."
        )
        yield

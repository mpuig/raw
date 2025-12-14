"""Voice capability - Make and receive phone calls.

Supports Twilio, Vonage, and other telephony providers.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.capability import Capability, CapabilityEvent


class VoiceCapability(Capability):
    """Voice call capability.

    Usage:
        # Make an outbound call
        async for event in self.capability("voice").run(
            to="+15551234567",
            twiml="<Response><Say>Hello!</Say></Response>",
        ):
            if event.type == "completed":
                duration = event.data["duration"]

        # Or connect to an existing call
        async for event in self.capability("voice").run(
            call_sid="CA...",
            action="connect",
        ):
            ...
    """

    name: ClassVar[str] = "voice"
    description: ClassVar[str] = "Make and manage phone calls"
    triggers: ClassVar[list[str]] = [
        "twilio.call.incoming",
        "twilio.call.status",
        "voice.call.ended",
    ]

    async def run(self, **config: Any) -> AsyncIterator[CapabilityEvent]:
        """Make or manage a voice call.

        Args:
            to: Recipient phone number (for outbound calls)
            from_number: Caller ID number
            twiml: TwiML instructions for the call
            call_sid: Existing call SID (for managing calls)
            action: Action to perform ("dial", "hangup", "connect")

        Yields:
            CapabilityEvent with types: started, ringing, answered, completed, failed
        """
        raise NotImplementedError(
            "Voice capability not implemented. "
            "Configure Twilio or another telephony provider to use this capability."
        )
        yield

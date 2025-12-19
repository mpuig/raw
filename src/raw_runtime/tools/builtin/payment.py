"""Payment capability - Process payments.

Supports Stripe, PayPal, Square, and other payment processors.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.tools.base import Tool, ToolEvent


class PaymentTool(Tool):
    """Payment processing capability.

    Usage:
        # Create a payment intent
        result = await self.capability("payment").call(
            action="create_intent",
            amount=1000,  # in cents
            currency="usd",
            customer_id="cus_xxx",
        )

        # Capture a payment
        result = await self.capability("payment").call(
            action="capture",
            payment_intent_id="pi_xxx",
        )
    """

    name: ClassVar[str] = "payment"
    description: ClassVar[str] = "Payment processing (Stripe, PayPal, etc.)"
    triggers: ClassVar[list[str]] = [
        "payment.succeeded",
        "payment.failed",
        "subscription.created",
        "subscription.cancelled",
    ]

    async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
        """Process payments.

        Args:
            action: Operation ("create_intent", "capture", "refund", "create_subscription")
            amount: Amount in cents
            currency: Currency code (e.g., "usd")
            customer_id: Customer ID
            payment_intent_id: Payment intent ID (for capture/refund)
            provider: Provider ("stripe", "paypal", "square")

        Yields:
            ToolEvent with types: started, completed, failed
        """
        raise NotImplementedError(
            "Payment capability not implemented. "
            "Configure payment processor credentials to use this capability."
        )
        yield

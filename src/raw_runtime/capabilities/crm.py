"""CRM capability - Customer relationship management.

Supports Salesforce, HubSpot, Pipedrive, and other CRM systems.
"""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

from raw_runtime.capability import Capability, CapabilityEvent


class CrmCapability(Capability):
    """CRM operations capability.

    Usage:
        # Get a contact
        result = await self.capability("crm").call(
            action="get_contact",
            email="john@example.com",
        )

        # Create a lead
        result = await self.capability("crm").call(
            action="create_lead",
            data={"name": "John Doe", "email": "john@example.com"},
        )
    """

    name: ClassVar[str] = "crm"
    description: ClassVar[str] = "CRM operations (Salesforce, HubSpot, etc.)"
    triggers: ClassVar[list[str]] = [
        "crm.contact.created",
        "crm.contact.updated",
        "crm.deal.won",
        "crm.deal.lost",
    ]

    async def run(self, **config: Any) -> AsyncIterator[CapabilityEvent]:
        """Perform CRM operations.

        Args:
            action: Operation ("get_contact", "create_lead", "update_deal", etc.)
            data: Data for create/update operations
            email: Email for contact lookup
            id: Record ID for get/update operations
            provider: Provider ("salesforce", "hubspot", "pipedrive")

        Yields:
            CapabilityEvent with types: started, completed, failed
        """
        raise NotImplementedError(
            "CRM capability not implemented. Configure CRM API credentials to use this capability."
        )
        yield

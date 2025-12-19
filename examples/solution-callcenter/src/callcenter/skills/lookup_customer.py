"""Customer lookup skill.

Look up customer information by phone number or account ID. This skill
retrieves customer profile data including name, tier, order history, and
contact preferences.
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def lookup_customer(
    phone: str | None = None,
    account_id: str | None = None,
    email: str | None = None,
) -> dict[str, Any]:
    """Look up customer information by phone, account ID, or email.

    Args:
        phone: Customer phone number (E.164 format, e.g., +15551234567).
        account_id: Customer account ID (e.g., cust_123).
        email: Customer email address.

    Returns:
        Customer information including:
        - id: Customer account ID
        - name: Customer name
        - email: Email address
        - phone: Phone number
        - tier: Customer tier (standard, premium, vip)
        - account_created: Account creation date
        - total_orders: Total number of orders
        - lifetime_value: Total amount spent
        - last_order_date: Date of most recent order
        - notes: Any special notes about the customer

    Why: Provides context about the customer to personalize the conversation
    and access relevant account information.
    """
    logger.info("Looking up customer", extra={"phone": phone, "account_id": account_id})

    # In production, this would query your CRM/database
    # For this example, we return mock data

    if not phone and not account_id and not email:
        return {
            "success": False,
            "error": "customer_not_found",
            "message": "Please provide phone number, account ID, or email address.",
        }

    # Mock customer data
    mock_customers = {
        "+15551234567": {
            "id": "cust_001",
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+15551234567",
            "tier": "premium",
            "account_created": "2023-01-15",
            "total_orders": 12,
            "lifetime_value": 2450.00,
            "last_order_date": "2024-12-10",
            "notes": "Prefers email communication",
        },
        "+15559876543": {
            "id": "cust_002",
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "phone": "+15559876543",
            "tier": "vip",
            "account_created": "2022-06-20",
            "total_orders": 45,
            "lifetime_value": 12300.00,
            "last_order_date": "2024-12-18",
            "notes": "VIP customer - expedite all requests",
        },
        "cust_001": {
            "id": "cust_001",
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+15551234567",
            "tier": "premium",
            "account_created": "2023-01-15",
            "total_orders": 12,
            "lifetime_value": 2450.00,
            "last_order_date": "2024-12-10",
            "notes": "Prefers email communication",
        },
    }

    # Try to find customer
    search_key = phone or account_id or email
    customer = mock_customers.get(search_key)

    if not customer:
        # In production, you might try fuzzy matching or ask for more info
        logger.warning("Customer not found", extra={"search_key": search_key})
        return {
            "success": False,
            "error": "customer_not_found",
            "message": "No customer found with that information.",
        }

    logger.info("Customer found", extra={"customer_id": customer["id"]})

    return {
        "success": True,
        **customer,
    }


# JSON schema for the tool (used by LLM)
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_customer",
        "description": (
            "Look up customer information by phone number, account ID, or email. "
            "Use this at the start of a call to retrieve customer context. "
            "Returns customer profile including tier, order history, and preferences."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "phone": {
                    "type": "string",
                    "description": (
                        "Customer phone number in E.164 format (e.g., +15551234567). "
                        "Include country code."
                    ),
                },
                "account_id": {
                    "type": "string",
                    "description": "Customer account ID (e.g., cust_123)",
                },
                "email": {
                    "type": "string",
                    "description": "Customer email address",
                },
            },
            # At least one parameter required, but make them all optional
            # so the LLM can choose which one to use
        },
    },
}


# Mock database interface (replace with real implementation)
class CustomerDatabase:
    """Mock customer database interface.

    Why: Abstracts database operations to make testing easier and allow
    swapping implementations (SQL, NoSQL, CRM API, etc.).
    """

    async def find_by_phone(self, phone: str) -> dict[str, Any] | None:
        """Find customer by phone number."""
        # In production: SELECT * FROM customers WHERE phone = ?
        return None

    async def find_by_account_id(self, account_id: str) -> dict[str, Any] | None:
        """Find customer by account ID."""
        # In production: SELECT * FROM customers WHERE id = ?
        return None

    async def find_by_email(self, email: str) -> dict[str, Any] | None:
        """Find customer by email."""
        # In production: SELECT * FROM customers WHERE email = ?
        return None

    async def update_last_contact(self, customer_id: str) -> None:
        """Update customer's last contact timestamp."""
        # In production: UPDATE customers SET last_contact = NOW() WHERE id = ?
        pass


# Production version with async database calls
async def lookup_customer_async(
    db: CustomerDatabase,
    phone: str | None = None,
    account_id: str | None = None,
    email: str | None = None,
) -> dict[str, Any]:
    """Production version with async database access.

    Args:
        db: Database instance
        phone: Customer phone number
        account_id: Customer account ID
        email: Customer email

    Returns:
        Customer information or error.

    Why: Separates business logic from I/O to enable testing and proper
    async handling in production.
    """
    if not phone and not account_id and not email:
        return {
            "success": False,
            "error": "customer_not_found",
            "message": "Please provide phone number, account ID, or email address.",
        }

    # Try different lookup methods
    customer = None
    if phone:
        customer = await db.find_by_phone(phone)
    elif account_id:
        customer = await db.find_by_account_id(account_id)
    elif email:
        customer = await db.find_by_email(email)

    if not customer:
        return {
            "success": False,
            "error": "customer_not_found",
            "message": "No customer found with that information.",
        }

    # Update last contact timestamp
    await db.update_last_contact(customer["id"])

    return {
        "success": True,
        **customer,
    }

"""Order status checking skill.

Check the status of customer orders including shipping information,
tracking numbers, and estimated delivery dates.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def check_order_status(order_id: str) -> dict[str, Any]:
    """Check the status of a customer order.

    Args:
        order_id: Order ID to look up (e.g., ORD-12345).

    Returns:
        Order information including:
        - order_id: Order ID
        - status: Order status (processing, shipped, delivered, cancelled)
        - order_date: Date order was placed
        - items: List of items in the order
        - total_amount: Total order amount
        - tracking_number: Shipping tracking number (if shipped)
        - carrier: Shipping carrier name
        - estimated_delivery: Estimated delivery date
        - actual_delivery: Actual delivery date (if delivered)

    Why: Provides real-time order information to answer customer questions
    about their purchases.
    """
    logger.info("Checking order status", extra={"order_id": order_id})

    if not order_id:
        return {
            "success": False,
            "error": "invalid_order_id",
            "message": "Please provide a valid order ID.",
        }

    # In production, this would query your order management system
    # For this example, we return mock data

    # Mock order data
    mock_orders = {
        "ORD-12345": {
            "order_id": "ORD-12345",
            "status": "shipped",
            "order_date": "2024-12-15",
            "items": [
                {"name": "Wireless Headphones", "quantity": 1, "price": 79.99},
                {"name": "USB-C Cable", "quantity": 2, "price": 12.99},
            ],
            "total_amount": 105.97,
            "tracking_number": "1Z999AA10123456784",
            "carrier": "UPS",
            "estimated_delivery": "2024-12-20",
            "shipping_address": {
                "street": "123 Main St",
                "city": "New York",
                "state": "NY",
                "zip": "10001",
            },
        },
        "ORD-67890": {
            "order_id": "ORD-67890",
            "status": "processing",
            "order_date": "2024-12-18",
            "items": [
                {"name": "Smart Watch", "quantity": 1, "price": 299.99},
            ],
            "total_amount": 299.99,
            "estimated_ship_date": "2024-12-19",
        },
        "ORD-11111": {
            "order_id": "ORD-11111",
            "status": "delivered",
            "order_date": "2024-12-10",
            "items": [
                {"name": "Laptop Stand", "quantity": 1, "price": 49.99},
            ],
            "total_amount": 49.99,
            "tracking_number": "1Z999AA10987654321",
            "carrier": "UPS",
            "estimated_delivery": "2024-12-13",
            "actual_delivery": "2024-12-12",
        },
    }

    order = mock_orders.get(order_id)

    if not order:
        logger.warning("Order not found", extra={"order_id": order_id})
        return {
            "success": False,
            "error": "order_not_found",
            "message": f"No order found with ID {order_id}.",
        }

    logger.info("Order found", extra={"order_id": order_id, "status": order["status"]})

    return {
        "success": True,
        **order,
    }


# JSON schema for the tool (used by LLM)
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "check_order_status",
        "description": (
            "Check the status of a customer order by order ID. "
            "Returns order details including status, items, tracking information, "
            "and estimated delivery date. Use this when customers ask about their orders."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": (
                        "Order ID to look up (e.g., ORD-12345). "
                        "This is typically provided by the customer or found in their order history."
                    ),
                },
            },
            "required": ["order_id"],
        },
    },
}


# Mock database interface
class OrderDatabase:
    """Mock order database interface.

    Why: Abstracts database operations to make testing easier and allow
    swapping implementations.
    """

    async def find_by_id(self, order_id: str) -> dict[str, Any] | None:
        """Find order by order ID."""
        # In production: SELECT * FROM orders WHERE id = ?
        return None

    async def find_by_customer(self, customer_id: str) -> list[dict[str, Any]]:
        """Find all orders for a customer."""
        # In production: SELECT * FROM orders WHERE customer_id = ? ORDER BY order_date DESC
        return []

    async def get_tracking_info(self, order_id: str) -> dict[str, Any] | None:
        """Get tracking information for an order."""
        # In production: Query shipping carrier API
        return None


# Production version with async database calls
async def check_order_status_async(
    db: OrderDatabase,
    order_id: str,
    fetch_live_tracking: bool = False,
) -> dict[str, Any]:
    """Production version with async database access.

    Args:
        db: Database instance
        order_id: Order ID to look up
        fetch_live_tracking: Whether to fetch live tracking from carrier API

    Returns:
        Order information or error.

    Why: Separates business logic from I/O to enable testing and proper
    async handling in production. Option to fetch live tracking for
    real-time updates.
    """
    if not order_id:
        return {
            "success": False,
            "error": "invalid_order_id",
            "message": "Please provide a valid order ID.",
        }

    # Look up order
    order = await db.find_by_id(order_id)

    if not order:
        return {
            "success": False,
            "error": "order_not_found",
            "message": f"No order found with ID {order_id}.",
        }

    # Optionally fetch live tracking information
    if fetch_live_tracking and order.get("tracking_number"):
        tracking_info = await db.get_tracking_info(order_id)
        if tracking_info:
            order.update(tracking_info)

    return {
        "success": True,
        **order,
    }


def get_recent_orders_for_customer(customer_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Get recent orders for a customer.

    Args:
        customer_id: Customer account ID
        limit: Maximum number of orders to return

    Returns:
        List of recent orders

    Why: Useful for proactive support - agent can see recent orders
    without customer providing order ID.
    """
    # Mock data
    mock_orders = {
        "cust_001": [
            {
                "order_id": "ORD-12345",
                "order_date": "2024-12-15",
                "total_amount": 105.97,
                "status": "shipped",
            },
            {
                "order_id": "ORD-11234",
                "order_date": "2024-11-20",
                "total_amount": 45.00,
                "status": "delivered",
            },
        ],
        "cust_002": [
            {
                "order_id": "ORD-67890",
                "order_date": "2024-12-18",
                "total_amount": 299.99,
                "status": "processing",
            },
        ],
    }

    orders = mock_orders.get(customer_id, [])
    return orders[:limit]

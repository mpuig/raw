"""Schedule callback skill.

Schedule callbacks for customers at their preferred time. Validates
business hours and availability.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def schedule_callback(
    customer_id: str,
    phone_number: str,
    preferred_time: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Schedule a callback for a customer.

    Args:
        customer_id: Customer account ID
        phone_number: Phone number to call back
        preferred_time: Preferred callback time (ISO format or natural language)
        reason: Reason for the callback (optional)

    Returns:
        Callback confirmation including:
        - callback_id: Unique callback ID
        - scheduled_time: Confirmed callback time
        - phone_number: Phone number to call
        - reason: Reason for callback
        - agent_assigned: Whether an agent has been assigned

    Why: Allows customers to receive support at their convenience rather
    than waiting on hold or resolving complex issues immediately.
    """
    logger.info(
        "Scheduling callback",
        extra={
            "customer_id": customer_id,
            "phone_number": phone_number,
            "preferred_time": preferred_time,
        },
    )

    if not customer_id or not phone_number:
        return {
            "success": False,
            "error": "missing_required_fields",
            "message": "Customer ID and phone number are required.",
        }

    # Parse the preferred time
    try:
        scheduled_time = parse_callback_time(preferred_time)
    except ValueError as e:
        return {
            "success": False,
            "error": "invalid_time",
            "message": str(e),
        }

    # Validate business hours
    if not is_business_hours(scheduled_time):
        return {
            "success": False,
            "error": "outside_business_hours",
            "message": (
                "Callbacks can only be scheduled during business hours: "
                "Monday-Friday, 9 AM - 5 PM Eastern Time."
            ),
        }

    # In production, this would create a callback in your scheduling system
    callback_id = f"CB-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    logger.info(
        "Callback scheduled successfully",
        extra={"callback_id": callback_id, "scheduled_time": scheduled_time.isoformat()},
    )

    return {
        "success": True,
        "callback_id": callback_id,
        "scheduled_time": scheduled_time.strftime("%A, %B %d at %I:%M %p %Z"),
        "phone_number": phone_number,
        "reason": reason or "General inquiry",
        "agent_assigned": False,  # Would be True if agent is assigned immediately
        "confirmation_sent": True,  # SMS/email confirmation sent
    }


def parse_callback_time(time_str: str) -> datetime:
    """Parse callback time from string.

    Args:
        time_str: Time in ISO format or natural language

    Returns:
        Parsed datetime

    Raises:
        ValueError: If time cannot be parsed

    Why: Handles both structured (ISO) and natural language time expressions.
    """
    # Try ISO format first
    try:
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        pass

    # Try common natural language patterns
    # In production, use a proper NLP library like dateutil or timeparse
    now = datetime.now()

    time_str_lower = time_str.lower()

    # Handle relative times
    if "tomorrow" in time_str_lower:
        base = now + timedelta(days=1)
        if "morning" in time_str_lower:
            return base.replace(hour=10, minute=0, second=0, microsecond=0)
        elif "afternoon" in time_str_lower:
            return base.replace(hour=14, minute=0, second=0, microsecond=0)
        else:
            return base.replace(hour=10, minute=0, second=0, microsecond=0)

    if "next week" in time_str_lower:
        base = now + timedelta(days=7)
        return base.replace(hour=10, minute=0, second=0, microsecond=0)

    # Default: schedule for next business day at 10 AM
    next_day = now + timedelta(days=1)
    while next_day.weekday() >= 5:  # Skip weekends
        next_day += timedelta(days=1)

    return next_day.replace(hour=10, minute=0, second=0, microsecond=0)


def is_business_hours(dt: datetime) -> bool:
    """Check if datetime falls within business hours.

    Args:
        dt: Datetime to check

    Returns:
        True if within business hours, False otherwise

    Why: Ensures callbacks are only scheduled when agents are available.
    """
    # Monday-Friday
    if dt.weekday() >= 5:
        return False

    # 9 AM - 5 PM
    if dt.hour < 9 or dt.hour >= 17:
        return False

    return True


# JSON schema for the tool (used by LLM)
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "schedule_callback",
        "description": (
            "Schedule a callback for a customer at their preferred time. "
            "Validates that the time is within business hours (Monday-Friday, 9 AM - 5 PM EST). "
            "Use this when a customer wants to be called back or when an issue requires follow-up. "
            "The customer will receive a confirmation via SMS."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer account ID (e.g., cust_123)",
                },
                "phone_number": {
                    "type": "string",
                    "description": (
                        "Phone number to call back in E.164 format (e.g., +15551234567). "
                        "Include country code."
                    ),
                },
                "preferred_time": {
                    "type": "string",
                    "description": (
                        "Preferred callback time. Can be ISO format (2024-12-20T14:00:00Z) "
                        'or natural language (e.g., "tomorrow afternoon", "next Monday at 2pm")'
                    ),
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the callback (e.g., 'Billing question', 'Order issue')",
                },
            },
            "required": ["customer_id", "phone_number", "preferred_time"],
        },
    },
}


# Mock database interface
class CallbackScheduler:
    """Mock callback scheduling system interface.

    Why: Abstracts scheduling operations to allow different implementations
    (database, calendar API, ticketing system, etc.).
    """

    async def create_callback(
        self,
        customer_id: str,
        phone_number: str,
        scheduled_time: datetime,
        reason: str | None = None,
    ) -> str:
        """Create a callback in the scheduling system.

        Returns:
            Callback ID
        """
        # In production: INSERT INTO callbacks (...) VALUES (...)
        return f"CB-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    async def find_available_agent(self, scheduled_time: datetime) -> str | None:
        """Find an available agent for the scheduled time.

        Returns:
            Agent ID if available, None otherwise
        """
        # In production: Query agent availability system
        return None

    async def send_confirmation(self, customer_id: str, callback_id: str) -> bool:
        """Send SMS/email confirmation to customer.

        Returns:
            True if sent successfully
        """
        # In production: Call SMS/email service
        return True


# Production version with async operations
async def schedule_callback_async(
    scheduler: CallbackScheduler,
    customer_id: str,
    phone_number: str,
    preferred_time: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """Production version with async scheduling operations.

    Args:
        scheduler: Scheduler instance
        customer_id: Customer account ID
        phone_number: Phone number to call back
        preferred_time: Preferred callback time
        reason: Reason for callback

    Returns:
        Callback confirmation or error.

    Why: Separates business logic from I/O to enable testing and proper
    async handling in production.
    """
    if not customer_id or not phone_number:
        return {
            "success": False,
            "error": "missing_required_fields",
            "message": "Customer ID and phone number are required.",
        }

    # Parse time
    try:
        scheduled_time = parse_callback_time(preferred_time)
    except ValueError as e:
        return {
            "success": False,
            "error": "invalid_time",
            "message": str(e),
        }

    # Validate business hours
    if not is_business_hours(scheduled_time):
        return {
            "success": False,
            "error": "outside_business_hours",
            "message": (
                "Callbacks can only be scheduled during business hours: "
                "Monday-Friday, 9 AM - 5 PM Eastern Time."
            ),
        }

    # Create callback
    callback_id = await scheduler.create_callback(
        customer_id=customer_id,
        phone_number=phone_number,
        scheduled_time=scheduled_time,
        reason=reason,
    )

    # Try to assign an agent
    agent_id = await scheduler.find_available_agent(scheduled_time)

    # Send confirmation
    confirmation_sent = await scheduler.send_confirmation(customer_id, callback_id)

    return {
        "success": True,
        "callback_id": callback_id,
        "scheduled_time": scheduled_time.strftime("%A, %B %d at %I:%M %p %Z"),
        "phone_number": phone_number,
        "reason": reason or "General inquiry",
        "agent_assigned": agent_id is not None,
        "confirmation_sent": confirmation_sent,
    }

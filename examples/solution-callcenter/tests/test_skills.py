"""Tests for call center skills.

Demonstrates how to test skills in isolation with mock data.
"""

import pytest

from callcenter.skills.check_order_status import check_order_status
from callcenter.skills.lookup_customer import lookup_customer
from callcenter.skills.schedule_callback import (
    is_business_hours,
    parse_callback_time,
    schedule_callback,
)


class TestLookupCustomer:
    """Tests for customer lookup skill."""

    def test_lookup_by_phone_success(self):
        """Test successful customer lookup by phone number."""
        result = lookup_customer(phone="+15551234567")

        assert result["success"] is True
        assert result["id"] == "cust_001"
        assert result["name"] == "John Doe"
        assert result["tier"] == "premium"

    def test_lookup_by_account_id_success(self):
        """Test successful customer lookup by account ID."""
        result = lookup_customer(account_id="cust_001")

        assert result["success"] is True
        assert result["id"] == "cust_001"
        assert result["name"] == "John Doe"

    def test_lookup_not_found(self):
        """Test customer lookup when customer not found."""
        result = lookup_customer(phone="+15559999999")

        assert result["success"] is False
        assert result["error"] == "customer_not_found"

    def test_lookup_no_identifier(self):
        """Test customer lookup with no identifier provided."""
        result = lookup_customer()

        assert result["success"] is False
        assert result["error"] == "customer_not_found"


class TestCheckOrderStatus:
    """Tests for order status checking skill."""

    def test_check_order_shipped(self):
        """Test checking status of shipped order."""
        result = check_order_status(order_id="ORD-12345")

        assert result["success"] is True
        assert result["status"] == "shipped"
        assert result["tracking_number"] == "1Z999AA10123456784"
        assert result["carrier"] == "UPS"

    def test_check_order_processing(self):
        """Test checking status of processing order."""
        result = check_order_status(order_id="ORD-67890")

        assert result["success"] is True
        assert result["status"] == "processing"
        assert "estimated_ship_date" in result

    def test_check_order_delivered(self):
        """Test checking status of delivered order."""
        result = check_order_status(order_id="ORD-11111")

        assert result["success"] is True
        assert result["status"] == "delivered"
        assert "actual_delivery" in result

    def test_check_order_not_found(self):
        """Test checking status of non-existent order."""
        result = check_order_status(order_id="ORD-99999")

        assert result["success"] is False
        assert result["error"] == "order_not_found"

    def test_check_order_no_id(self):
        """Test checking order with no ID provided."""
        result = check_order_status(order_id="")

        assert result["success"] is False
        assert result["error"] == "invalid_order_id"


class TestScheduleCallback:
    """Tests for callback scheduling skill."""

    def test_schedule_callback_success(self):
        """Test successful callback scheduling."""
        result = schedule_callback(
            customer_id="cust_001",
            phone_number="+15551234567",
            preferred_time="tomorrow afternoon",
            reason="Billing question",
        )

        assert result["success"] is True
        assert "callback_id" in result
        assert result["phone_number"] == "+15551234567"
        assert result["reason"] == "Billing question"

    def test_schedule_callback_missing_fields(self):
        """Test callback scheduling with missing required fields."""
        result = schedule_callback(
            customer_id="",
            phone_number="",
            preferred_time="tomorrow",
        )

        assert result["success"] is False
        assert result["error"] == "missing_required_fields"

    def test_parse_callback_time_tomorrow(self):
        """Test parsing 'tomorrow' as callback time."""
        from datetime import datetime, timedelta

        result = parse_callback_time("tomorrow morning")
        expected = (datetime.now() + timedelta(days=1)).date()

        assert result.date() == expected
        assert result.hour == 10  # Morning

    def test_is_business_hours_weekday(self):
        """Test business hours check for weekday."""
        from datetime import datetime

        # Monday at 2 PM
        dt = datetime(2024, 12, 23, 14, 0)  # Monday
        assert is_business_hours(dt) is True

    def test_is_business_hours_weekend(self):
        """Test business hours check for weekend."""
        from datetime import datetime

        # Saturday at 2 PM
        dt = datetime(2024, 12, 21, 14, 0)  # Saturday
        assert is_business_hours(dt) is False

    def test_is_business_hours_outside_hours(self):
        """Test business hours check outside working hours."""
        from datetime import datetime

        # Monday at 8 PM
        dt = datetime(2024, 12, 23, 20, 0)
        assert is_business_hours(dt) is False


# Integration test example
class TestSkillIntegration:
    """Integration tests for skill interactions."""

    def test_lookup_then_check_order(self):
        """Test workflow: lookup customer, then check their order."""
        # Step 1: Lookup customer
        customer = lookup_customer(phone="+15551234567")
        assert customer["success"] is True

        # Step 2: Check their recent order (would get from customer data)
        order = check_order_status(order_id="ORD-12345")
        assert order["success"] is True
        assert order["status"] == "shipped"

    def test_lookup_then_schedule_callback(self):
        """Test workflow: lookup customer, then schedule callback."""
        # Step 1: Lookup customer
        customer = lookup_customer(phone="+15551234567")
        assert customer["success"] is True

        # Step 2: Schedule callback
        callback = schedule_callback(
            customer_id=customer["id"],
            phone_number=customer["phone"],
            preferred_time="tomorrow afternoon",
            reason="Follow-up on order",
        )
        assert callback["success"] is True


# Fixtures for async tests
@pytest.fixture
async def mock_db():
    """Mock database for testing async functions."""

    class MockDB:
        async def find_by_phone(self, phone):
            if phone == "+15551234567":
                return {
                    "id": "cust_001",
                    "name": "John Doe",
                    "phone": phone,
                }
            return None

    return MockDB()


# Example async test (uncomment when testing async versions)
# @pytest.mark.asyncio
# async def test_lookup_customer_async(mock_db):
#     """Test async customer lookup."""
#     from callcenter.skills.lookup_customer import lookup_customer_async
#
#     result = await lookup_customer_async(mock_db, phone="+15551234567")
#     assert result["success"] is True
#     assert result["name"] == "John Doe"


if __name__ == "__main__":
    # Run tests with: pytest tests/test_skills.py -v
    pytest.main([__file__, "-v"])

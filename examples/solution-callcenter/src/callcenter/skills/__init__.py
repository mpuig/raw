"""Skills for the call center AI agent.

Skills are tools that the agent can use during conversations. Each skill
is a Python function with a JSON schema that the LLM uses to determine
when and how to call it.
"""

from callcenter.skills.check_order_status import (
    TOOL_SCHEMA as CHECK_ORDER_STATUS_SCHEMA,
)
from callcenter.skills.check_order_status import check_order_status
from callcenter.skills.lookup_customer import TOOL_SCHEMA as LOOKUP_CUSTOMER_SCHEMA
from callcenter.skills.lookup_customer import lookup_customer
from callcenter.skills.schedule_callback import (
    TOOL_SCHEMA as SCHEDULE_CALLBACK_SCHEMA,
)
from callcenter.skills.schedule_callback import schedule_callback

# Registry of all available tools
TOOLS_REGISTRY = {
    "lookup_customer": lookup_customer,
    "check_order_status": check_order_status,
    "schedule_callback": schedule_callback,
}

# List of tool schemas for LLM
TOOLS_SCHEMA = [
    LOOKUP_CUSTOMER_SCHEMA,
    CHECK_ORDER_STATUS_SCHEMA,
    SCHEDULE_CALLBACK_SCHEMA,
]

__all__ = [
    "TOOLS_REGISTRY",
    "TOOLS_SCHEMA",
    "lookup_customer",
    "check_order_status",
    "schedule_callback",
]

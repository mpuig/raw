#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "anthropic>=0.40.0"]
# ///
"""Example: Using @agentic for edge case classification.

This shows Layer 2 of agent-native architecture - selective agent-in-loop.
Most steps are deterministic (fast, free, predictable), but classification
uses LLM reasoning (costs money, adds intelligence).

This pattern is cost-effective:
- Deterministic steps: $0 cost
- One agentic step: ~$0.001 per execution
- Total: Predictable, minimal cost

The workflow demonstrates:
1. Fetching data (deterministic)
2. Classifying with LLM reasoning (agentic)
3. Routing based on classification (deterministic)

Usage:
    python examples/edge_case_handler.py --ticket-id TKT-12345
"""

from typing import Literal

from pydantic import BaseModel, Field

from raw_runtime import BaseWorkflow, agentic
from raw_runtime import raw_step as step


class Params(BaseModel):
    """CLI parameters."""

    ticket_id: str = Field(..., description="Support ticket ID")


class EdgeCaseHandler(BaseWorkflow[Params]):
    """Workflow that uses LLM for classification decision.

    This demonstrates the agent-native pattern: use deterministic code
    where possible, invoke LLM only for nuanced reasoning.
    """

    @step("fetch_ticket")
    def fetch_ticket(self) -> dict:
        """Fetch ticket data from database.

        Deterministic step - no LLM needed, just data retrieval.
        Cost: $0
        """
        # In production, this would query a real database
        # For demo, we simulate a ticket
        ticket = {
            "id": self.params.ticket_id,
            "customer": "Enterprise Corp",
            "customer_tier": "enterprise",
            "issue": "Database connection timeouts in production environment",
            "description": (
                "Our production app is experiencing intermittent database timeouts. "
                "This started after the system upgrade last week. "
                "Error rate is ~15% of requests. "
                "Affects critical customer-facing features."
            ),
            "history": [
                "Similar timeout 3 months ago, resolved by indexing",
                "System upgraded 1 week ago",
                "Customer escalated issue 2 hours ago",
            ],
            "reported_at": "2024-01-10T14:30:00Z",
        }

        self.log(f"Fetched ticket: {ticket['id']}")
        self.log(f"Customer: {ticket['customer']} ({ticket['customer_tier']})")
        self.log(f"Issue: {ticket['issue']}")

        return ticket

    @step("classify_urgency")
    @agentic(
        prompt="""
Classify the urgency of this support ticket based on the information below.

Customer: {context.customer} (tier: {context.customer_tier})
Issue: {context.issue}
Description: {context.description}
History: {context.history}

Consider:
- Production issues are critical (affects live systems)
- Enterprise customers get higher priority
- Recent system changes increase risk
- Customer escalation indicates high impact

Return ONLY one word: critical, high, medium, or low
""",
        model="claude-3-5-haiku-20241022",  # Cheapest model for simple classification
        max_tokens=10,  # Minimal tokens needed (one word)
        cost_limit=0.01,  # Safety limit: ~10x expected cost
    )
    def classify_urgency(
        self,
        customer: str,
        customer_tier: str,
        issue: str,
        description: str,
        history: list,
    ) -> Literal["critical", "high", "medium", "low"]:
        """Classify ticket urgency using LLM reasoning.

        This is an agentic step - the LLM uses reasoning to classify
        based on nuanced factors that would be hard to encode in rules.

        Cost: ~$0.001 per call
        Time: ~1-2 seconds
        """
        pass  # Implementation injected by @agentic decorator

    @step("route")
    def route_ticket(self, urgency: str, ticket: dict) -> dict:
        """Route ticket based on classification.

        Deterministic step - simple mapping logic, no LLM needed.
        Cost: $0
        """
        # Routing rules based on urgency
        routing_table = {
            "critical": {
                "assignee": "on-call-engineer",
                "sla": "1 hour",
                "escalate": True,
                "notify": ["ops-team@company.com", "cto@company.com"],
            },
            "high": {
                "assignee": "senior-support",
                "sla": "4 hours",
                "escalate": False,
                "notify": ["support-team@company.com"],
            },
            "medium": {
                "assignee": "support-queue",
                "sla": "24 hours",
                "escalate": False,
                "notify": ["support-team@company.com"],
            },
            "low": {
                "assignee": "support-queue",
                "sla": "48 hours",
                "escalate": False,
                "notify": [],
            },
        }

        routing = routing_table[urgency]
        result = {
            "ticket_id": ticket["id"],
            "urgency": urgency,
            "assignee": routing["assignee"],
            "sla": routing["sla"],
            "escalate": routing["escalate"],
            "notify": routing["notify"],
        }

        self.log("Routing decision:")
        self.log(f"  Urgency: {urgency}")
        self.log(f"  Assigned to: {result['assignee']}")
        self.log(f"  SLA: {result['sla']}")

        return result

    def run(self) -> int:
        """Execute the workflow.

        Pattern:
        1. Fetch data (deterministic, free)
        2. Classify with LLM (agentic, ~$0.001)
        3. Route based on result (deterministic, free)

        Total cost: ~$0.001 per execution
        """
        # Step 1: Fetch ticket data (deterministic)
        ticket = self.fetch_ticket()

        # Step 2: Use LLM to classify urgency (agentic - only step that costs money)
        urgency = self.classify_urgency(
            customer=ticket["customer"],
            customer_tier=ticket["customer_tier"],
            issue=ticket["issue"],
            description=ticket["description"],
            history=ticket["history"],
        )

        # Step 3: Route based on classification (deterministic)
        routing = self.route_ticket(urgency, ticket)

        # Save result
        self.save("routing.json", routing)

        # Show cost breakdown
        if self.context:
            total_cost = sum(
                step_data.get("cost", 0)
                for step_data in self.context._steps.values()
                if "cost" in step_data
            )
            self.log(f"\nTotal agentic cost: ${total_cost:.4f}")
            self.log("(Deterministic steps are free - only the classify_urgency step costs money)")

        return 0


if __name__ == "__main__":
    EdgeCaseHandler.main()

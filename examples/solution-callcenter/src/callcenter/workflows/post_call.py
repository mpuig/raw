"""Post-call workflow for call center automation.

Automatically processes completed calls to:
1. Generate conversation summary
2. Update CRM with call details
3. Send follow-up emails if needed
4. Create support tickets for unresolved issues
5. Log metrics for analytics
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class PostCallWorkflow:
    """Post-call automation workflow.

    Why: Automates tedious post-call tasks that would otherwise be done
    manually by agents, ensuring consistency and saving time.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize workflow with configuration.

        Args:
            config: Workflow configuration from CallCenterConfig
        """
        self.config = config
        self.enabled = config.get("enabled", True)
        self.summarize = config.get("summarize", True)
        self.update_crm = config.get("update_crm", True)
        self.send_email = config.get("send_email", False)
        self.create_ticket_threshold = config.get("create_ticket_threshold", 0.6)

    async def run(self, call_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the post-call workflow.

        Args:
            call_data: Call information including:
                - call_sid: Twilio call SID
                - customer_id: Customer account ID
                - transcript: Conversation transcript
                - duration: Call duration in seconds
                - outcome: Call outcome (resolved, escalated, etc.)
                - sentiment: Customer sentiment score (0-1)

        Returns:
            Workflow results including:
                - summary: Generated summary
                - crm_updated: Whether CRM was updated
                - email_sent: Whether follow-up email was sent
                - ticket_created: Whether support ticket was created
                - metrics_logged: Whether metrics were logged

        Why: Centralizes all post-call automation in a single workflow
        that can be tested and modified independently.
        """
        if not self.enabled:
            logger.info("Post-call workflow disabled")
            return {"enabled": False}

        logger.info(
            "Starting post-call workflow",
            extra={
                "call_sid": call_data.get("call_sid"),
                "customer_id": call_data.get("customer_id"),
            },
        )

        results = {
            "call_sid": call_data.get("call_sid"),
            "started_at": datetime.now().isoformat(),
        }

        # Step 1: Generate summary
        if self.summarize:
            summary = await self._generate_summary(call_data)
            results["summary"] = summary
            results["summary_generated"] = True
        else:
            results["summary_generated"] = False

        # Step 2: Update CRM
        if self.update_crm:
            crm_result = await self._update_crm(call_data, results.get("summary"))
            results["crm_updated"] = crm_result.get("success", False)
            results["crm_activity_id"] = crm_result.get("activity_id")
        else:
            results["crm_updated"] = False

        # Step 3: Send follow-up email (if enabled and needed)
        if self.send_email and self._should_send_email(call_data):
            email_result = await self._send_follow_up_email(call_data, results.get("summary"))
            results["email_sent"] = email_result.get("success", False)
        else:
            results["email_sent"] = False

        # Step 4: Create support ticket if sentiment is low
        sentiment = call_data.get("sentiment", 1.0)
        if sentiment < self.create_ticket_threshold:
            ticket_result = await self._create_support_ticket(call_data, results.get("summary"))
            results["ticket_created"] = ticket_result.get("success", False)
            results["ticket_id"] = ticket_result.get("ticket_id")
        else:
            results["ticket_created"] = False

        # Step 5: Log metrics
        metrics_result = await self._log_metrics(call_data)
        results["metrics_logged"] = metrics_result.get("success", False)

        results["completed_at"] = datetime.now().isoformat()
        logger.info("Post-call workflow completed", extra=results)

        return results

    async def _generate_summary(self, call_data: dict[str, Any]) -> str:
        """Generate a summary of the conversation.

        Args:
            call_data: Call information

        Returns:
            Generated summary

        Why: Provides agents and managers with quick overview of calls
        without reading full transcripts.
        """
        transcript = call_data.get("transcript", [])

        if not transcript:
            return "No transcript available."

        # In production, use LLM to generate intelligent summary
        # For this example, we create a simple summary

        summary_lines = [
            "Call Summary:",
            f"- Duration: {call_data.get('duration', 0)} seconds",
            f"- Outcome: {call_data.get('outcome', 'unknown')}",
            f"- Customer satisfaction: {call_data.get('sentiment', 0.5) * 100:.0f}%",
        ]

        # Extract key topics (in production, use NLP)
        topics = call_data.get("topics", [])
        if topics:
            summary_lines.append(f"- Topics discussed: {', '.join(topics)}")

        # Extract tools used
        tools_used = call_data.get("tools_used", [])
        if tools_used:
            summary_lines.append(f"- Actions taken: {', '.join(tools_used)}")

        return "\n".join(summary_lines)

    async def _update_crm(
        self, call_data: dict[str, Any], summary: str | None
    ) -> dict[str, Any]:
        """Update CRM with call details.

        Args:
            call_data: Call information
            summary: Generated summary

        Returns:
            CRM update result

        Why: Ensures customer interaction history is tracked in central system.
        """
        customer_id = call_data.get("customer_id")

        if not customer_id:
            logger.warning("No customer ID, skipping CRM update")
            return {"success": False, "reason": "no_customer_id"}

        # In production, call your CRM API (Salesforce, HubSpot, etc.)
        activity_data = {
            "type": "call",
            "date": datetime.now().isoformat(),
            "duration": call_data.get("duration"),
            "outcome": call_data.get("outcome"),
            "summary": summary,
            "sentiment": call_data.get("sentiment"),
            "call_sid": call_data.get("call_sid"),
        }

        logger.info(
            "Updating CRM",
            extra={"customer_id": customer_id, "activity_data": activity_data},
        )

        # Mock CRM update
        activity_id = f"ACT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return {
            "success": True,
            "activity_id": activity_id,
        }

    def _should_send_email(self, call_data: dict[str, Any]) -> bool:
        """Determine if follow-up email should be sent.

        Args:
            call_data: Call information

        Returns:
            True if email should be sent

        Why: Only send emails when appropriate (e.g., action items,
        unresolved issues, customer requested).
        """
        # Send email if:
        # 1. Customer requested it
        # 2. Call outcome requires follow-up
        # 3. There are action items

        outcome = call_data.get("outcome", "")
        action_items = call_data.get("action_items", [])

        return (
            outcome in ["follow_up_needed", "escalated", "pending"]
            or len(action_items) > 0
            or call_data.get("email_requested", False)
        )

    async def _send_follow_up_email(
        self, call_data: dict[str, Any], summary: str | None
    ) -> dict[str, Any]:
        """Send follow-up email to customer.

        Args:
            call_data: Call information
            summary: Generated summary

        Returns:
            Email send result

        Why: Provides customer with written record of conversation and
        next steps.
        """
        customer_id = call_data.get("customer_id")
        email = call_data.get("customer_email")

        if not email:
            logger.warning("No customer email, skipping follow-up email")
            return {"success": False, "reason": "no_email"}

        # In production, use email service (SendGrid, SES, etc.)
        email_content = {
            "to": email,
            "subject": "Follow-up: Your recent call with Acme Support",
            "body": self._format_email_body(call_data, summary),
        }

        logger.info("Sending follow-up email", extra={"email": email})

        # Mock email send
        return {
            "success": True,
            "email_id": f"EMAIL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        }

    def _format_email_body(self, call_data: dict[str, Any], summary: str | None) -> str:
        """Format email body with call details.

        Args:
            call_data: Call information
            summary: Generated summary

        Returns:
            Formatted email body
        """
        body_parts = [
            "Hello,",
            "",
            "Thank you for contacting Acme Corporation customer support. "
            "Here's a summary of our conversation:",
            "",
            summary or "Call summary not available.",
            "",
        ]

        # Add action items if any
        action_items = call_data.get("action_items", [])
        if action_items:
            body_parts.extend(
                [
                    "Next steps:",
                    *[f"- {item}" for item in action_items],
                    "",
                ]
            )

        body_parts.extend(
            [
                "If you have any questions or need further assistance, "
                "please don't hesitate to reach out.",
                "",
                "Best regards,",
                "Acme Corporation Customer Support",
            ]
        )

        return "\n".join(body_parts)

    async def _create_support_ticket(
        self, call_data: dict[str, Any], summary: str | None
    ) -> dict[str, Any]:
        """Create support ticket for unresolved issues.

        Args:
            call_data: Call information
            summary: Generated summary

        Returns:
            Ticket creation result

        Why: Ensures low-satisfaction calls are tracked and followed up
        by human agents.
        """
        customer_id = call_data.get("customer_id")

        # In production, create ticket in your ticketing system (Zendesk, Jira, etc.)
        ticket_data = {
            "customer_id": customer_id,
            "subject": f"Follow-up needed: Low satisfaction call",
            "description": summary or "Call summary not available.",
            "priority": "high" if call_data.get("sentiment", 1) < 0.3 else "medium",
            "tags": ["low-satisfaction", "ai-escalation"],
            "call_sid": call_data.get("call_sid"),
        }

        logger.info("Creating support ticket", extra={"customer_id": customer_id})

        # Mock ticket creation
        ticket_id = f"TICKET-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return {
            "success": True,
            "ticket_id": ticket_id,
        }

    async def _log_metrics(self, call_data: dict[str, Any]) -> dict[str, Any]:
        """Log metrics for analytics.

        Args:
            call_data: Call information

        Returns:
            Metrics logging result

        Why: Tracks KPIs for call center performance (duration, resolution
        rate, satisfaction, etc.).
        """
        # In production, send to analytics system (DataDog, New Relic, etc.)
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "call_duration": call_data.get("duration", 0),
            "outcome": call_data.get("outcome"),
            "sentiment": call_data.get("sentiment", 0.5),
            "tools_used_count": len(call_data.get("tools_used", [])),
            "resolution_time": call_data.get("duration", 0),
        }

        logger.info("Logging metrics", extra=metrics)

        return {"success": True}


# Factory function for creating workflow from config
def create_post_call_workflow(config: dict[str, Any]) -> PostCallWorkflow:
    """Create post-call workflow from configuration.

    Args:
        config: Workflow configuration

    Returns:
        PostCallWorkflow instance

    Why: Provides dependency injection for easier testing and configuration.
    """
    return PostCallWorkflow(config)

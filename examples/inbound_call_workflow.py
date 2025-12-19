"""Example: Inbound Call Handling Workflow with Tools.

This example demonstrates how to use RAW's tool system to:
1. Trigger a workflow from an external event (Twilio incoming call)
2. Load customer context from a CRM
3. Handle a conversation using Converse
4. Summarize the call and update the CRM

Usage:
    # This workflow would be triggered by a webhook, not run directly.
    # For testing, you can run it manually:
    uv run python examples/inbound_call_workflow.py --phone="+15551234567"
"""

from pydantic import BaseModel, Field

from raw_runtime import BaseWorkflow, on_event, step
from raw_runtime.tools import ToolEventType


class CallParams(BaseModel):
    """Parameters for inbound call handling."""

    phone: str = Field(..., description="Caller phone number")
    call_sid: str = Field(default="", description="Twilio call SID")


@on_event("twilio.call.incoming")
class InboundCallWorkflow(BaseWorkflow[CallParams]):
    """Handle incoming phone calls with AI conversation.

    This workflow:
    1. Looks up the caller in the CRM
    2. Starts a conversation with context
    3. Logs conversation events
    4. Summarizes and updates CRM when done
    """

    @step("load_customer")
    async def load_customer(self) -> dict:
        """Load customer information from CRM."""
        self.log(f"Looking up customer: {self.params.phone}")

        # Use CRM tool to get customer data
        result = await self.tool("crm").call(
            action="get_contact",
            phone=self.params.phone,
        )

        if result.success:
            customer = result.data
            self.log(f"Found customer: {customer.get('name', 'Unknown')}")
            return customer

        self.log("Customer not found, creating new contact")
        return {"phone": self.params.phone, "is_new": True}

    @step("handle_conversation")
    async def handle_conversation(self, customer: dict) -> dict:
        """Handle the conversation using Converse capability."""
        self.log("Starting conversation...")

        transcript = []
        outcome = None

        # Use Converse tool for AI conversation
        async for event in self.tool("converse").run(
            bot="support",
            transport="twilio",
            call_sid=self.params.call_sid,
            context={
                "customer": customer,
                "channel": "voice",
            },
        ):
            if event.type == ToolEventType.MESSAGE:
                role = event.data.get("role", "assistant")
                text = event.data.get("text", "")
                transcript.append({"role": role, "text": text})
                self.log(f"[{role}]: {text[:50]}...")

            elif event.type == ToolEventType.CUSTOM:
                if event.data.get("event") == "tool_call":
                    self.log(f"Tool called: {event.data.get('tool_name')}")

            elif event.type == ToolEventType.COMPLETED:
                outcome = event.data.get("outcome")
                self.log(f"Conversation ended with outcome: {outcome}")

        return {
            "transcript": transcript,
            "outcome": outcome,
            "customer_id": customer.get("id"),
        }

    @step("summarize_call")
    async def summarize_call(self, conversation: dict) -> str:
        """Generate a summary of the call."""
        self.log("Generating call summary...")

        # Join transcript into text
        transcript_text = "\n".join(
            f"{msg['role']}: {msg['text']}" for msg in conversation["transcript"]
        )

        # Use summarize tool
        result = await self.tool("summarize").call(
            text=transcript_text,
            style="bullet_points",
            max_length=100,
        )

        if result.success:
            return result.data.get("summary", "No summary available")
        return "Summary generation failed"

    @step("update_crm")
    async def update_crm(self, customer: dict, conversation: dict, summary: str) -> None:
        """Update CRM with call details."""
        if not customer.get("id"):
            self.log("No customer ID, skipping CRM update")
            return

        self.log("Updating CRM with call details...")

        await self.tool("crm").call(
            action="create_activity",
            contact_id=customer["id"],
            data={
                "type": "call",
                "outcome": conversation.get("outcome"),
                "summary": summary,
                "duration": conversation.get("duration"),
            },
        )

        self.log("CRM updated successfully")

    def run(self) -> int:
        """Execute the inbound call workflow."""
        import asyncio

        async def _run():
            # Load customer context
            customer = await self.load_customer()

            # Handle the conversation
            conversation = await self.handle_conversation(customer)

            # Summarize the call
            summary = await self.summarize_call(conversation)

            # Update CRM
            await self.update_crm(customer, conversation, summary)

            # Save results
            self.save(
                "call_result.json",
                {
                    "customer": customer,
                    "outcome": conversation.get("outcome"),
                    "summary": summary,
                },
            )

        asyncio.run(_run())
        return 0


if __name__ == "__main__":
    InboundCallWorkflow.main()

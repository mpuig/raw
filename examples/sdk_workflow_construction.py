"""Example: Agent-Built Workflow using Python SDK.

This example demonstrates how an agent can programmatically construct
workflows using the RAW Python SDK instead of CLI commands.

The agent interprets a user request and builds a complete workflow
with tool discovery, step configuration, and validation.

Usage:
    python examples/sdk_workflow_construction.py
"""

from raw.sdk import create_workflow, add_step, get_workflow, list_workflows


def build_report_workflow(user_request: str) -> str:
    """Build a data report workflow from natural language request.

    This simulates an agent understanding a user's intent and constructing
    a workflow programmatically.

    Args:
        user_request: Natural language description of desired workflow

    Returns:
        Workflow ID of created workflow
    """
    print(f"User request: {user_request}")
    print("\nAgent reasoning:")
    print("  1. Need to fetch data from API")
    print("  2. Need to generate report from data")
    print("  3. Need to send report via email")
    print()

    # Create workflow
    print("Creating workflow...")
    workflow = create_workflow(
        name="daily-sales-report",
        intent=user_request,
    )
    print(f"✓ Created workflow: {workflow.id}")

    # Add data fetching step
    print("\nAdding step: fetch_sales_data")
    add_step(
        workflow,
        name="fetch_sales_data",
        tool="api_client",
        config={
            "endpoint": "/api/sales",
            "date_range": "last_24h",
            "format": "json",
        },
    )
    print("  ✓ Step added")

    # Add report generation step with inline code
    print("\nAdding step: generate_report")
    add_step(
        workflow,
        name="generate_report",
        code="""
import json
from datetime import datetime

def generate(sales_data):
    total = sum(item['amount'] for item in sales_data)
    count = len(sales_data)

    return {
        'date': datetime.now().isoformat(),
        'total_sales': total,
        'transaction_count': count,
        'average': total / count if count > 0 else 0
    }
        """,
    )
    print("  ✓ Step added")

    # Add email sending step
    print("\nAdding step: send_email")
    add_step(
        workflow,
        name="send_email",
        tool="email_sender",
        config={
            "to": "team@company.com",
            "subject": "Daily Sales Report - {results.generate_report.date}",
            "template": "sales_report",
            "data": "{results.generate_report}",
        },
    )
    print("  ✓ Step added")

    print(f"\n✓ Workflow ready: {workflow.id}")
    return workflow.id


def build_classification_workflow() -> str:
    """Build a classification workflow using @agentic decorator.

    This demonstrates combining SDK construction with selective agentic steps.
    """
    print("\nBuilding classification workflow with @agentic step...")

    workflow = create_workflow(
        name="ticket-classifier",
        intent="Classify support tickets by urgency and category",
    )

    # Add data loading step (deterministic)
    add_step(
        workflow,
        name="load_ticket",
        code="""
def load(ticket_id):
    # Fetch from database
    return {
        'id': ticket_id,
        'text': 'Customer cannot login, urgent',
        'customer_tier': 'enterprise'
    }
        """,
    )

    # Add classification step (agentic)
    add_step(
        workflow,
        name="classify_urgency",
        code="""
from typing import Literal
from raw_runtime import agentic

@agentic(
    prompt='''
    Classify support ticket urgency:
    Customer tier: {context.customer_tier}
    Issue: {context.text}

    Return ONLY: critical, high, medium, or low
    ''',
    model="claude-3-5-haiku-20241022",
    max_tokens=10,
    cost_limit=0.001
)
def classify(customer_tier: str, text: str) -> Literal["critical", "high", "medium", "low"]:
    pass  # Implementation injected by decorator
        """,
    )

    # Add routing step (deterministic)
    add_step(
        workflow,
        name="route_ticket",
        code="""
def route(urgency, ticket_id):
    queues = {
        'critical': 'tier1_immediate',
        'high': 'tier1_priority',
        'medium': 'tier2_standard',
        'low': 'tier3_batch'
    }
    return {'queue': queues[urgency], 'ticket_id': ticket_id}
        """,
    )

    print(f"✓ Created classification workflow: {workflow.id}")
    return workflow.id


def list_all_workflows() -> None:
    """List all workflows in the project."""
    print("\n" + "=" * 60)
    print("All Workflows")
    print("=" * 60)

    workflows = list_workflows()

    if not workflows:
        print("No workflows found")
        return

    for wf in workflows:
        print(f"\n{wf.name}")
        print(f"  ID: {wf.id}")
        print(f"  Status: {wf.status}")
        print(f"  Steps: {len(wf.steps)}")
        if wf.steps:
            for step in wf.steps:
                print(f"    - {step.name} ({step.tool or 'inline code'})")


def inspect_workflow(workflow_id: str) -> None:
    """Inspect a workflow's configuration."""
    print("\n" + "=" * 60)
    print(f"Inspecting Workflow: {workflow_id}")
    print("=" * 60)

    workflow = get_workflow(workflow_id)
    if not workflow:
        print(f"Workflow not found: {workflow_id}")
        return

    print(f"\nName: {workflow.name}")
    print(f"Status: {workflow.status}")
    print(f"Path: {workflow.path}")
    print(f"\nSteps ({len(workflow.steps)}):")

    for i, step in enumerate(workflow.steps, 1):
        print(f"\n{i}. {step.name}")
        print(f"   Tool: {step.tool or 'inline code'}")
        if step.inputs:
            print(f"   Config:")
            for key, value in step.inputs.items():
                print(f"     {key}: {value}")


if __name__ == "__main__":
    # Example 1: Build report workflow from user request
    print("=" * 60)
    print("Example 1: Agent-Built Report Workflow")
    print("=" * 60)

    user_request = "Fetch yesterday's sales data and email a summary report to the team"
    workflow_id = build_report_workflow(user_request)

    # Inspect the created workflow
    inspect_workflow(workflow_id)

    # Example 2: Build classification workflow with agentic steps
    print("\n" + "=" * 60)
    print("Example 2: Classification Workflow with @agentic")
    print("=" * 60)

    classifier_id = build_classification_workflow()
    inspect_workflow(classifier_id)

    # List all workflows
    list_all_workflows()

    print("\n" + "=" * 60)
    print("Next Steps")
    print("=" * 60)
    print(f"\nRun the report workflow:")
    print(f"  raw run {workflow_id}")
    print(f"\nRun the classifier workflow:")
    print(f"  raw run {classifier_id} --ticket-id 12345")
    print()

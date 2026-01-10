#!/usr/bin/env python3
"""Example: Agent builds workflow programmatically using SDK.

This shows Layer 1 of agent-native architecture - agents as builders.
Demonstrates how an agent can use the RAW SDK to construct workflows
from natural language requirements without manual YAML editing.

This is more sophisticated than CLI-only workflow creation - the agent
can reason about requirements, discover existing tools, compose steps,
and validate the workflow before execution.

Usage:
    python examples/agent_built_workflow.py
"""

from raw.sdk import add_step, create_workflow, get_workflow, list_workflows


def build_etl_pipeline() -> str:
    """Build a data ETL pipeline programmatically.

    Simulates an agent understanding: "Extract customer data from API,
    transform it to our schema, and load it into the database."
    """
    print("Agent reasoning about user request:")
    print("  'Extract customer data from API, transform, load to database'\n")
    print("Agent planning:")
    print("  1. Need HTTP client to fetch from API")
    print("  2. Need transformation logic (inline code)")
    print("  3. Need database loader tool")
    print()

    # Create workflow
    print("Creating workflow...")
    workflow = create_workflow(
        name="customer-etl",
        intent="Extract customer data from API, transform, and load to database",
    )
    print(f"✓ Created workflow: {workflow.id}\n")

    # Add extraction step
    print("Adding step: extract_customers")
    add_step(
        workflow,
        name="extract_customers",
        tool="http_client",
        config={
            "url": "https://api.example.com/customers",
            "method": "GET",
            "headers": {"Authorization": "Bearer {env.API_TOKEN}"},
        },
    )
    print("  ✓ Step added\n")

    # Add transformation step with inline code
    print("Adding step: transform_schema")
    add_step(
        workflow,
        name="transform_schema",
        code="""
def transform(raw_data):
    # Convert API schema to internal schema
    return [
        {
            "id": record["customer_id"],
            "name": record["full_name"].upper(),
            "email": record["email_address"],
            "joined": record["signup_date"],
        }
        for record in raw_data
    ]
        """,
    )
    print("  ✓ Step added\n")

    # Add loading step
    print("Adding step: load_to_database")
    add_step(
        workflow,
        name="load_to_database",
        tool="database",
        config={
            "connection": "{env.DB_URL}",
            "table": "customers",
            "operation": "upsert",
            "key": "id",
        },
    )
    print("  ✓ Step added\n")

    print(f"✓ Workflow ready: {workflow.id}")
    return workflow.id


def build_conditional_workflow() -> str:
    """Build a workflow with conditional steps.

    Shows how agents can construct workflows with branching logic
    based on runtime conditions.
    """
    print("\nBuilding conditional alert workflow...")

    workflow = create_workflow(
        name="conditional-alerts",
        intent="Monitor metrics and send alerts only when thresholds are exceeded",
    )

    # Fetch metrics (always runs)
    add_step(
        workflow,
        name="fetch_metrics",
        code="""
def fetch():
    import random
    return {
        'cpu_usage': random.uniform(0.3, 0.95),
        'memory_usage': random.uniform(0.4, 0.85),
        'disk_usage': random.uniform(0.5, 0.90)
    }
        """,
    )

    # Check if alert needed (conditional logic)
    add_step(
        workflow,
        name="check_thresholds",
        code="""
def check(metrics):
    exceeded = []
    thresholds = {'cpu_usage': 0.8, 'memory_usage': 0.7, 'disk_usage': 0.85}

    for metric, value in metrics.items():
        if value > thresholds[metric]:
            exceeded.append(f"{metric}: {value:.1%} > {thresholds[metric]:.1%}")

    return {
        'should_alert': len(exceeded) > 0,
        'exceeded': exceeded,
        'metrics': metrics
    }
        """,
    )

    # Send alert only if needed
    add_step(
        workflow,
        name="send_alert",
        tool="email",
        config={
            "to": "ops-team@company.com",
            "subject": "Alert: Threshold Exceeded",
            "body": "The following metrics exceeded thresholds:\n{results.check_thresholds.exceeded}",
        },
        # This would use @conditional decorator in the actual implementation
    )

    print(f"✓ Created conditional workflow: {workflow.id}")
    return workflow.id


def inspect_workflow_details(workflow_id: str) -> None:
    """Display detailed workflow configuration.

    Shows how agents can introspect workflows they've built
    to verify correctness before execution.
    """
    print("\n" + "=" * 70)
    print(f"Workflow Details: {workflow_id}")
    print("=" * 70)

    workflow = get_workflow(workflow_id)
    if not workflow:
        print(f"❌ Workflow not found: {workflow_id}")
        return

    print(f"\nName: {workflow.name}")
    print(f"Status: {workflow.status}")
    print(f"Intent: {workflow.intent or '(not specified)'}")
    print(f"\nSteps: {len(workflow.steps)}")

    for i, step in enumerate(workflow.steps, 1):
        print(f"\n  {i}. {step.name}")
        if step.tool:
            print(f"     Tool: {step.tool}")
        else:
            print("     Type: Inline code")

        if step.inputs:
            print("     Config:")
            for key, value in step.inputs.items():
                # Truncate long values
                value_str = str(value)
                if len(value_str) > 60:
                    value_str = value_str[:57] + "..."
                print(f"       {key}: {value_str}")


def list_all() -> None:
    """List all workflows in the project.

    Demonstrates how agents can query the workflow registry
    to understand what's already been built.
    """
    print("\n" + "=" * 70)
    print("All Workflows")
    print("=" * 70)

    workflows = list_workflows()

    if not workflows:
        print("\nNo workflows found")
        return

    print(f"\nFound {len(workflows)} workflows:\n")

    for wf in workflows:
        print(f"  {wf.name} ({wf.id})")
        print(f"    Status: {wf.status}")
        print(f"    Steps: {len(wf.steps)}")
        if wf.steps:
            step_names = ", ".join(s.name for s in wf.steps[:3])
            if len(wf.steps) > 3:
                step_names += "..."
            print(f"    Pipeline: {step_names}")
        print()


if __name__ == "__main__":
    print("=" * 70)
    print("Example 1: Agent-Built ETL Pipeline")
    print("=" * 70)
    print()

    # Build first workflow
    etl_id = build_etl_pipeline()
    inspect_workflow_details(etl_id)

    print("\n" + "=" * 70)
    print("Example 2: Conditional Alert Workflow")
    print("=" * 70)

    # Build second workflow
    alert_id = build_conditional_workflow()
    inspect_workflow_details(alert_id)

    # List all workflows
    list_all()

    # Show next steps
    print("=" * 70)
    print("Next Steps")
    print("=" * 70)
    print("\nRun the ETL pipeline:")
    print(f"  raw run {etl_id}")
    print("\nRun the alert workflow:")
    print(f"  raw run {alert_id}")
    print("\nValidate a workflow:")
    print(f"  raw validate {etl_id}")
    print()

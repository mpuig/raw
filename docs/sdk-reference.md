# RAW Python SDK Reference

Complete API reference for programmatic workflow construction.

## Installation

The SDK is included with RAW:

```bash
pip install raw-workflows
```

## Imports

```python
from raw.sdk import (
    create_workflow,
    list_workflows,
    get_workflow,
    update_workflow,
    delete_workflow,
    add_step,
    WorkflowNotFoundError,
    Workflow,
    Step,
)
```

## Workflow Management

### create_workflow()

Create a new workflow programmatically.

```python
def create_workflow(
    name: str,
    intent: str | None = None,
    description: str | None = None
) -> Workflow
```

**Parameters:**
- `name` (str): Human-readable workflow name (e.g., "stock-analysis")
- `intent` (str, optional): Natural language description of workflow purpose
- `description` (str, optional): Additional description (reserved for future use)

**Returns:**
- `Workflow`: Workflow object with metadata and path

**Raises:**
- `ValueError`: If workflow creation fails

**Example:**
```python
workflow = create_workflow(
    name="email-report",
    intent="Fetch metrics and send daily email report to team"
)

print(f"Created: {workflow.id}")
print(f"Path: {workflow.path}")
```

---

### list_workflows()

List all workflows in the current project.

```python
def list_workflows() -> list[Workflow]
```

**Returns:**
- `list[Workflow]`: List of all workflows (empty list if none)

**Example:**
```python
workflows = list_workflows()

for wf in workflows:
    print(f"{wf.name} ({wf.status})")
    print(f"  ID: {wf.id}")
    print(f"  Steps: {len(wf.steps)}")
```

---

### get_workflow()

Get a workflow by ID or partial match.

```python
def get_workflow(workflow_id: str) -> Workflow | None
```

**Parameters:**
- `workflow_id` (str): Full or partial workflow ID

**Returns:**
- `Workflow | None`: Workflow object or None if not found

**Example:**
```python
# Get by full ID
workflow = get_workflow("20250106-email-report-a1b2c3")

# Get by name (partial match)
workflow = get_workflow("email-report")

if workflow:
    print(f"Found: {workflow.name}")
else:
    print("Workflow not found")
```

---

### update_workflow()

Update workflow metadata.

```python
def update_workflow(
    workflow: Workflow,
    **kwargs: Any
) -> Workflow
```

**Parameters:**
- `workflow` (Workflow): Workflow to update
- `**kwargs`: Fields to update
  - `name` (str): New workflow name
  - `intent` (str): New intent description
  - `status` (str): New status ("draft", "published")
  - `version` (str): New version string

**Returns:**
- `Workflow`: Updated workflow object

**Raises:**
- `WorkflowNotFoundError`: If workflow doesn't exist

**Example:**
```python
workflow = get_workflow("email-report")

# Update metadata
workflow = update_workflow(
    workflow,
    status="published",
    version="1.0.0"
)
```

---

### delete_workflow()

Delete a workflow and all its files.

```python
def delete_workflow(workflow: Workflow) -> None
```

**Parameters:**
- `workflow` (Workflow): Workflow to delete

**Raises:**
- `WorkflowNotFoundError`: If workflow directory doesn't exist

**Example:**
```python
workflow = get_workflow("old-workflow")
if workflow:
    delete_workflow(workflow)
    print("Deleted successfully")
```

---

### add_step()

Add a step to a workflow.

```python
def add_step(
    workflow: Workflow,
    name: str,
    code: str | None = None,
    tool: str | None = None,
    config: dict[str, Any] | None = None
) -> Step
```

**Parameters:**
- `workflow` (Workflow): Workflow to add step to
- `name` (str): Step name (lowercase, underscores)
- `code` (str, optional): Inline Python code for the step
- `tool` (str, optional): Tool name to use (from tools/ directory)
- `config` (dict, optional): Configuration dict (maps to tool inputs)

**Returns:**
- `Step`: Step object with metadata

**Raises:**
- `ValueError`: If neither tool nor code provided, or both provided
- `WorkflowNotFoundError`: If workflow doesn't exist

**Example - Tool Step:**
```python
workflow = create_workflow("stock-report", "Fetch and report stock data")

# Add step using existing tool
add_step(
    workflow,
    name="fetch_data",
    tool="stock_fetcher",
    config={
        "ticker": "TSLA",
        "days": 30
    }
)
```

**Example - Inline Code Step:**
```python
# Add step with inline Python code
add_step(
    workflow,
    name="calculate_stats",
    code="""
def calculate(data):
    return {
        "mean": sum(data) / len(data),
        "max": max(data),
        "min": min(data)
    }
    """
)
```

---

## Data Models

### Workflow

Workflow metadata and configuration.

```python
class Workflow:
    id: str                  # Unique workflow ID
    name: str                # Human-readable name
    path: Path               # Filesystem path to workflow
    status: str              # "draft" or "published"
    description: str | None  # Optional description
    steps: list[Step]        # List of workflow steps
    version: str | None      # Version string
```

**Example:**
```python
workflow = get_workflow("email-report")

print(f"ID: {workflow.id}")
print(f"Name: {workflow.name}")
print(f"Status: {workflow.status}")
print(f"Steps: {len(workflow.steps)}")
print(f"Path: {workflow.path}")
```

---

### Step

Step metadata within a workflow.

```python
class Step:
    id: str                      # Unique step ID
    name: str                    # Step name
    description: str             # Step description
    tool: str | None             # Tool name (if tool-based)
    inputs: dict[str, Any]       # Step inputs/config
```

**Example:**
```python
workflow = get_workflow("email-report")

for step in workflow.steps:
    print(f"Step: {step.name}")
    print(f"  Tool: {step.tool}")
    print(f"  Config: {step.inputs}")
```

---

## Error Handling

### WorkflowNotFoundError

Raised when a workflow cannot be found.

```python
class WorkflowNotFoundError(Exception):
    pass
```

**Example:**
```python
from raw.sdk import WorkflowNotFoundError, get_workflow, delete_workflow

try:
    workflow = get_workflow("nonexistent")
    if workflow:
        delete_workflow(workflow)
except WorkflowNotFoundError as e:
    print(f"Error: {e}")
```

---

## Complete Examples

### Create and Configure Workflow

```python
from raw.sdk import create_workflow, add_step

# Create workflow
workflow = create_workflow(
    name="customer-onboarding",
    intent="Send welcome email and create CRM record for new customers"
)

# Add steps
add_step(
    workflow,
    name="validate_email",
    tool="email_validator",
    config={"email": "{params.customer_email}"}
)

add_step(
    workflow,
    name="create_crm_record",
    tool="crm_client",
    config={
        "action": "create",
        "data": {
            "email": "{params.customer_email}",
            "name": "{params.customer_name}",
            "source": "web"
        }
    }
)

add_step(
    workflow,
    name="send_welcome",
    tool="email_sender",
    config={
        "to": "{params.customer_email}",
        "template": "welcome"
    }
)

print(f"Created workflow: {workflow.id}")
print(f"Steps: {len(workflow.steps)}")
```

---

### List and Filter Workflows

```python
from raw.sdk import list_workflows

# Get all workflows
workflows = list_workflows()

# Filter published workflows
published = [wf for wf in workflows if wf.status == "published"]

print(f"Total workflows: {len(workflows)}")
print(f"Published: {len(published)}")

for wf in published:
    print(f"  {wf.name} v{wf.version}")
```

---

### Update Workflow Metadata

```python
from raw.sdk import get_workflow, update_workflow

# Get workflow
workflow = get_workflow("customer-onboarding")

if workflow:
    # Publish it
    workflow = update_workflow(
        workflow,
        status="published",
        version="1.0.0"
    )
    print(f"Published {workflow.name} v{workflow.version}")
```

---

### Clone and Modify Workflow

```python
from raw.sdk import get_workflow, create_workflow, add_step

# Get existing workflow
original = get_workflow("email-report")

# Create new workflow based on original
new_workflow = create_workflow(
    name="enhanced-email-report",
    intent=f"Enhanced version of {original.name}"
)

# Copy steps from original
for step in original.steps:
    add_step(
        new_workflow,
        name=step.name,
        tool=step.tool,
        config=step.inputs
    )

# Add new step
add_step(
    new_workflow,
    name="add_charts",
    tool="chart_generator",
    config={"type": "bar", "data": "{results.metrics}"}
)

print(f"Created enhanced workflow: {new_workflow.id}")
```

---

### Workflow Validation Pattern

```python
from raw.sdk import create_workflow, add_step, get_workflow
from raw.validation import WorkflowValidator

# Create workflow
workflow = create_workflow("data-pipeline", "ETL pipeline for analytics")

add_step(workflow, name="extract", tool="api_client")
add_step(workflow, name="transform", tool="data_transformer")
add_step(workflow, name="load", tool="db_loader")

# Validate before running
validator = WorkflowValidator()
result = validator.validate(workflow.path)

if result.success:
    print("✓ Workflow valid")
    # Safe to run
else:
    print("✗ Validation failed:")
    for error in result.errors:
        print(f"  - {error}")
```

---

### Dynamic Workflow Generation

```python
from raw.sdk import create_workflow, add_step

def build_monitoring_workflow(services: list[str]) -> str:
    """Generate monitoring workflow for multiple services."""

    workflow = create_workflow(
        name="service-monitor",
        intent=f"Monitor {len(services)} services and send alerts"
    )

    # Add monitoring step for each service
    for service in services:
        add_step(
            workflow,
            name=f"check_{service}",
            tool="health_checker",
            config={
                "service": service,
                "timeout": 30
            }
        )

    # Add aggregation step
    add_step(
        workflow,
        name="aggregate_results",
        code="""
def aggregate(results):
    failed = [r for r in results if r['status'] != 'healthy']
    return {
        'total': len(results),
        'failed': len(failed),
        'services': failed
    }
        """
    )

    # Add alert step
    add_step(
        workflow,
        name="send_alert",
        tool="pagerduty",
        config={
            "severity": "high",
            "message": "{results.aggregate_results}"
        }
    )

    return workflow.id

# Generate workflow for 3 services
workflow_id = build_monitoring_workflow(["api", "web", "worker"])
print(f"Generated workflow: {workflow_id}")
```

---

## Integration with CLI

SDK-created workflows work seamlessly with CLI:

```python
from raw.sdk import create_workflow, add_step
import subprocess

# Create workflow via SDK
workflow = create_workflow("my-workflow", "Do something useful")
add_step(workflow, name="process", tool="processor")

# Run via CLI
result = subprocess.run(
    ["raw", "run", workflow.id, "--arg", "value"],
    capture_output=True,
    text=True
)

print(result.stdout)
```

---

## Type Annotations

The SDK uses type annotations for better IDE support:

```python
from raw.sdk import Workflow, Step
from pathlib import Path

def process_workflow(workflow: Workflow) -> list[Step]:
    """Get all steps from a workflow."""
    return workflow.steps

def get_workflow_path(workflow: Workflow) -> Path:
    """Get filesystem path to workflow."""
    return workflow.path
```

Your IDE will provide autocomplete and type checking for all SDK functions and models.

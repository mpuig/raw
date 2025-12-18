# raw-agent

Autonomous workflow execution engine for RAW Platform.

## Installation

```bash
pip install raw-agent
```

## Usage

Create workflows with type-safe parameters and tracked steps:

```python
from pydantic import BaseModel, Field
from raw_agent import BaseWorkflow, step

class MyParams(BaseModel):
    input_file: str = Field(..., description="Input file path")
    threshold: float = Field(default=0.5, description="Processing threshold")

class MyWorkflow(BaseWorkflow[MyParams]):
    @step("load_data")
    def load_data(self) -> dict:
        # Load data from input file
        return {"records": 100}

    @step("process")
    def process(self) -> dict:
        # Process with threshold
        return {"filtered": 50}

    def run(self) -> int:
        data = self.load_data()
        result = self.process()
        return 0

# Execute workflow
params = MyParams(input_file="data.csv", threshold=0.7)
workflow = MyWorkflow(params=params)
exit_code = workflow.run()
```

## Features

- **Type-safe parameters**: Use Pydantic models for validation
- **Step tracking**: Automatic timing and event emission with @step decorator
- **Retry logic**: Add @retry for resilient operations
- **Result caching**: Use @cache for expensive computations
- **Context management**: Track workflow state and steps

## Decorators

### @step

Track step execution with timing and events:

```python
@step("fetch_data")
def fetch_data(self) -> dict:
    return {"data": "..."}
```

### @retry

Add retry logic with exponential backoff:

```python
@step("api_call")
@retry(retries=3, backoff="exponential")
def api_call(self):
    return requests.get(url)
```

### @cache

Cache expensive computations:

```python
@step("compute")
@cache
def compute(self, data):
    return expensive_calculation(data)
```

## Context management

Use WorkflowContext for advanced tracking:

```python
from raw_agent import WorkflowContext

context = WorkflowContext(
    workflow_id="my-workflow-001",
    workflow_name="my-workflow",
    parameters=params.model_dump()
)

with context:
    workflow = MyWorkflow(params=params, context=context)
    workflow.run()
    summary = context.finalize(success=True)
```

# RAW Quickstart

Get RAW running in 30 seconds.

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv): `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Setup

```bash
# Create project
mkdir my-project && cd my-project
uv init
uv add raw

# Initialize RAW (with Claude Code hooks)
raw init --hooks
```

## Create Your First Workflow

```bash
# Create a workflow with intent (Claude Code will implement it)
raw create my-workflow --intent "Describe what the workflow should do"

# Or create an empty workflow scaffold
raw create my-workflow

# List your workflows
raw list
```

## Run a Workflow

```bash
# Test with mocks first (recommended)
raw run my-workflow --dry

# Run for real
raw run my-workflow
```

**Example output:**
```
Starting workflow...

► Step 1: Fetching data...
✓ Fetched 10 items
► Step 2: Processing...
✓ Processing complete
► Step 3: Generating output...
✓ Report saved to results/output.md

✓ Workflow completed successfully!
```

Results are saved in the workflow's `results/` directory.

## What's Next?

- **Build your own workflow:** See [GUIDE.md](GUIDE.md)
- **Understand the architecture:** See [ARCHITECTURE.md](ARCHITECTURE.md)
- **API reference:** See [API.md](API.md)

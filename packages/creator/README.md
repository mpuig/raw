# raw-creator

Self-extension capabilities for RAW Platform. The creator agent can design, generate, validate, and refine tools and workflows.

## Installation

```bash
pip install raw-creator
```

## Usage

### Create a tool

```python
from raw_creator import CreatorAgent

agent = CreatorAgent()

# End-to-end tool creation with automatic refinement
tool_path, validation = agent.create_tool(
    intent="Fetch stock prices from Yahoo Finance API with support for historical data",
    name="fetch_stock",
    auto_refine=True
)

if validation.passed:
    print(f"Tool created successfully at {tool_path}")
else:
    print(f"Tool created with issues: {validation.errors}")
```

### Create a workflow

```python
from raw_creator import CreatorAgent

agent = CreatorAgent()

# End-to-end workflow creation
workflow_path, validation = agent.create_workflow(
    intent="Fetch TSLA stock data, calculate 50-day moving average and RSI, generate PDF report",
    name="stock_analysis",
    auto_refine=True
)

if validation.passed:
    print(f"Workflow created successfully at {workflow_path}")
```

### Manual control over phases

For more control, use individual phases:

```python
from raw_creator import CreatorAgent

agent = CreatorAgent()

# Phase 1: Design
spec = agent.design_tool(
    intent="Parse CSV files with automatic type detection",
    name="csv_parser"
)

# Phase 2: Generate
tool_path = agent.generate_tool(spec)

# Phase 3: Validate
validation = agent.validate(tool_path, CreatorType.TOOL)

# Phase 4: Refine (if needed)
if not validation.passed:
    tool_path = agent.refine(tool_path, validation, CreatorType.TOOL)
    validation = agent.validate(tool_path, CreatorType.TOOL)
```

## Architecture

The creator agent uses a skills-based architecture with progressive disclosure:

### Four phases

1. **Design**: Analyze user intent and create structured specifications
   - Extract inputs, outputs, and dependencies
   - Search for existing tools to avoid duplication
   - Generate design spec as Pydantic model

2. **Generate**: Create implementation files from design specs
   - Tools: `tool.py`, `__init__.py`, `test.py`, `config.yaml`
   - Workflows: `run.py`, `dry_run.py`, `mocks/`
   - Use templates for consistent structure

3. **Validate**: Run tests and quality checks
   - Syntax validation (Python parsing)
   - Import validation (can it be imported?)
   - Test execution (pytest for tools, dry-run for workflows)
   - Style checks (docstrings, naming conventions)

4. **Refine**: Fix issues based on validation feedback
   - Simulation-based improvement
   - Iterative refinement until validation passes
   - Preserve working functionality

### Skills

Each phase is implemented as a separate skill module:

- `skills/design.py` - Design specification generation
- `skills/generate.py` - Code generation from specs
- `skills/validate.py` - Testing and validation
- `skills/refine.py` - Iterative improvement

Skills are loaded on-demand using progressive disclosure. Only the needed skill is loaded when a phase is called.

## Design principles

### Progressive disclosure
Skills load on-demand, not eagerly. This keeps the agent lightweight and allows skills to be swapped or extended without changing the core agent.

### Simulation-based refinement
Use dry-runs and tests to identify issues before real execution. The refine skill analyzes validation errors and applies fixes iteratively.

### Type-safe parameters
All specs and results use Pydantic models for validation and type safety.

### Clear separation
Each phase has a single responsibility and clear inputs/outputs. This makes the system testable and maintainable.

## Examples

### Tool creation with dependencies

```python
agent = CreatorAgent()

# The design phase will automatically detect dependencies
tool_path, validation = agent.create_tool(
    intent="Scrape product data from e-commerce sites using BeautifulSoup and requests",
    name="product_scraper"
)
# Generated tool will include:
# dependencies = ["beautifulsoup4>=4.0", "requests>=2.28"]
```

### Workflow with multiple steps

```python
agent = CreatorAgent()

workflow_path, validation = agent.create_workflow(
    intent="Fetch top HackerNews stories, summarize with GPT-4, post to Slack",
    name="hn_digest"
)
# Generated workflow will have steps: fetch, summarize, post
```

### Custom refinement

```python
agent = CreatorAgent()

spec = agent.design_tool(
    intent="Calculate technical indicators for stock data",
    name="tech_indicators"
)

tool_path = agent.generate_tool(spec)
validation = agent.validate(tool_path, CreatorType.TOOL)

# Manual refinement with custom max iterations
max_iterations = 5
iterations = 0

while not validation.passed and iterations < max_iterations:
    print(f"Refinement iteration {iterations + 1}")
    print(f"Errors: {validation.errors}")

    tool_path = agent.refine(tool_path, validation, CreatorType.TOOL)
    validation = agent.validate(tool_path, CreatorType.TOOL)
    iterations += 1

if validation.passed:
    print("Tool validated successfully!")
else:
    print(f"Tool still has issues after {iterations} iterations")
    print(f"Errors: {validation.errors}")
    print(f"Warnings: {validation.warnings}")
```

## Integration with RAW CLI

The creator agent is designed to work with RAW CLI commands:

```bash
# Create tool using CLI (uses creator agent internally)
raw create fetch_stock --tool -d "Fetch stock data from Yahoo Finance"

# Create workflow using CLI
raw create stock_report --intent "Fetch TSLA data and generate report"

# The CLI delegates to CreatorAgent for implementation
```

## Development

### Running tests

```bash
cd packages/creator
uv run pytest tests/ -v
```

### Adding new skills

To add a new skill phase:

1. Create `src/raw_creator/skills/new_skill.py`
2. Implement the skill functions
3. Add enum value to `CreatorPhase` in `agent.py`
4. Add method to `CreatorAgent` that loads and uses the skill

### Extending existing skills

Skills are modular and can be extended:

```python
# Custom design skill with LLM-based intent parsing
from raw_creator.skills import design

def design_tool_with_llm(intent: str, name: str) -> DesignSpec:
    # Use LLM to parse intent
    parsed = llm_parse_intent(intent)

    # Fall back to default design logic
    return design.design_tool(intent, name)
```

## Dependencies

- `raw-core` - Core protocols and events
- `raw-agent` - Workflow engine with decorators
- `pydantic>=2.0` - Type-safe models

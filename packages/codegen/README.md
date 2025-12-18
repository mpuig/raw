# raw-codegen

Code generation, validation, and sandboxing package for RAW Platform creator functionality.

## Installation

```bash
pip install raw-codegen
```

## Overview

This package provides three core capabilities for the RAW Platform:

1. **Code Generation**: Template-based generation of tools and workflows
2. **Code Validation**: AST-based validation without execution
3. **Safe Execution**: Sandboxed code execution for testing

## Components

### Code Generator

Generate Python code from templates or programmatically:

```python
from raw_codegen import CodeGenerator, CodeGenContext, InputSpec, OutputSpec

# Define code specification
context = CodeGenContext(
    name="fetch_stock",
    description="Fetch stock data from Yahoo Finance",
    inputs=[
        InputSpec(name="ticker", type="str", description="Stock ticker symbol", required=True),
        InputSpec(name="period", type="str", description="Time period", required=False, default="1mo"),
    ],
    outputs=[
        OutputSpec(name="prices", type="list[float]", description="Historical prices"),
    ],
    dependencies=["yfinance>=0.2.0"],
)

# Generate tool files
generator = CodeGenerator()
files = generator.generate_tool_scaffold(context)

# files contains: tool.py, test.py, __init__.py, README.md
print(files["tool.py"])
```

### Code Validator

Validate Python code using AST analysis:

```python
from raw_codegen import CodeValidator, validate_code

# Validate source code
source = '''
def hello(name: str) -> str:
    return f"Hello, {name}!"
'''

result = validate_code(source)
print(f"Valid: {result.valid}")
for issue in result.issues:
    print(f"  {issue.severity}: {issue.message}")

# Check for dangerous operations
dangerous_code = '''
def dangerous():
    eval("print('unsafe')")
'''

result = validate_code(dangerous_code)
if result.has_errors():
    print("Code contains dangerous operations!")

# Analyze imports
validator = CodeValidator()
imports = validator.analyze_imports(source)
print(f"Imports: {imports}")

# Analyze functions
functions = validator.analyze_functions(source)
print(f"Functions: {functions}")
```

### Safe Execution Sandbox

Execute code in an isolated environment:

```python
from raw_codegen import CodeSandbox, execute_source
from pathlib import Path

# Execute a script
sandbox = CodeSandbox(timeout_seconds=30.0)
result = sandbox.execute_script(Path("tool.py"), args=["--ticker", "AAPL"])

if result.success:
    print(f"Output: {result.stdout}")
else:
    print(f"Error: {result.stderr}")

# Execute source code directly
source = '''
print("Hello from sandbox!")
'''

result = execute_source(source)
print(f"Exit code: {result.exit_code}")
print(f"Duration: {result.duration_seconds}s")

# Validate imports are available
sandbox = CodeSandbox()
result = sandbox.validate_imports('''
import requests
import pandas as pd
''')

if result.success:
    print("All imports available")
```

### Mock Data Generation

Generate test fixtures for code testing:

```python
from raw_codegen import MockEnvironment

# Create mock environment
mock_env = MockEnvironment()

# Generate mock data by type
ticker_mock = mock_env.generate_mock_data("str", "ticker")  # "mock_ticker"
price_mock = mock_env.generate_mock_data("float", "price")  # 3.14

# Create test fixtures from function signature
function_info = {
    "name": "fetch_stock",
    "args": [
        {"name": "ticker", "type": "str"},
        {"name": "period", "type": "str"},
    ]
}

fixtures = mock_env.create_test_fixtures(function_info)
# {"ticker": "mock_ticker", "period": "mock_period"}
```

## Architecture

This package follows clean architecture principles:

### Separation of Concerns

- **Generator**: Pure code generation, no I/O
- **Validator**: AST analysis only, no execution
- **Sandbox**: Isolated execution, resource-limited

### Type Safety

All models use Pydantic for validation:

```python
from raw_codegen import CodeGenContext, InputSpec

# Type-safe context creation
context = CodeGenContext(
    name="my_tool",
    description="Tool description",
    inputs=[InputSpec(name="arg", type="str", description="Argument")]
)

# Validation happens automatically
try:
    invalid = CodeGenContext(name="")  # ValidationError: name cannot be empty
except Exception as e:
    print(f"Validation error: {e}")
```

### Immutability

Validation results are immutable dataclasses:

```python
from raw_codegen import ValidationResult, ValidationIssue

result = ValidationResult(
    valid=True,
    issues=[],
    ast_tree=None
)

# result.valid = False  # Error: frozen dataclass
```

## Validation Features

### Dangerous Operation Detection

The validator detects potentially unsafe operations:

```python
from raw_codegen import validate_code

# Detects eval, exec, compile
code = "eval('malicious code')"
result = validate_code(code)
assert result.has_errors()
assert "Dangerous operation" in result.errors[0].message

# Detects unsafe subprocess calls
code = "import os; os.system('rm -rf /')"
result = validate_code(code)
assert len(result.warnings) > 0
```

### Import Analysis

Extract all imports from code:

```python
from raw_codegen import CodeValidator

validator = CodeValidator()
source = '''
import json
from pathlib import Path
from typing import Any, Dict
'''

imports = validator.analyze_imports(source)
print(imports)
# {
#   "imports": ["json"],
#   "from_imports": {
#     "pathlib": ["Path"],
#     "typing": ["Any", "Dict"]
#   }
# }
```

### Function Analysis

Extract function signatures and metadata:

```python
from raw_codegen import CodeValidator

validator = CodeValidator()
source = '''
def process_data(data: list[str], limit: int = 10) -> dict:
    """Process the data."""
    return {"count": len(data)}

async def fetch_api(url: str) -> dict:
    """Fetch from API."""
    pass
'''

functions = validator.analyze_functions(source)
print(functions["process_data"])
# {
#   "name": "process_data",
#   "args": [
#     {"name": "data", "type": "list[str]"},
#     {"name": "limit", "type": "int"}
#   ],
#   "return_type": "dict",
#   "docstring": "Process the data.",
#   "line": 1,
#   "is_async": False
# }
```

### PEP 723 Header Validation

Check for inline script metadata:

```python
from raw_codegen import CodeValidator

validator = CodeValidator()
source = '''
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28"]
# ///
import requests
'''

result = validator.check_pep723_header(source)
assert result.valid
```

## Sandbox Features

### Resource Limits

Execution is time-limited to prevent infinite loops:

```python
from raw_codegen import CodeSandbox, SandboxError

sandbox = CodeSandbox(timeout_seconds=5.0)

try:
    # This will timeout
    result = sandbox.execute_source('''
import time
time.sleep(10)
''')
except SandboxError as e:
    print(f"Timeout: {e}")
```

### Subprocess Isolation

Code runs in separate processes with no access to parent state:

```python
from raw_codegen import execute_source

# Each execution is isolated
result1 = execute_source('x = 1; print(x)')
result2 = execute_source('print(x)')  # NameError: x not defined
```

### Test Execution

Run pytest tests in the sandbox:

```python
from raw_codegen import CodeSandbox
from pathlib import Path

sandbox = CodeSandbox()
result = sandbox.run_tests(Path("tools/my_tool/test.py"))

if result.success:
    print("All tests passed!")
else:
    print(f"Tests failed:\n{result.stderr}")
```

## Use Cases

### Tool Creation Workflow

```python
from raw_codegen import CodeGenerator, CodeGenContext, InputSpec, validate_code
from pathlib import Path

# 1. Define tool specification
context = CodeGenContext(
    name="csv_parser",
    description="Parse CSV files with automatic type detection",
    inputs=[
        InputSpec(name="file_path", type="str", description="Path to CSV file")
    ],
    dependencies=["pandas>=2.0"],
)

# 2. Generate scaffold
generator = CodeGenerator()
files = generator.generate_tool_scaffold(context)

# 3. Validate generated code
for filename, content in files.items():
    result = validate_code(content)
    if not result.valid:
        print(f"{filename} has issues: {result.errors}")

# 4. Write files
tool_dir = Path("tools/csv_parser")
tool_dir.mkdir(parents=True, exist_ok=True)
for filename, content in files.items():
    (tool_dir / filename).write_text(content)
```

### Code Review Pipeline

```python
from raw_codegen import CodeValidator, CodeSandbox
from pathlib import Path

def review_code(file_path: Path) -> bool:
    """Review code for safety and correctness."""
    validator = CodeValidator(strict=True)

    # 1. Validate syntax and safety
    result = validator.validate_file(file_path)
    if not result.valid:
        print(f"Validation failed: {result.errors}")
        return False

    # 2. Check for required functions
    source = file_path.read_text()
    result = validator.check_required_functions(source, ["main"])
    if not result.valid:
        print("Missing main() function")
        return False

    # 3. Verify imports are available
    sandbox = CodeSandbox()
    try:
        result = sandbox.validate_imports(source)
        if not result.success:
            print("Import validation failed")
            return False
    except Exception as e:
        print(f"Sandbox error: {e}")
        return False

    return True
```

## Error Handling

All operations use structured error types:

```python
from raw_codegen import SandboxError, ValidationResult

try:
    result = execute_script(Path("nonexistent.py"))
except SandboxError as e:
    print(f"Execution error: {e}")

# Validation returns results, never raises
result = validate_code("invalid python {{{")
if not result.valid:
    for error in result.errors:
        print(f"Line {error.line}: {error.message}")
```

## Dependencies

- **raw-core**: Core protocols and errors
- **pydantic**: Type validation
- **jinja2**: Template rendering

## Development

Run tests:

```bash
pytest tests/ -v
```

## License

See main RAW Platform license.

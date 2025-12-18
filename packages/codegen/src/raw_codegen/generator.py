"""Code generation utilities for RAW creator functionality.

Provides template-based code generation for tools and workflows with support
for progressive disclosure and intelligent defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel, Field


class InputSpec(BaseModel):
    """Specification for a tool or workflow input parameter."""

    name: str = Field(..., description="Parameter name")
    type: str = Field(default="str", description="Python type annotation")
    description: str = Field(..., description="Human-readable description")
    required: bool = Field(default=True, description="Whether parameter is required")
    default: Any | None = Field(default=None, description="Default value if not required")


class OutputSpec(BaseModel):
    """Specification for a tool or workflow output."""

    name: str = Field(..., description="Output field name")
    type: str = Field(default="Any", description="Python type annotation")
    description: str = Field(..., description="Human-readable description")


class CodeGenContext(BaseModel):
    """Context for code generation templates."""

    name: str = Field(..., description="Tool or workflow name")
    description: str = Field(..., description="What the code does")
    inputs: list[InputSpec] = Field(default_factory=list)
    outputs: list[OutputSpec] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list, description="PEP 723 dependencies")
    extra: dict[str, Any] = Field(default_factory=dict, description="Template-specific context")


class CodeGenerator:
    """Generate Python code from templates with validation.

    Supports both Jinja2 templates and direct string generation.
    Follows clean architecture by separating generation logic from I/O.
    """

    def __init__(self, templates_dir: Path | None = None) -> None:
        """Initialize code generator.

        Args:
            templates_dir: Directory containing Jinja2 templates (optional)
        """
        self.templates_dir = templates_dir
        self._env: Environment | None = None

    @property
    def env(self) -> Environment:
        """Lazy-load Jinja2 environment."""
        if self._env is None:
            if self.templates_dir is None:
                raise ValueError("templates_dir not configured")
            self._env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                keep_trailing_newline=True,
                trim_blocks=False,
                lstrip_blocks=False,
            )
        return self._env

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a Jinja2 template with context.

        Args:
            template_name: Template filename (e.g., "tool.py.j2")
            context: Template variables

        Returns:
            Rendered template content

        Raises:
            ValueError: If templates_dir not configured
        """
        template = self.env.get_template(template_name)
        return template.render(**context)

    def generate_tool_scaffold(self, context: CodeGenContext) -> dict[str, str]:
        """Generate complete tool scaffold files.

        Args:
            context: Code generation context with tool specifications

        Returns:
            Dict mapping filename to file contents
        """
        files = {}

        # Generate tool.py
        files["tool.py"] = self._generate_tool_implementation(context)

        # Generate test.py
        files["test.py"] = self._generate_tool_tests(context)

        # Generate __init__.py
        files["__init__.py"] = self._generate_tool_init(context)

        # Generate README.md
        files["README.md"] = self._generate_tool_readme(context)

        return files

    def generate_workflow_scaffold(self, context: CodeGenContext) -> dict[str, str]:
        """Generate complete workflow scaffold files.

        Args:
            context: Code generation context with workflow specifications

        Returns:
            Dict mapping filename to file contents
        """
        files = {}

        # Generate run.py
        files["run.py"] = self._generate_workflow_run(context)

        # Generate test.py
        files["test.py"] = self._generate_workflow_tests(context)

        # Generate dry_run.py
        files["dry_run.py"] = self._generate_workflow_dry_run(context)

        # Generate README.md
        files["README.md"] = self._generate_workflow_readme(context)

        return files

    def _generate_tool_implementation(self, context: CodeGenContext) -> str:
        """Generate tool.py implementation."""
        func_name = context.name.replace("-", "_")

        # Format dependencies for PEP 723 header
        deps_str = ""
        if context.dependencies:
            deps_str = "\n".join(f'#   "{dep}",' for dep in context.dependencies)
            deps_str = f"\n{deps_str}\n"

        # Format input parameters
        params = []
        for inp in context.inputs:
            if inp.required:
                params.append(f"{inp.name}: {inp.type}")
            else:
                default_val = repr(inp.default) if inp.default is not None else "None"
                params.append(f"{inp.name}: {inp.type} = {default_val}")
        params_str = ", ".join(params) if params else ""

        # Determine return type
        if len(context.outputs) > 1:
            return_type = f"tuple[{', '.join(o.type for o in context.outputs)}]"
        elif context.outputs:
            return_type = context.outputs[0].type
        else:
            return_type = "dict[str, Any]"

        # Format docstring sections
        args_doc = ""
        if context.inputs:
            args_doc = "    Args:\n"
            for inp in context.inputs:
                args_doc += f"        {inp.name}: {inp.description}\n"

        returns_doc = "    Returns:\n"
        if context.outputs:
            for out in context.outputs:
                returns_doc += f"        {out.name}: {out.description}\n"
        else:
            returns_doc += "        Dictionary with results\n"

        return f'''#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [{deps_str}# ]
# ///
"""{context.description}"""

from typing import Any


def {func_name}({params_str}) -> {return_type}:
    """{context.description}

{args_doc}
{returns_doc}
    Raises:
        ValueError: If inputs are invalid
    """
    # === Input Validation ===
    # TODO: Add input validation

    # === Main Logic ===
    # TODO: Implement tool logic

    # === Return Results ===
    raise NotImplementedError("Tool not implemented yet")


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="{context.description}")
{self._generate_arg_parser_args(context.inputs)}
    args = parser.parse_args()

    try:
        result = {func_name}({self._generate_function_call_args(context.inputs)})
        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        print(json.dumps({{"error": str(e)}}))
        exit(1)
'''

    def _generate_arg_parser_args(self, inputs: list[InputSpec]) -> str:
        """Generate argparse argument definitions."""
        lines = []
        for inp in inputs:
            arg_type = f", type={inp.type}" if inp.type != "str" else ""
            required = ", required=True" if inp.required else f", default={repr(inp.default)}"
            lines.append(f'    parser.add_argument("--{inp.name}"{arg_type}{required}, help="{inp.description}")')
        return "\n".join(lines) if lines else ""

    def _generate_function_call_args(self, inputs: list[InputSpec]) -> str:
        """Generate function call arguments from parsed args."""
        return ", ".join(f"args.{inp.name}" for inp in inputs) if inputs else ""

    def _generate_tool_tests(self, context: CodeGenContext) -> str:
        """Generate test.py for tool."""
        func_name = context.name.replace("-", "_")

        # Copy dependencies for tests
        deps_str = ""
        if context.dependencies:
            deps_str = "\n".join(f'#   "{dep}",' for dep in context.dependencies)
            deps_str = f"\n{deps_str}\n"

        return f'''#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pytest>=8.0",{deps_str}# ]
# ///
"""Tests for {context.name}."""

import pytest
from tool import {func_name}


class Test{context.name.replace("-", "_").title()}:
    def test_basic_usage(self) -> None:
        """Test normal usage."""
        # TODO: Implement test
        with pytest.raises(NotImplementedError):
            {func_name}()

    def test_invalid_input(self) -> None:
        """Test error handling."""
        # TODO: Implement error test
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''

    def _generate_tool_init(self, context: CodeGenContext) -> str:
        """Generate __init__.py for tool package."""
        func_name = context.name.replace("-", "_")
        return f'''"""{context.description}"""

from .tool import {func_name}

__all__ = ["{func_name}"]
'''

    def _generate_tool_readme(self, context: CodeGenContext) -> str:
        """Generate README.md for tool."""
        func_name = context.name.replace("-", "_")

        usage_args = []
        for inp in context.inputs:
            if inp.required:
                usage_args.append(f'{inp.name}="value"')
            else:
                usage_args.append(f'{inp.name}={repr(inp.default)}')
        usage_str = ", ".join(usage_args)

        return f'''# {context.name}

{context.description}

## Installation

Ensure dependencies are installed:

```bash
uv pip install {" ".join(context.dependencies) if context.dependencies else "# no external dependencies"}
```

## Usage

### As a Python module

```python
from tools.{context.name} import {func_name}

result = {func_name}({usage_str})
print(result)
```

### As a CLI tool

```bash
cd tools/{context.name}
uv run tool.py {" ".join(f"--{inp.name} <value>" for inp in context.inputs if inp.required)}
```

## Testing

```bash
cd tools/{context.name}
uv run pytest test.py -v
```
'''

    def _generate_workflow_run(self, context: CodeGenContext) -> str:
        """Generate run.py for workflow."""
        class_name = "".join(word.capitalize() for word in context.name.replace("-", " ").split())

        return f'''#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pydantic>=2.0",
#   "rich>=13.0",
# ]
# ///
"""{context.description}"""

from pydantic import BaseModel, Field

from raw_runtime import BaseWorkflow, step


class {class_name}Params(BaseModel):
    """Workflow parameters."""
    pass


class {class_name}(BaseWorkflow[{class_name}Params]):
    """{context.description}"""

    @step("execute")
    def execute(self) -> dict:
        """Execute workflow logic."""
        # TODO: Implement workflow
        return {{"status": "completed"}}

    def run(self) -> int:
        """Run workflow."""
        result = self.execute()
        self.save("result.json", result)
        return 0


if __name__ == "__main__":
    {class_name}.main()
'''

    def _generate_workflow_tests(self, context: CodeGenContext) -> str:
        """Generate test.py for workflow."""
        class_name = "".join(word.capitalize() for word in context.name.replace("-", " ").split())

        return f'''#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pytest>=8.0",
#   "pydantic>=2.0",
# ]
# ///
"""Tests for {context.name}."""

import pytest
from run import {class_name}, {class_name}Params


def test_workflow_execution():
    """Test workflow runs successfully."""
    params = {class_name}Params()
    workflow = {class_name}(params)
    exit_code = workflow.run()
    assert exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''

    def _generate_workflow_dry_run(self, context: CodeGenContext) -> str:
        """Generate dry_run.py for workflow."""
        return '''#!/usr/bin/env python3
"""Dry run validation - checks imports and syntax."""

if __name__ == "__main__":
    try:
        from run import *
        print("✓ Syntax valid")
        print("✓ Imports resolved")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        exit(1)
'''

    def _generate_workflow_readme(self, context: CodeGenContext) -> str:
        """Generate README.md for workflow."""
        return f'''# {context.name}

{context.description}

## Usage

```bash
raw run {context.name}
```

## Testing

```bash
cd .raw/workflows/{context.name}
uv run pytest test.py -v
```
'''


def create_generator(templates_dir: Path | None = None) -> CodeGenerator:
    """Factory function for creating a CodeGenerator.

    Args:
        templates_dir: Optional directory containing Jinja2 templates

    Returns:
        Configured CodeGenerator instance
    """
    return CodeGenerator(templates_dir=templates_dir)

"""
Generate skill for creator agent.

This skill generates actual code files from design specifications.
It uses templates to create tools and workflows with proper structure,
documentation, and test scaffolding.

Key responsibilities:
- Generate tool.py from design spec
- Generate workflow run.py from design spec
- Create test files with appropriate mocks
- Generate config files and documentation
- Ensure consistent code style and structure
"""

from pathlib import Path
from textwrap import dedent

from raw_creator.agent import DesignSpec


def generate_tool(spec: DesignSpec) -> Path:
    """
    Generate tool implementation files from design spec.

    Creates:
    - tools/<name>/tool.py - Main implementation
    - tools/<name>/__init__.py - Package exports
    - tools/<name>/test.py - Unit tests
    - tools/<name>/config.yaml - Metadata

    Args:
        spec: Design specification with inputs, outputs, dependencies

    Returns:
        Path to generated tool directory

    Example:
        >>> spec = DesignSpec(
        ...     name="fetch_stock",
        ...     description="Fetch stock data",
        ...     type=CreatorType.TOOL,
        ...     inputs=[{"name": "ticker", "type": "str", "required": True}],
        ...     outputs=[{"name": "prices", "type": "list[float]"}],
        ...     dependencies=["yfinance>=0.2"]
        ... )
        >>> tool_path = generate_tool(spec)
        >>> tool_path.exists()
        True
    """
    # Create tool directory
    tool_dir = Path.cwd() / "tools" / spec.name
    tool_dir.mkdir(parents=True, exist_ok=True)

    # Generate tool.py
    tool_py = _generate_tool_py(spec)
    (tool_dir / "tool.py").write_text(tool_py)

    # Generate __init__.py
    init_py = _generate_tool_init(spec)
    (tool_dir / "__init__.py").write_text(init_py)

    # Generate test.py
    test_py = _generate_tool_test(spec)
    (tool_dir / "test.py").write_text(test_py)

    # Generate config.yaml
    config_yaml = _generate_tool_config(spec)
    (tool_dir / "config.yaml").write_text(config_yaml)

    return tool_dir


def generate_workflow(spec: DesignSpec) -> Path:
    """
    Generate workflow implementation files from design spec.

    Creates:
    - .raw/workflows/<id>/run.py - Main workflow
    - .raw/workflows/<id>/dry_run.py - Mock version
    - .raw/workflows/<id>/mocks/ - Mock data files

    Args:
        spec: Design specification with steps and parameters

    Returns:
        Path to generated workflow directory

    Example:
        >>> spec = DesignSpec(
        ...     name="stock_analysis",
        ...     description="Analyze stock data",
        ...     type=CreatorType.WORKFLOW,
        ...     steps=["fetch", "process", "save"],
        ...     dependencies=["pandas>=2.0"]
        ... )
        >>> workflow_path = generate_workflow(spec)
        >>> workflow_path.exists()
        True
    """
    # Create workflow directory
    # In RAW, workflows go in .raw/workflows/<timestamp>-<name>-<id>/
    import time

    timestamp = time.strftime("%Y%m%d")
    workflow_id = f"{timestamp}-{spec.name}-001"
    workflow_dir = Path.cwd() / ".raw" / "workflows" / workflow_id
    workflow_dir.mkdir(parents=True, exist_ok=True)

    # Generate run.py
    run_py = _generate_workflow_run(spec)
    (workflow_dir / "run.py").write_text(run_py)

    # Generate dry_run.py
    dry_run_py = _generate_workflow_dry_run(spec)
    (workflow_dir / "dry_run.py").write_text(dry_run_py)

    # Create mocks directory
    mocks_dir = workflow_dir / "mocks"
    mocks_dir.mkdir(exist_ok=True)

    # Generate sample mock data
    mock_data = _generate_mock_data(spec)
    (mocks_dir / "sample_data.json").write_text(mock_data)

    return workflow_dir


def _generate_tool_py(spec: DesignSpec) -> str:
    """Generate tool.py content from spec."""
    # Build function signature from inputs
    params = []
    for inp in spec.inputs:
        param_str = f"{inp['name']}: {inp['type']}"
        if not inp.get("required", True):
            default = inp.get("default", "None")
            param_str += f" = {default}"
        params.append(param_str)

    params_str = ",\n    ".join(params) if params else ""

    # Build docstring args section
    args_doc = "\n".join(
        f"        {inp['name']}: {inp.get('description', 'Parameter')}"
        for inp in spec.inputs
    )

    # Build dependencies list
    deps = "\n".join(f'#   "{dep}",' for dep in spec.dependencies)

    return dedent(
        f'''\
        #!/usr/bin/env python3
        # /// script
        # requires-python = ">=3.10"
        # dependencies = [
        {deps}
        # ]
        # ///
        """
        {spec.name} - {spec.description}

        A reusable RAW tool for {spec.description}.
        """

        from typing import Any


        def {spec.name}(
            {params_str}
        ) -> dict[str, Any]:
            """{spec.description}

            Args:
        {args_doc}

            Returns:
                Dictionary containing the operation result

            Raises:
                ValueError: If inputs are invalid
            """
            # === Input Validation ===
            # TODO: Add input validation

            # === Main Logic ===
            # TODO: Implement tool logic

            # === Return Results ===
            return {{"success": True, "result": "not_implemented"}}


        # === CLI Support ===
        if __name__ == "__main__":
            import argparse
            import json

            parser = argparse.ArgumentParser(description=__doc__)

            # TODO: Add CLI arguments
            # parser.add_argument("--param", required=True)

            args = parser.parse_args()

            try:
                result = {spec.name}()
                print(json.dumps(result, indent=2, default=str))
            except ValueError as e:
                print(json.dumps({{"success": False, "error": str(e)}}))
                exit(1)
        '''
    )


def _generate_tool_init(spec: DesignSpec) -> str:
    """Generate __init__.py content from spec."""
    return dedent(
        f'''\
        """{spec.description}."""

        from .tool import {spec.name}

        __all__ = ["{spec.name}"]
        '''
    )


def _generate_tool_test(spec: DesignSpec) -> str:
    """Generate test.py content from spec."""
    return dedent(
        f'''\
        #!/usr/bin/env python3
        # /// script
        # requires-python = ">=3.10"
        # dependencies = [
        #   "pytest>=8.0",
        # ]
        # ///
        """Tests for {spec.name}."""

        import pytest
        from tool import {spec.name}


        class Test{spec.name.title().replace("_", "")}:
            def test_basic_usage(self) -> None:
                """Test normal usage."""
                # TODO: Implement test
                result = {spec.name}()
                assert result["success"] is True

            def test_invalid_input(self) -> None:
                """Test error handling."""
                # TODO: Implement validation test
                pass


        if __name__ == "__main__":
            pytest.main([__file__, "-v"])
        '''
    )


def _generate_tool_config(spec: DesignSpec) -> str:
    """Generate config.yaml content from spec."""
    inputs_yaml = "\n".join(
        f"  - name: {inp['name']}\n"
        f"    type: {inp['type']}\n"
        f"    required: {inp.get('required', True)}\n"
        f"    description: {inp.get('description', '')}"
        for inp in spec.inputs
    )

    outputs_yaml = "\n".join(
        f"  - name: {out['name']}\n"
        f"    type: {out['type']}\n"
        f"    description: {out.get('description', '')}"
        for out in spec.outputs
    )

    deps_yaml = "\n".join(f"  - {dep}" for dep in spec.dependencies)

    return dedent(
        f'''\
        name: {spec.name}
        description: {spec.description}
        version: 0.1.0

        inputs:
        {inputs_yaml}

        outputs:
        {outputs_yaml}

        dependencies:
        {deps_yaml}
        '''
    )


def _generate_workflow_run(spec: DesignSpec) -> str:
    """Generate workflow run.py content from spec."""
    # Build step methods from spec.steps
    steps = spec.steps or ["fetch", "process", "save"]
    step_methods = []

    for step in steps:
        step_methods.append(
            dedent(
                f'''\
                    @step("{step}")
                    def {step}(self) -> dict[str, Any]:
                        """Step: {step}."""
                        console.print(f"[bold blue]>[/] {step.title()}...")
                        # TODO: Implement {step} logic
                        return {{"status": "completed"}}
                '''
            )
        )

    steps_code = "\n\n".join(step_methods)

    # Build run method calls
    run_calls = "\n".join(f"        self.{step}()" for step in steps)

    # Build parameters
    params = []
    for inp in spec.inputs:
        param_type = inp["type"]
        param_desc = inp.get("description", f"{inp['name']} parameter")
        if inp.get("required", True):
            params.append(
                f'    {inp["name"]}: {param_type} = Field(..., description="{param_desc}")'
            )
        else:
            default = inp.get("default", "None")
            params.append(
                f'    {inp["name"]}: {param_type} = Field(default={default}, description="{param_desc}")'
            )

    params_str = "\n".join(params) if params else '    pass  # No parameters'

    # Build dependencies
    deps = "\n".join(f'#   "{dep}",' for dep in spec.dependencies)

    return dedent(
        f'''\
        #!/usr/bin/env python3
        # /// script
        # requires-python = ">=3.10"
        # dependencies = [
        #   "pydantic>=2.0",
        #   "rich>=13.0",
        {deps}
        # ]
        # ///
        """
        {spec.name} - {spec.description}

        Usage:
            uv run run.py
        """

        from pathlib import Path
        from typing import Any

        from pydantic import BaseModel, Field
        from rich.console import Console
        from raw_agent import BaseWorkflow, step

        console = Console()


        class WorkflowParams(BaseModel):
            """Parameters for {spec.name} workflow."""

        {params_str}


        class {spec.name.title().replace("_", "")}Workflow(BaseWorkflow[WorkflowParams]):
            """Main workflow implementation for {spec.description}."""

            def __init__(self, params: WorkflowParams) -> None:
                super().__init__(params)
                self.results_dir = Path("results")
                self.results_dir.mkdir(exist_ok=True)

        {steps_code}

            def run(self) -> int:
                """Execute the workflow."""
                try:
        {run_calls}

                    console.print("[bold green]Done![/]")
                    return 0

                except Exception as e:
                    console.print(f"[bold red]Error:[/] {{e}}")
                    return 1


        if __name__ == "__main__":
            # TODO: Add CLI argument parsing
            params = WorkflowParams()
            workflow = {spec.name.title().replace("_", "")}Workflow(params)
            exit(workflow.run())
        '''
    )


def _generate_workflow_dry_run(spec: DesignSpec) -> str:
    """Generate workflow dry_run.py content from spec."""
    # Similar to run.py but with mock data
    steps = spec.steps or ["fetch", "process", "save"]
    step_methods = []

    for step in steps:
        step_methods.append(
            dedent(
                f'''\
                    def {step}(self) -> dict[str, Any]:
                        """Mock {step} step."""
                        console.print(f"[dim]>[/] {step.title()} (mocked)")
                        # Return mock data
                        return {{"status": "completed", "mock": True}}
                '''
            )
        )

    steps_code = "\n\n".join(step_methods)
    run_calls = "\n".join(f"        self.{step}()" for step in steps)

    return dedent(
        f'''\
        #!/usr/bin/env python3
        """
        Dry run version of {spec.name} workflow.

        Uses mock data instead of real API calls for testing.
        """

        from pathlib import Path
        from typing import Any

        from rich.console import Console

        console = Console()


        class {spec.name.title().replace("_", "")}WorkflowDry:
            """Dry run version with mocked data."""

            def __init__(self) -> None:
                self.results_dir = Path("results")
                self.results_dir.mkdir(exist_ok=True)

        {steps_code}

            def run(self) -> int:
                """Execute dry run."""
                try:
        {run_calls}

                    console.print("[bold green]Dry run completed![/]")
                    return 0

                except Exception as e:
                    console.print(f"[bold red]Error:[/] {{e}}")
                    return 1


        if __name__ == "__main__":
            workflow = {spec.name.title().replace("_", "")}WorkflowDry()
            exit(workflow.run())
        '''
    )


def _generate_mock_data(spec: DesignSpec) -> str:
    """Generate sample mock data for workflow testing."""
    import json

    # Generate sample mock data based on spec
    mock = {
        "status": "ok",
        "data": {
            "source": "mock",
            "description": f"Mock data for {spec.name}",
        },
    }

    return json.dumps(mock, indent=2)

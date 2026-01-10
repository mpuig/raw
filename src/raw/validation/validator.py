"""Workflow validator for structure and dependencies.

Validates workflow structure, PEP 723 dependencies, tool imports,
and metadata completeness.
"""

import ast
import re
from pathlib import Path

from pydantic import BaseModel, Field
from rich.console import Console


class ValidationResult(BaseModel):
    """Result of workflow validation.

    Attributes:
        success: Whether validation passed
        errors: List of errors that must be fixed
        warnings: List of warnings that should be addressed
        suggestions: List of optional improvements
    """

    success: bool = Field(..., description="Whether validation passed")
    errors: list[str] = Field(default_factory=list, description="Errors that must be fixed")
    warnings: list[str] = Field(
        default_factory=list, description="Warnings that should be addressed"
    )
    suggestions: list[str] = Field(default_factory=list, description="Optional improvements")

    def format(self) -> str:
        """Format validation result for display with Rich.

        Returns:
            Formatted string suitable for Rich console output
        """
        lines: list[str] = []

        if self.success:
            lines.append("[green]✓[/green] Validation passed")
        else:
            lines.append("[red]✗[/red] Validation failed")

        if self.errors:
            lines.append("\n[red bold]Errors:[/red bold]")
            for error in self.errors:
                lines.append(f"  [red]•[/red] {error}")

        if self.warnings:
            lines.append("\n[yellow bold]Warnings:[/yellow bold]")
            for warning in self.warnings:
                lines.append(f"  [yellow]•[/yellow] {warning}")

        if self.suggestions:
            lines.append("\n[blue bold]Suggestions:[/blue bold]")
            for suggestion in self.suggestions:
                lines.append(f"  [blue]•[/blue] {suggestion}")

        return "\n".join(lines)

    def print(self) -> None:
        """Print formatted validation result to console."""
        console = Console()
        console.print(self.format())


class WorkflowValidator:
    """Validates workflow structure and dependencies.

    Checks:
    - run.py exists and is executable
    - PEP 723 dependencies are valid
    - Imported tools exist in tools/
    - Workflow metadata is complete
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize validator.

        Args:
            project_root: Root directory of the RAW project (contains tools/).
                         If None, uses current working directory.
        """
        self.project_root = project_root or Path.cwd()

    def validate(self, workflow_dir: Path) -> ValidationResult:
        """Validate workflow structure and dependencies.

        Args:
            workflow_dir: Path to workflow directory containing run.py

        Returns:
            ValidationResult with errors, warnings, and suggestions
        """
        errors: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []

        # Check run.py exists
        run_py = workflow_dir / "run.py"
        if not run_py.exists():
            errors.append(f"run.py not found in {workflow_dir}")
            return ValidationResult(success=False, errors=errors)

        # Read run.py content
        try:
            content = run_py.read_text()
        except Exception as e:
            errors.append(f"Failed to read run.py: {e}")
            return ValidationResult(success=False, errors=errors)

        # Check shebang
        if not content.startswith("#!/usr/bin/env python"):
            warnings.append("Missing shebang line (#!/usr/bin/env python3)")

        # Validate PEP 723 metadata
        pep723_errors, pep723_warnings = self._validate_pep723(content)
        errors.extend(pep723_errors)
        warnings.extend(pep723_warnings)

        # Parse imports
        try:
            tree = ast.parse(content)
            imports = self._extract_imports(tree)
        except SyntaxError as e:
            errors.append(f"Syntax error in run.py: {e}")
            return ValidationResult(success=False, errors=errors)

        # Validate tool imports
        tool_errors, tool_warnings, tool_suggestions = self._validate_tools(imports)
        errors.extend(tool_errors)
        warnings.extend(tool_warnings)
        suggestions.extend(tool_suggestions)

        # Check for BaseWorkflow usage
        if "BaseWorkflow" not in content:
            errors.append("run.py must subclass BaseWorkflow")

        # Check for run() method
        if not self._has_run_method(tree):
            errors.append("Workflow class must implement run() method")

        # Check for main entry point
        if 'if __name__ == "__main__"' not in content:
            warnings.append("Missing main entry point (if __name__ == '__main__')")

        # Check executable permission
        if not run_py.stat().st_mode & 0o111:
            suggestions.append("run.py should be executable (chmod +x run.py)")

        success = len(errors) == 0
        return ValidationResult(
            success=success,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
        )

    def _validate_pep723(self, content: str) -> tuple[list[str], list[str]]:
        """Validate PEP 723 script metadata.

        Args:
            content: Content of run.py

        Returns:
            Tuple of (errors, warnings)
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check for PEP 723 block
        pep723_pattern = r"# /// script\n(.*?)\n# ///"
        match = re.search(pep723_pattern, content, re.DOTALL)

        if not match:
            errors.append("Missing PEP 723 metadata block (# /// script)")
            return errors, warnings

        metadata = match.group(1)

        # Check for required fields
        if "requires-python" not in metadata:
            warnings.append("PEP 723: Missing requires-python")
        elif ">=3.10" not in metadata:
            warnings.append("PEP 723: Should require Python >=3.10")

        if "dependencies" not in metadata:
            warnings.append("PEP 723: Missing dependencies list")
        else:
            # Check for essential dependencies
            if "pydantic" not in metadata:
                warnings.append("PEP 723: Missing pydantic dependency")
            if "rich" not in metadata:
                warnings.append("PEP 723: Missing rich dependency")

        return errors, warnings

    def _extract_imports(self, tree: ast.AST) -> list[tuple[str, str | None]]:
        """Extract imports from AST.

        Args:
            tree: Parsed AST

        Returns:
            List of (module, alias) tuples
        """
        imports: list[tuple[str, str | None]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, alias.asname))
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append((node.module, None))

        return imports

    def _validate_tools(
        self, imports: list[tuple[str, str | None]]
    ) -> tuple[list[str], list[str], list[str]]:
        """Validate tool imports exist in tools/ directory.

        Args:
            imports: List of (module, alias) tuples

        Returns:
            Tuple of (errors, warnings, suggestions)
        """
        errors: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []

        tools_dir = self.project_root / "tools"
        if not tools_dir.exists():
            warnings.append("tools/ directory not found in project root")
            return errors, warnings, suggestions

        # Check tool imports
        for module, _ in imports:
            if module.startswith("tools.") or module.startswith("_tools."):
                tool_name = module.split(".")[1] if "." in module else module
                tool_path = tools_dir / tool_name

                if not tool_path.exists():
                    errors.append(f"Tool not found: {tool_name} (imported from {module})")
                elif (
                    not (tool_path / "__init__.py").exists()
                    and not (tool_path.with_suffix(".py")).exists()
                ):
                    warnings.append(f"Tool {tool_name} exists but missing __init__.py or .py file")

        return errors, warnings, suggestions

    def _has_run_method(self, tree: ast.AST) -> bool:
        """Check if AST contains a run() method.

        Args:
            tree: Parsed AST

        Returns:
            True if run() method exists
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "run":
                return True
        return False

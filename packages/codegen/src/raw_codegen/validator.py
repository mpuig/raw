"""Code validation utilities using AST analysis.

Provides safe validation of Python code without execution, checking for:
- Syntax errors
- Dangerous operations (eval, exec, compile)
- Import validity
- Function signatures
- Type hints
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ValidationIssue:
    """Represents a code validation issue."""

    severity: str  # "error", "warning", "info"
    message: str
    line: int | None = None
    column: int | None = None
    node_type: str | None = None


@dataclass
class ValidationResult:
    """Result of code validation."""

    valid: bool
    issues: list[ValidationIssue]
    ast_tree: ast.Module | None = None

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == "warning"]

    def has_errors(self) -> bool:
        """Check if validation found any errors."""
        return len(self.errors) > 0


class DangerousOperationDetector(ast.NodeVisitor):
    """AST visitor to detect dangerous operations.

    Checks for:
    - Direct calls to eval(), exec(), compile()
    - Use of __import__
    - File system operations that could be unsafe
    - Network operations without proper safeguards
    """

    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []
        self.dangerous_builtins = {"eval", "exec", "compile", "__import__"}
        self.dangerous_modules = {"os.system", "subprocess.call"}

    def visit_Call(self, node: ast.Call) -> Any:
        """Check function calls for dangerous operations."""
        # Check for dangerous built-in functions
        if isinstance(node.func, ast.Name):
            if node.func.id in self.dangerous_builtins:
                self.issues.append(
                    ValidationIssue(
                        severity="error",
                        message=f"Dangerous operation detected: {node.func.id}()",
                        line=node.lineno,
                        column=node.col_offset,
                        node_type="Call",
                    )
                )

        # Check for dangerous module functions
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                full_name = f"{node.func.value.id}.{node.func.attr}"
                if full_name in self.dangerous_modules:
                    self.issues.append(
                        ValidationIssue(
                            severity="warning",
                            message=f"Potentially unsafe operation: {full_name}",
                            line=node.lineno,
                            column=node.col_offset,
                            node_type="Call",
                        )
                    )

        self.generic_visit(node)
        return None


class ImportAnalyzer(ast.NodeVisitor):
    """Analyze imports in Python code."""

    def __init__(self) -> None:
        self.imports: list[str] = []
        self.from_imports: dict[str, list[str]] = {}

    def visit_Import(self, node: ast.Import) -> Any:
        """Record import statements."""
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
        return None

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        """Record from-import statements."""
        if node.module:
            names = [alias.name for alias in node.names]
            self.from_imports[node.module] = names
        self.generic_visit(node)
        return None


class FunctionAnalyzer(ast.NodeVisitor):
    """Analyze function definitions in Python code."""

    def __init__(self) -> None:
        self.functions: dict[str, dict[str, Any]] = {}

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        """Extract function signature information."""
        # Extract argument names and types
        args = []
        for arg in node.args.args:
            arg_info = {
                "name": arg.arg,
                "type": self._get_annotation(arg.annotation),
            }
            args.append(arg_info)

        # Extract return type
        return_type = self._get_annotation(node.returns)

        # Check for docstring
        docstring = ast.get_docstring(node)

        self.functions[node.name] = {
            "name": node.name,
            "args": args,
            "return_type": return_type,
            "docstring": docstring,
            "line": node.lineno,
            "is_async": False,
        }

        self.generic_visit(node)
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        """Extract async function signature information."""
        # Similar to FunctionDef but mark as async
        args = []
        for arg in node.args.args:
            arg_info = {
                "name": arg.arg,
                "type": self._get_annotation(arg.annotation),
            }
            args.append(arg_info)

        return_type = self._get_annotation(node.returns)
        docstring = ast.get_docstring(node)

        self.functions[node.name] = {
            "name": node.name,
            "args": args,
            "return_type": return_type,
            "docstring": docstring,
            "line": node.lineno,
            "is_async": True,
        }

        self.generic_visit(node)
        return None

    def _get_annotation(self, node: ast.expr | None) -> str | None:
        """Extract type annotation as string."""
        if node is None:
            return None
        return ast.unparse(node)


class CodeValidator:
    """Validate Python code using AST analysis.

    Provides safe validation without executing code.
    Follows separation of concerns by analyzing code structure only.
    """

    def __init__(self, strict: bool = False) -> None:
        """Initialize validator.

        Args:
            strict: If True, warnings are treated as errors
        """
        self.strict = strict

    def validate_source(self, source: str) -> ValidationResult:
        """Validate Python source code.

        Args:
            source: Python source code as string

        Returns:
            ValidationResult with issues found
        """
        issues: list[ValidationIssue] = []

        # Check for syntax errors
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    message=f"Syntax error: {e.msg}",
                    line=e.lineno,
                    column=e.offset,
                )
            )
            return ValidationResult(valid=False, issues=issues, ast_tree=None)

        # Check for dangerous operations
        danger_detector = DangerousOperationDetector()
        danger_detector.visit(tree)
        issues.extend(danger_detector.issues)

        # Determine if valid (no errors, or no warnings if strict)
        has_errors = any(i.severity == "error" for i in issues)
        has_warnings = any(i.severity == "warning" for i in issues)
        valid = not has_errors and (not has_warnings if self.strict else True)

        return ValidationResult(valid=valid, issues=issues, ast_tree=tree)

    def validate_file(self, file_path: Path) -> ValidationResult:
        """Validate Python source file.

        Args:
            file_path: Path to Python file

        Returns:
            ValidationResult with issues found
        """
        try:
            source = file_path.read_text()
            return self.validate_source(source)
        except FileNotFoundError:
            return ValidationResult(
                valid=False,
                issues=[
                    ValidationIssue(
                        severity="error",
                        message=f"File not found: {file_path}",
                    )
                ],
                ast_tree=None,
            )
        except Exception as e:
            return ValidationResult(
                valid=False,
                issues=[
                    ValidationIssue(
                        severity="error",
                        message=f"Failed to read file: {e}",
                    )
                ],
                ast_tree=None,
            )

    def analyze_imports(self, source: str) -> dict[str, Any]:
        """Analyze imports in Python code.

        Args:
            source: Python source code

        Returns:
            Dict with 'imports' and 'from_imports' keys
        """
        try:
            tree = ast.parse(source)
            analyzer = ImportAnalyzer()
            analyzer.visit(tree)
            return {
                "imports": analyzer.imports,
                "from_imports": analyzer.from_imports,
            }
        except SyntaxError:
            return {"imports": [], "from_imports": {}}

    def analyze_functions(self, source: str) -> dict[str, dict[str, Any]]:
        """Analyze function definitions in Python code.

        Args:
            source: Python source code

        Returns:
            Dict mapping function names to signature information
        """
        try:
            tree = ast.parse(source)
            analyzer = FunctionAnalyzer()
            analyzer.visit(tree)
            return analyzer.functions
        except SyntaxError:
            return {}

    def check_required_functions(
        self, source: str, required_functions: list[str]
    ) -> ValidationResult:
        """Check if source code contains required function definitions.

        Args:
            source: Python source code
            required_functions: List of function names that must be present

        Returns:
            ValidationResult indicating if all required functions exist
        """
        issues: list[ValidationIssue] = []

        functions = self.analyze_functions(source)
        for func_name in required_functions:
            if func_name not in functions:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        message=f"Missing required function: {func_name}",
                    )
                )

        valid = len(issues) == 0
        return ValidationResult(valid=valid, issues=issues)

    def check_pep723_header(self, source: str) -> ValidationResult:
        """Check if source has valid PEP 723 script header.

        Args:
            source: Python source code

        Returns:
            ValidationResult indicating if PEP 723 header is present and valid
        """
        issues: list[ValidationIssue] = []

        lines = source.split("\n")
        if not lines:
            issues.append(
                ValidationIssue(
                    severity="error",
                    message="Empty source code",
                )
            )
            return ValidationResult(valid=False, issues=issues)

        # Look for PEP 723 header in first 10 lines
        found_header = False
        for i, line in enumerate(lines[:10]):
            if "# /// script" in line:
                found_header = True
                break

        if not found_header:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message="Missing PEP 723 script header (# /// script)",
                    line=1,
                )
            )

        valid = not any(i.severity == "error" for i in issues)
        return ValidationResult(valid=valid, issues=issues)


def validate_code(source: str, strict: bool = False) -> ValidationResult:
    """Validate Python source code.

    Convenience function for creating a validator and running validation.

    Args:
        source: Python source code
        strict: If True, warnings are treated as errors

    Returns:
        ValidationResult with issues found
    """
    validator = CodeValidator(strict=strict)
    return validator.validate_source(source)


def validate_file(file_path: Path, strict: bool = False) -> ValidationResult:
    """Validate Python source file.

    Convenience function for creating a validator and validating a file.

    Args:
        file_path: Path to Python file
        strict: If True, warnings are treated as errors

    Returns:
        ValidationResult with issues found
    """
    validator = CodeValidator(strict=strict)
    return validator.validate_file(file_path)

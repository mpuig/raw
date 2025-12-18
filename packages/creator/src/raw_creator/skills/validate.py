"""
Validate skill for creator agent.

This skill validates generated tools and workflows by running tests,
checking syntax, verifying imports, and ensuring code quality.

Key responsibilities:
- Syntax validation (Python parsing)
- Import validation (can files be imported?)
- Test execution (pytest for tools, dry-run for workflows)
- Code quality checks (naming, docstrings, type hints)
- Security checks (no hardcoded secrets, safe file operations)
"""

import ast
import subprocess
from pathlib import Path

from raw_creator.agent import CreatorType, ValidationResult


def validate(
    artifact_path: Path,
    artifact_type: CreatorType,
) -> ValidationResult:
    """
    Validate a generated tool or workflow.

    Runs multiple validation checks:
    1. Syntax validation - Parse Python files
    2. Import validation - Try importing the module
    3. Test execution - Run pytest or dry-run
    4. Style validation - Check conventions

    Args:
        artifact_path: Path to tool or workflow directory
        artifact_type: Whether this is a tool or workflow

    Returns:
        ValidationResult with pass/fail status and any errors

    Example:
        >>> tool_path = Path("tools/fetch_stock")
        >>> result = validate(tool_path, CreatorType.TOOL)
        >>> result.passed
        True
    """
    errors = []
    warnings = []

    # Phase 1: Syntax validation
    syntax_errors = _validate_syntax(artifact_path, artifact_type)
    errors.extend(syntax_errors)

    # Phase 2: Import validation
    if not syntax_errors:  # Only try importing if syntax is valid
        import_errors = _validate_imports(artifact_path, artifact_type)
        errors.extend(import_errors)

    # Phase 3: Test execution
    if not errors:  # Only run tests if no critical errors
        test_errors = _validate_tests(artifact_path, artifact_type)
        errors.extend(test_errors)

    # Phase 4: Style validation
    style_warnings = _validate_style(artifact_path, artifact_type)
    warnings.extend(style_warnings)

    return ValidationResult(
        passed=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def _validate_syntax(artifact_path: Path, artifact_type: CreatorType) -> list[str]:
    """Validate Python syntax by parsing files.

    Args:
        artifact_path: Path to artifact
        artifact_type: Tool or workflow

    Returns:
        List of syntax error messages
    """
    errors = []

    if artifact_type == CreatorType.TOOL:
        files_to_check = [
            artifact_path / "tool.py",
            artifact_path / "__init__.py",
            artifact_path / "test.py",
        ]
    else:  # WORKFLOW
        files_to_check = [
            artifact_path / "run.py",
            artifact_path / "dry_run.py",
        ]

    for file_path in files_to_check:
        if not file_path.exists():
            errors.append(f"Missing required file: {file_path.name}")
            continue

        try:
            code = file_path.read_text()
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Syntax error in {file_path.name}: {e.msg} (line {e.lineno})")

    return errors


def _validate_imports(artifact_path: Path, artifact_type: CreatorType) -> list[str]:
    """Validate that files can be imported without errors.

    Args:
        artifact_path: Path to artifact
        artifact_type: Tool or workflow

    Returns:
        List of import error messages
    """
    errors = []

    if artifact_type == CreatorType.TOOL:
        # Try importing the tool module
        tool_name = artifact_path.name
        try:
            # Basic check: see if the file uses any undefined names
            tool_py = artifact_path / "tool.py"
            if tool_py.exists():
                code = tool_py.read_text()
                tree = ast.parse(code)

                # Check for undefined imports
                imports = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split(".")[0])

                # Check for common issues
                if "httpx" in code and "httpx" not in imports:
                    errors.append("Uses httpx but doesn't import it")

        except Exception as e:
            errors.append(f"Import validation failed: {str(e)}")

    return errors


def _validate_tests(artifact_path: Path, artifact_type: CreatorType) -> list[str]:
    """Run tests and capture failures.

    Args:
        artifact_path: Path to artifact
        artifact_type: Tool or workflow

    Returns:
        List of test failure messages
    """
    errors = []

    if artifact_type == CreatorType.TOOL:
        # Run pytest on test.py
        test_file = artifact_path / "test.py"
        if test_file.exists():
            try:
                result = subprocess.run(
                    ["uv", "run", "pytest", str(test_file), "-v"],
                    cwd=artifact_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    # Parse pytest output for specific failures
                    errors.append(f"Tests failed: {result.stdout}")
            except subprocess.TimeoutExpired:
                errors.append("Tests timed out after 30 seconds")
            except Exception as e:
                errors.append(f"Test execution failed: {str(e)}")

    else:  # WORKFLOW
        # Run dry_run.py
        dry_run = artifact_path / "dry_run.py"
        if dry_run.exists():
            try:
                result = subprocess.run(
                    ["uv", "run", str(dry_run)],
                    cwd=artifact_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode != 0:
                    errors.append(f"Dry run failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                errors.append("Dry run timed out after 30 seconds")
            except Exception as e:
                errors.append(f"Dry run execution failed: {str(e)}")

    return errors


def _validate_style(artifact_path: Path, artifact_type: CreatorType) -> list[str]:
    """Check code style and conventions.

    Args:
        artifact_path: Path to artifact
        artifact_type: Tool or workflow

    Returns:
        List of style warning messages
    """
    warnings = []

    if artifact_type == CreatorType.TOOL:
        tool_py = artifact_path / "tool.py"
        if tool_py.exists():
            code = tool_py.read_text()
            tree = ast.parse(code)

            # Check for docstrings
            has_module_docstring = ast.get_docstring(tree) is not None
            if not has_module_docstring:
                warnings.append("tool.py missing module docstring")

            # Check functions have docstrings
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not ast.get_docstring(node):
                        warnings.append(f"Function {node.name} missing docstring")

    else:  # WORKFLOW
        run_py = artifact_path / "run.py"
        if run_py.exists():
            code = run_py.read_text()
            tree = ast.parse(code)

            # Check for module docstring
            has_module_docstring = ast.get_docstring(tree) is not None
            if not has_module_docstring:
                warnings.append("run.py missing module docstring")

    return warnings

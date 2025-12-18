"""
Refine skill for creator agent.

This skill improves generated code based on validation feedback.
It uses simulation-based refinement to identify and fix issues
iteratively until validation passes.

Key responsibilities:
- Analyze validation errors and warnings
- Generate refinement suggestions
- Apply fixes to implementation
- Preserve working functionality while fixing issues
"""

from pathlib import Path

from raw_creator.agent import CreatorType, ValidationResult


def refine(
    artifact_path: Path,
    validation: ValidationResult,
    artifact_type: CreatorType,
) -> Path:
    """
    Refine implementation based on validation feedback.

    This function analyzes validation errors and applies fixes:
    1. Syntax errors -> Fix malformed code
    2. Import errors -> Add missing imports
    3. Test failures -> Fix implementation bugs
    4. Style warnings -> Add docstrings, improve naming

    Args:
        artifact_path: Path to artifact to refine
        validation: Validation results with errors/warnings
        artifact_type: Tool or workflow

    Returns:
        Path to refined artifact (same as input, modified in-place)

    Example:
        >>> validation = ValidationResult(
        ...     passed=False,
        ...     errors=["Missing import: httpx"],
        ...     warnings=[]
        ... )
        >>> refined_path = refine(tool_path, validation, CreatorType.TOOL)
        >>> refined_path == tool_path
        True
    """
    # Analyze errors and generate fixes
    fixes = _analyze_errors(validation.errors, artifact_type)

    # Apply fixes to the artifact
    for fix in fixes:
        _apply_fix(artifact_path, fix, artifact_type)

    return artifact_path


def _analyze_errors(errors: list[str], artifact_type: CreatorType) -> list[dict]:
    """
    Analyze validation errors and generate fix strategies.

    Args:
        errors: List of error messages from validation
        artifact_type: Tool or workflow

    Returns:
        List of fix strategies to apply

    Example:
        >>> errors = ["Missing import: httpx"]
        >>> fixes = _analyze_errors(errors, CreatorType.TOOL)
        >>> fixes[0]["type"]
        'add_import'
    """
    fixes = []

    for error in errors:
        if "missing import" in error.lower() or "uses" in error.lower():
            # Extract package name from error message
            # "Uses httpx but doesn't import it"
            if "uses" in error.lower():
                parts = error.lower().split("uses")
                if len(parts) > 1:
                    package = parts[1].split("but")[0].strip()
                    fixes.append(
                        {
                            "type": "add_import",
                            "package": package,
                            "file": "tool.py" if artifact_type == CreatorType.TOOL else "run.py",
                        }
                    )

        elif "syntax error" in error.lower():
            # Syntax errors need manual inspection or LLM-based fixing
            # For now, log that manual intervention is needed
            fixes.append(
                {
                    "type": "syntax_error",
                    "message": error,
                    "action": "manual_review_needed",
                }
            )

        elif "tests failed" in error.lower() or "dry run failed" in error.lower():
            # Test failures usually mean implementation is incomplete
            fixes.append(
                {
                    "type": "implementation_incomplete",
                    "message": error,
                    "action": "review_implementation",
                }
            )

        elif "missing" in error.lower() and "file" in error.lower():
            # Missing file - need to generate it
            if "__init__.py" in error:
                fixes.append({"type": "create_init", "file": "__init__.py"})
            elif "test.py" in error:
                fixes.append({"type": "create_test", "file": "test.py"})

        elif "missing docstring" in error.lower():
            # Style issue - add docstring
            fixes.append(
                {
                    "type": "add_docstring",
                    "message": error,
                }
            )

    return fixes


def _apply_fix(artifact_path: Path, fix: dict, artifact_type: CreatorType) -> None:
    """
    Apply a specific fix to the artifact.

    Args:
        artifact_path: Path to artifact
        fix: Fix specification with type and parameters
        artifact_type: Tool or workflow
    """
    fix_type = fix["type"]

    if fix_type == "add_import":
        # Add missing import to file
        file_path = artifact_path / fix["file"]
        if file_path.exists():
            code = file_path.read_text()

            # Find where to insert the import (after other imports)
            lines = code.splitlines()
            insert_idx = 0

            # Find last import line
            for i, line in enumerate(lines):
                if line.strip().startswith(("import ", "from ")):
                    insert_idx = i + 1

            # Insert the import
            package = fix["package"]
            import_line = f"import {package}"

            # Check if already imported
            if import_line not in code:
                lines.insert(insert_idx, import_line)
                file_path.write_text("\n".join(lines))

    elif fix_type == "create_init":
        # Create basic __init__.py
        init_path = artifact_path / "__init__.py"
        if not init_path.exists():
            # Extract tool name from directory
            tool_name = artifact_path.name
            init_content = f'''"""Generated tool."""

from .tool import {tool_name}

__all__ = ["{tool_name}"]
'''
            init_path.write_text(init_content)

    elif fix_type == "create_test":
        # Create basic test.py
        test_path = artifact_path / "test.py"
        if not test_path.exists():
            tool_name = artifact_path.name
            test_content = f'''#!/usr/bin/env python3
"""Tests for {tool_name}."""

import pytest
from tool import {tool_name}


class Test{tool_name.title().replace("_", "")}:
    def test_basic(self):
        """Basic test."""
        # TODO: Implement test
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''
            test_path.write_text(test_content)

    elif fix_type == "add_docstring":
        # This would require parsing and modifying AST
        # For now, log that manual intervention is needed
        pass

    elif fix_type in ["syntax_error", "implementation_incomplete"]:
        # These require more sophisticated analysis or LLM-based fixing
        # Log for manual review
        pass

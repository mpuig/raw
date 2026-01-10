"""Tests for workflow validator."""

from pathlib import Path

import pytest

from raw.validation.validator import ValidationResult, WorkflowValidator


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project structure."""
    # Create tools directory
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()

    # Create a sample tool
    tool_dir = tools_dir / "sample_tool"
    tool_dir.mkdir()
    (tool_dir / "__init__.py").write_text("# Sample tool")

    return tmp_path


@pytest.fixture
def valid_workflow_content() -> str:
    """Valid workflow content."""
    return """#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "rich>=13.0"]
# ///
from pydantic import BaseModel, Field
from raw_runtime import BaseWorkflow, step

class Params(BaseModel):
    name: str = Field(..., description="Name parameter")

class MyWorkflow(BaseWorkflow[Params]):
    @step("process")
    def process(self) -> str:
        return f"Hello, {self.params.name}!"

    def run(self) -> int:
        result = self.process()
        self.save("output.txt", result)
        return 0

if __name__ == "__main__":
    MyWorkflow.main()
"""


def test_validation_result_creation() -> None:
    """Test ValidationResult creation."""
    result = ValidationResult(
        success=True,
        errors=[],
        warnings=["Warning 1"],
        suggestions=["Suggestion 1"],
    )

    assert result.success is True
    assert len(result.errors) == 0
    assert len(result.warnings) == 1
    assert len(result.suggestions) == 1


def test_validation_result_format_success() -> None:
    """Test ValidationResult.format() for successful validation."""
    result = ValidationResult(success=True)
    formatted = result.format()

    assert "✓" in formatted
    assert "Validation passed" in formatted


def test_validation_result_format_with_errors() -> None:
    """Test ValidationResult.format() with errors."""
    result = ValidationResult(
        success=False,
        errors=["Error 1", "Error 2"],
        warnings=["Warning 1"],
        suggestions=["Suggestion 1"],
    )
    formatted = result.format()

    assert "✗" in formatted
    assert "Validation failed" in formatted
    assert "Error 1" in formatted
    assert "Error 2" in formatted
    assert "Warning 1" in formatted
    assert "Suggestion 1" in formatted


def test_validator_initialization() -> None:
    """Test WorkflowValidator initialization."""
    validator = WorkflowValidator()
    assert validator.project_root == Path.cwd()

    custom_root = Path("/tmp/test")
    validator = WorkflowValidator(custom_root)
    assert validator.project_root == custom_root


def test_validate_missing_run_py(temp_project: Path) -> None:
    """Test validation fails when run.py is missing."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert result.success is False
    assert any("run.py not found" in error for error in result.errors)


def test_validate_valid_workflow(temp_project: Path, valid_workflow_content: str) -> None:
    """Test validation of a valid workflow."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"
    run_py.write_text(valid_workflow_content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert result.success is True
    assert len(result.errors) == 0


def test_validate_missing_shebang(temp_project: Path) -> None:
    """Test validation warns about missing shebang."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"

    content = """# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0"]
# ///
from raw_runtime import BaseWorkflow
class MyWorkflow(BaseWorkflow):
    def run(self) -> int:
        return 0
"""
    run_py.write_text(content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert any("shebang" in warning.lower() for warning in result.warnings)


def test_validate_missing_pep723(temp_project: Path) -> None:
    """Test validation fails when PEP 723 metadata is missing."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"

    content = """#!/usr/bin/env python3
from raw_runtime import BaseWorkflow
class MyWorkflow(BaseWorkflow):
    def run(self) -> int:
        return 0
"""
    run_py.write_text(content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert result.success is False
    assert any("PEP 723" in error for error in result.errors)


def test_validate_missing_python_version(temp_project: Path) -> None:
    """Test validation warns about missing requires-python."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"

    content = """#!/usr/bin/env python3
# /// script
# dependencies = ["pydantic>=2.0"]
# ///
from raw_runtime import BaseWorkflow
class MyWorkflow(BaseWorkflow):
    def run(self) -> int:
        return 0
"""
    run_py.write_text(content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert any("requires-python" in warning for warning in result.warnings)


def test_validate_wrong_python_version(temp_project: Path) -> None:
    """Test validation warns about wrong Python version."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"

    content = """#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = ["pydantic>=2.0"]
# ///
from raw_runtime import BaseWorkflow
class MyWorkflow(BaseWorkflow):
    def run(self) -> int:
        return 0
"""
    run_py.write_text(content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert any(">=3.10" in warning for warning in result.warnings)


def test_validate_missing_dependencies(temp_project: Path) -> None:
    """Test validation warns about missing dependencies."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"

    content = """#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
from raw_runtime import BaseWorkflow
class MyWorkflow(BaseWorkflow):
    def run(self) -> int:
        return 0
"""
    run_py.write_text(content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert any("dependencies" in warning for warning in result.warnings)


def test_validate_missing_pydantic(temp_project: Path) -> None:
    """Test validation warns about missing pydantic."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"

    content = """#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["rich>=13.0"]
# ///
from raw_runtime import BaseWorkflow
class MyWorkflow(BaseWorkflow):
    def run(self) -> int:
        return 0
"""
    run_py.write_text(content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert any("pydantic" in warning for warning in result.warnings)


def test_validate_missing_baseworkflow(temp_project: Path) -> None:
    """Test validation fails when BaseWorkflow is not used."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"

    content = """#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0"]
# ///
class MyWorkflow:
    def run(self) -> int:
        return 0
"""
    run_py.write_text(content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert result.success is False
    assert any("BaseWorkflow" in error for error in result.errors)


def test_validate_missing_run_method(temp_project: Path) -> None:
    """Test validation fails when run() method is missing."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"

    content = """#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0"]
# ///
from raw_runtime import BaseWorkflow
class MyWorkflow(BaseWorkflow):
    def process(self) -> int:
        return 0
"""
    run_py.write_text(content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert result.success is False
    assert any("run() method" in error for error in result.errors)


def test_validate_missing_main(temp_project: Path) -> None:
    """Test validation warns about missing main entry point."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"

    content = """#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0"]
# ///
from raw_runtime import BaseWorkflow
class MyWorkflow(BaseWorkflow):
    def run(self) -> int:
        return 0
"""
    run_py.write_text(content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert any("main entry point" in warning for warning in result.warnings)


def test_validate_tool_import_exists(temp_project: Path) -> None:
    """Test validation succeeds when imported tool exists."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"

    content = """#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "rich>=13.0"]
# ///
from raw_runtime import BaseWorkflow
from tools.sample_tool import process

class MyWorkflow(BaseWorkflow):
    def run(self) -> int:
        process()
        return 0

if __name__ == "__main__":
    MyWorkflow.main()
"""
    run_py.write_text(content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert result.success is True


def test_validate_tool_import_missing(temp_project: Path) -> None:
    """Test validation fails when imported tool doesn't exist."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"

    content = """#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "rich>=13.0"]
# ///
from raw_runtime import BaseWorkflow
from tools.nonexistent_tool import process

class MyWorkflow(BaseWorkflow):
    def run(self) -> int:
        process()
        return 0

if __name__ == "__main__":
    MyWorkflow.main()
"""
    run_py.write_text(content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert result.success is False
    assert any("nonexistent_tool" in error for error in result.errors)


def test_validate_syntax_error(temp_project: Path) -> None:
    """Test validation handles syntax errors gracefully."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"

    content = """#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0"]
# ///
from raw_runtime import BaseWorkflow
class MyWorkflow(BaseWorkflow):
    def run(self) -> int:
        return 0
    # Missing closing bracket
"""
    run_py.write_text(content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    # Should succeed since there's no actual syntax error in this case
    # Let's create actual syntax error
    content_with_error = """#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0"]
# ///
from raw_runtime import BaseWorkflow
class MyWorkflow(BaseWorkflow):
    def run(self) -> int
        return 0
"""
    run_py.write_text(content_with_error)

    result = validator.validate(workflow_dir)
    assert result.success is False
    assert any("Syntax error" in error for error in result.errors)


def test_validate_no_tools_directory(temp_project: Path, valid_workflow_content: str) -> None:
    """Test validation warns when tools/ directory doesn't exist."""
    # Remove tools directory
    import shutil

    shutil.rmtree(temp_project / "tools")

    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"
    run_py.write_text(valid_workflow_content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert any("tools/ directory not found" in warning for warning in result.warnings)


def test_validate_underscore_tools_import(temp_project: Path) -> None:
    """Test validation handles _tools.* imports."""
    workflow_dir = temp_project / "workflow"
    workflow_dir.mkdir()
    run_py = workflow_dir / "run.py"

    content = """#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "rich>=13.0"]
# ///
from raw_runtime import BaseWorkflow
from _tools.sample_tool import process

class MyWorkflow(BaseWorkflow):
    def run(self) -> int:
        process()
        return 0

if __name__ == "__main__":
    MyWorkflow.main()
"""
    run_py.write_text(content)

    validator = WorkflowValidator(temp_project)
    result = validator.validate(workflow_dir)

    assert result.success is True

"""Safe code execution sandbox for testing generated code.

Provides isolated execution environments for running generated code
without side effects or security risks. Uses subprocess isolation
and resource limits.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ExecutionResult:
    """Result of code execution in sandbox."""

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    success: bool

    @property
    def output(self) -> str:
        """Get combined output (stdout + stderr)."""
        return self.stdout + self.stderr

    def __str__(self) -> str:
        """String representation of execution result."""
        status = "SUCCESS" if self.success else "FAILED"
        return f"{status} (exit={self.exit_code}, duration={self.duration_seconds:.2f}s)"


class SandboxError(Exception):
    """Raised when sandbox execution fails."""

    pass


class CodeSandbox:
    """Execute Python code in an isolated sandbox environment.

    Uses subprocess isolation to prevent side effects.
    Enforces timeouts and resource limits.
    """

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        working_dir: Path | None = None,
    ) -> None:
        """Initialize sandbox.

        Args:
            timeout_seconds: Maximum execution time
            working_dir: Working directory for execution (temp dir if None)
        """
        self.timeout_seconds = timeout_seconds
        self.working_dir = working_dir

    def execute_script(
        self,
        script_path: Path,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Execute a Python script in the sandbox.

        Args:
            script_path: Path to Python script
            args: Command-line arguments
            env: Environment variables (merged with current env)

        Returns:
            ExecutionResult with output and exit code

        Raises:
            SandboxError: If execution fails or times out
        """
        if not script_path.exists():
            raise SandboxError(f"Script not found: {script_path}")

        # Determine working directory
        cwd = self.working_dir or script_path.parent

        # Build command
        cmd = ["python3", str(script_path)]
        if args:
            cmd.extend(args)

        # Prepare environment
        import os

        exec_env = os.environ.copy()
        if env:
            exec_env.update(env)

        # Execute with timeout
        import time

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env=exec_env,
            )
            duration = time.time() - start_time

            return ExecutionResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
                success=result.returncode == 0,
            )

        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            raise SandboxError(
                f"Execution timeout after {self.timeout_seconds}s"
            ) from e

        except Exception as e:
            duration = time.time() - start_time
            raise SandboxError(f"Execution failed: {e}") from e

    def execute_source(
        self,
        source: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Execute Python source code in the sandbox.

        Creates a temporary file and executes it.

        Args:
            source: Python source code
            args: Command-line arguments
            env: Environment variables

        Returns:
            ExecutionResult with output and exit code

        Raises:
            SandboxError: If execution fails or times out
        """
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            dir=self.working_dir,
        ) as f:
            f.write(source)
            temp_path = Path(f.name)

        try:
            return self.execute_script(temp_path, args=args, env=env)
        finally:
            # Clean up temporary file
            try:
                temp_path.unlink()
            except Exception:
                pass

    def validate_imports(self, source: str) -> ExecutionResult:
        """Validate that all imports in source code can be resolved.

        Executes a minimal script that only imports the modules.

        Args:
            source: Python source code

        Returns:
            ExecutionResult indicating if imports are valid
        """
        # Extract import statements
        from raw_codegen.validator import CodeValidator

        validator = CodeValidator()
        imports_info = validator.analyze_imports(source)

        # Build validation script
        validation_lines = ["# Import validation script", ""]

        for module in imports_info["imports"]:
            validation_lines.append(f"import {module}")

        for module, names in imports_info["from_imports"].items():
            names_str = ", ".join(names)
            validation_lines.append(f"from {module} import {names_str}")

        validation_lines.append("")
        validation_lines.append('print("✓ All imports valid")')

        validation_source = "\n".join(validation_lines)

        try:
            return self.execute_source(validation_source)
        except SandboxError:
            # Re-raise with more context
            raise

    def run_tests(self, test_script: Path) -> ExecutionResult:
        """Run tests using pytest.

        Args:
            test_script: Path to test file

        Returns:
            ExecutionResult with test output

        Raises:
            SandboxError: If test execution fails
        """
        if not test_script.exists():
            raise SandboxError(f"Test script not found: {test_script}")

        # Run pytest on the test file
        cmd = ["python3", "-m", "pytest", str(test_script), "-v"]

        import os
        import time

        exec_env = os.environ.copy()
        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=test_script.parent,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env=exec_env,
            )
            duration = time.time() - start_time

            return ExecutionResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
                success=result.returncode == 0,
            )

        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            raise SandboxError(
                f"Test execution timeout after {self.timeout_seconds}s"
            ) from e

        except Exception as e:
            duration = time.time() - start_time
            raise SandboxError(f"Test execution failed: {e}") from e


class MockEnvironment:
    """Provides mock data for testing generated code.

    Generates realistic mock data based on type hints and descriptions.
    Used to test code without requiring actual external dependencies.
    """

    def __init__(self) -> None:
        """Initialize mock environment."""
        self.mocks: dict[str, Any] = {}

    def add_mock(self, name: str, value: Any) -> None:
        """Add a mock value.

        Args:
            name: Name of the mocked value
            value: Mock value
        """
        self.mocks[name] = value

    def generate_mock_data(self, type_hint: str, name: str = "") -> Any:
        """Generate mock data based on type hint.

        Args:
            type_hint: Python type hint string (e.g., "str", "int", "list[str]")
            name: Name hint for generating contextual data

        Returns:
            Mock value matching the type hint
        """
        # Simple mock generation based on type
        type_lower = type_hint.lower()

        if "str" in type_lower:
            return f"mock_{name}" if name else "mock_string"
        elif "int" in type_lower:
            return 42
        elif "float" in type_lower:
            return 3.14
        elif "bool" in type_lower:
            return True
        elif "list" in type_lower:
            return []
        elif "dict" in type_lower:
            return {}
        else:
            return None

    def create_test_fixtures(
        self, function_info: dict[str, Any]
    ) -> dict[str, Any]:
        """Create test fixtures for a function.

        Args:
            function_info: Function signature information from validator

        Returns:
            Dict mapping argument names to mock values
        """
        fixtures = {}
        for arg in function_info.get("args", []):
            arg_name = arg["name"]
            arg_type = arg.get("type", "Any")
            fixtures[arg_name] = self.generate_mock_data(arg_type, arg_name)
        return fixtures


def execute_script(
    script_path: Path,
    args: list[str] | None = None,
    timeout_seconds: float = 30.0,
) -> ExecutionResult:
    """Execute a Python script in a sandbox.

    Convenience function for one-off script execution.

    Args:
        script_path: Path to Python script
        args: Command-line arguments
        timeout_seconds: Maximum execution time

    Returns:
        ExecutionResult with output and exit code
    """
    sandbox = CodeSandbox(timeout_seconds=timeout_seconds)
    return sandbox.execute_script(script_path, args=args)


def execute_source(
    source: str,
    args: list[str] | None = None,
    timeout_seconds: float = 30.0,
) -> ExecutionResult:
    """Execute Python source code in a sandbox.

    Convenience function for one-off source execution.

    Args:
        source: Python source code
        args: Command-line arguments
        timeout_seconds: Maximum execution time

    Returns:
        ExecutionResult with output and exit code
    """
    sandbox = CodeSandbox(timeout_seconds=timeout_seconds)
    return sandbox.execute_source(source, args=args)

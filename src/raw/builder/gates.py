"""Builder quality gate runner.

Executes deterministic gates (validate, dry, pytest, ruff, etc.) and
captures results for feedback into the builder loop.
"""

import asyncio
import subprocess
import time
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

from raw.builder.config import BuilderConfig, GateCommand
from raw.discovery.workflow import find_workflow
from raw.validation.validator import WorkflowValidator


class GateResult(BaseModel):
    """Result of running a quality gate."""

    gate: str
    passed: bool
    duration_seconds: float
    output: str
    exit_code: int | None = None


class Gate(Protocol):
    """Protocol for quality gates."""

    name: str
    description: str

    async def run(self, workflow_id: str, workflow_dir: Path) -> GateResult:
        """Execute gate and return result."""
        ...


class ValidateGate:
    """Structural validation gate."""

    name = "validate"
    description = "Workflow structural validation"

    async def run(self, workflow_id: str, workflow_dir: Path) -> GateResult:
        """Run workflow validation."""
        start_time = time.time()

        try:
            validator = WorkflowValidator(project_root=Path.cwd())
            result = validator.validate(workflow_dir)

            duration = time.time() - start_time

            # Format output
            output_lines = []
            if result.success:
                output_lines.append("✓ Validation passed")
            else:
                output_lines.append("✗ Validation failed")

            if result.errors:
                output_lines.append("\nErrors:")
                for error in result.errors:
                    output_lines.append(f"  • {error}")

            if result.warnings:
                output_lines.append("\nWarnings:")
                for warning in result.warnings:
                    output_lines.append(f"  • {warning}")

            output = "\n".join(output_lines)

            return GateResult(
                gate=self.name,
                passed=result.success,
                duration_seconds=duration,
                output=output,
                exit_code=0 if result.success else 1,
            )

        except Exception as e:
            duration = time.time() - start_time
            return GateResult(
                gate=self.name,
                passed=False,
                duration_seconds=duration,
                output=f"Error running validation: {e}",
                exit_code=1,
            )


class DryRunGate:
    """Dry run gate - executes workflow with --dry flag."""

    name = "dry"
    description = "Dry run with mock data"

    async def run(self, workflow_id: str, workflow_dir: Path) -> GateResult:
        """Run workflow with --dry flag."""
        start_time = time.time()

        try:
            # Check if dry_run.py exists
            dry_run_file = workflow_dir / "dry_run.py"
            if not dry_run_file.exists():
                duration = time.time() - start_time
                return GateResult(
                    gate=self.name,
                    passed=False,
                    duration_seconds=duration,
                    output="dry_run.py not found. Run 'raw run --dry --init' to generate template.",
                    exit_code=1,
                )

            # Execute dry run
            process = await asyncio.create_subprocess_exec(
                "raw",
                "run",
                workflow_id,
                "--dry",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path.cwd(),
            )

            stdout, stderr = await process.communicate()

            duration = time.time() - start_time

            # Combine output
            output = stdout.decode() + stderr.decode()

            return GateResult(
                gate=self.name,
                passed=process.returncode == 0,
                duration_seconds=duration,
                output=output,
                exit_code=process.returncode,
            )

        except Exception as e:
            duration = time.time() - start_time
            return GateResult(
                gate=self.name,
                passed=False,
                duration_seconds=duration,
                output=f"Error running dry run: {e}",
                exit_code=1,
            )


class CommandGate:
    """Custom command gate (pytest, ruff, etc.)."""

    def __init__(self, name: str, command_config: GateCommand):
        """Initialize command gate.

        Args:
            name: Gate name
            command_config: Command configuration
        """
        self.name = name
        self.description = f"Custom command: {command_config.command}"
        self._command = command_config.command
        self._timeout = command_config.timeout_seconds

    async def run(self, workflow_id: str, workflow_dir: Path) -> GateResult:
        """Run custom command."""
        start_time = time.time()

        try:
            # Execute command
            process = await asyncio.create_subprocess_shell(
                self._command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path.cwd(),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self._timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                duration = time.time() - start_time
                return GateResult(
                    gate=self.name,
                    passed=False,
                    duration_seconds=duration,
                    output=f"Command timed out after {self._timeout} seconds",
                    exit_code=124,
                )

            duration = time.time() - start_time

            # Combine output
            output = stdout.decode() + stderr.decode()

            return GateResult(
                gate=self.name,
                passed=process.returncode == 0,
                duration_seconds=duration,
                output=output,
                exit_code=process.returncode,
            )

        except Exception as e:
            duration = time.time() - start_time
            return GateResult(
                gate=self.name,
                passed=False,
                duration_seconds=duration,
                output=f"Error running command: {e}",
                exit_code=1,
            )


async def run_gates(
    workflow_id: str,
    config: BuilderConfig,
    workflow_dir: Path | None = None,
    journal: "BuilderJournal | None" = None,
    build_id: str | None = None,
    iteration: int | None = None,
) -> list[GateResult]:
    """Run all configured gates for a workflow.

    Args:
        workflow_id: Workflow to validate
        config: Builder configuration with gates
        workflow_dir: Workflow directory (resolved if None)
        journal: Optional journal for event logging
        build_id: Build ID (required if journal provided)
        iteration: Iteration number (required if journal provided)

    Returns:
        List of gate results

    Example:
        config = load_builder_config()
        results = await run_gates("my-workflow", config)
        for result in results:
            print(f"{result.gate}: {'PASS' if result.passed else 'FAIL'}")
    """
    # Resolve workflow directory
    if workflow_dir is None:
        workflow_dir = find_workflow(workflow_id)
        if not workflow_dir:
            raise ValueError(f"Workflow not found: {workflow_id}")

    results: list[GateResult] = []

    # Build gate list
    gates: list[Gate] = []

    # Default gates
    if "validate" in config.gates.default:
        gates.append(ValidateGate())

    if "dry" in config.gates.default:
        gates.append(DryRunGate())

    # Optional gates
    for gate_name, gate_config in config.gates.optional.items():
        gates.append(CommandGate(gate_name, gate_config))

    # Run gates sequentially (could be parallelized in future)
    for gate in gates:
        # Write started event if journal provided
        if journal and build_id and iteration is not None:
            from raw.builder.events import GateStartedEvent

            journal.write(
                GateStartedEvent(
                    build_id=build_id,
                    iteration=iteration,
                    gate=gate.name,
                )
            )

        result = await gate.run(workflow_id, workflow_dir)
        results.append(result)

        # Write completed event if journal provided
        if journal and build_id and iteration is not None:
            from raw.builder.events import GateCompletedEvent

            journal.write(
                GateCompletedEvent(
                    build_id=build_id,
                    iteration=iteration,
                    gate=result.gate,
                    passed=result.passed,
                    duration_seconds=result.duration_seconds,
                    output_path=str(save_gate_output(result, journal.build_dir)),
                )
            )

    return results


def save_gate_output(result: GateResult, build_dir: Path) -> Path:
    """Save gate output to log file.

    Args:
        result: Gate result with output
        build_dir: Build directory (e.g., .raw/builds/<build_id>)

    Returns:
        Path to saved log file
    """
    logs_dir = build_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    log_path = logs_dir / f"{result.gate}.log"
    log_path.write_text(result.output)

    return log_path


def format_gate_failures(results: list[GateResult]) -> str:
    """Format gate failures for feedback into plan mode.

    Args:
        results: List of gate results

    Returns:
        Formatted string describing failures

    Example:
        failures = format_gate_failures(results)
        # "Gates failed: validate (2 errors), dry (exit code 1)"
    """
    failures = [r for r in results if not r.passed]

    if not failures:
        return "All gates passed"

    failure_descriptions = []
    for result in failures:
        desc = result.gate

        # Extract key failure info
        if "error" in result.output.lower():
            # Count errors
            error_count = result.output.lower().count("error")
            desc += f" ({error_count} errors)"
        elif result.exit_code and result.exit_code != 0:
            desc += f" (exit code {result.exit_code})"

        failure_descriptions.append(desc)

    return "Gates failed: " + ", ".join(failure_descriptions)

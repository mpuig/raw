"""Workflow execution via uv run."""

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

# Default timeout for dry runs (mock data should execute quickly)
DRY_RUN_TIMEOUT_SECONDS = 60


def create_run_directory(workflow_dir: Path) -> Path:
    """Create a timestamped run directory for workflow execution.

    Returns path like: workflow_dir/runs/20251207-215930/
    """
    runs_dir = workflow_dir / "runs"
    runs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = runs_dir / timestamp
    run_dir.mkdir(exist_ok=True)

    (run_dir / "results").mkdir(exist_ok=True)

    return run_dir


def save_run_manifest(
    run_dir: Path,
    workflow_id: str,
    exit_code: int,
    duration_seconds: float,
    args: list[str],
) -> None:
    """Save execution manifest to run directory."""
    manifest = {
        "workflow_id": workflow_id,
        "run_id": run_dir.name,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": exit_code,
        "duration_seconds": duration_seconds,
        "args": args,
        "status": "success" if exit_code == 0 else "failed",
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))


def parse_pep723_dependencies(script_path: Path) -> list[str]:
    """Parse PEP 723 inline script dependencies.

    Extracts dependencies from the script metadata block:
    # /// script
    # dependencies = ["pandas>=2.0", "yfinance"]
    # ///

    Returns:
        List of dependency strings (e.g., ["pandas>=2.0", "yfinance"])
    """
    try:
        content = script_path.read_text()
    except OSError:
        return []

    pattern = r"# /// script\s*\n(.*?)# ///"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return []

    metadata_block = match.group(1)

    deps_pattern = r"#\s*dependencies\s*=\s*\[(.*?)\]"
    deps_match = re.search(deps_pattern, metadata_block, re.DOTALL)
    if not deps_match:
        return []

    deps_content = deps_match.group(1)

    dep_strings = re.findall(r'"([^"]+)"', deps_content)

    # Filter out pydantic and rich (already in raw_runtime)
    filtered = [d for d in dep_strings if not d.startswith(("pydantic", "rich"))]

    return filtered


@dataclass
class RunResult:
    """Result of a workflow execution."""

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False


class ExecutionBackend(Protocol):
    """Protocol for execution backends."""

    def run(
        self,
        script_path: Path,
        args: list[str],
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> RunResult:
        """Execute a script and return the result."""
        ...


class SubprocessBackend:
    """Execute workflows via uv run subprocess."""

    def run(
        self,
        script_path: Path,
        args: list[str],
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> RunResult:
        """Execute a script via uv run.

        Uses uv run to execute PEP 723 scripts with inline dependencies.
        Parses dependencies from the script and adds them via --with flags.

        Args:
            script_path: Path to the Python script
            args: Arguments to pass to the script
            cwd: Working directory for execution
            timeout: Maximum execution time in seconds (None for no limit)

        Returns:
            RunResult with exit code, output, and timing
        """
        start_time = datetime.now(timezone.utc)

        # Parse PEP 723 dependencies from the script
        deps = parse_pep723_dependencies(script_path)

        # Build command: uv run [--with dep1 --with dep2 ...] python script.py
        cmd = ["uv", "run"]
        for dep in deps:
            cmd.extend(["--with", dep])
        cmd.extend(["python", str(script_path)] + args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
            )

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            return RunResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
            )
        except subprocess.TimeoutExpired as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            # e.stdout is str when text=True, bytes otherwise
            stdout = e.stdout if isinstance(e.stdout, str) else (e.stdout.decode() if e.stdout else "")
            return RunResult(
                exit_code=124,  # Standard timeout exit code
                stdout=stdout,
                stderr=f"Timeout: execution exceeded {timeout}s limit",
                duration_seconds=duration,
                timed_out=True,
            )


# Default backend
default_backend = SubprocessBackend()


def verify_tool_hashes(workflow_dir: Path) -> list[str]:
    """Verify tool hashes for a published workflow.

    Returns list of warnings for tools with mismatched hashes.
    """
    from raw.discovery.workflow import load_workflow_config  # type: ignore[attr-defined]
    from raw.scaffold.init import calculate_tool_hash, get_tools_dir

    warnings: list[str] = []
    config = load_workflow_config(workflow_dir)
    if not config:
        return warnings

    # Only verify published workflows with pinned hashes
    if config.status != "published":
        return warnings

    tools_dir = get_tools_dir()
    for step in config.steps:
        if step.tool_hash:
            tool_dir = tools_dir / step.tool
            if tool_dir.exists():
                current_hash = calculate_tool_hash(tool_dir)
                if current_hash != step.tool_hash:
                    warnings.append(
                        f"Tool '{step.tool}' has been modified since workflow was published "
                        f"(expected hash: {step.tool_hash[:12]}..., current: {current_hash[:12]}...)"
                    )

    return warnings


def run_workflow(
    workflow_dir: Path,
    script_name: str = "run.py",
    args: list[str] | None = None,
    backend: ExecutionBackend | None = None,
    timeout: float | None = None,
    isolate_run: bool = True,
) -> RunResult:
    """Run a workflow script.

    Args:
        workflow_dir: Path to workflow directory
        script_name: Name of script to run (run.py, dry_run.py)
        args: Arguments to pass to the script
        backend: Execution backend to use
        timeout: Maximum execution time in seconds (None for no limit)
        isolate_run: Create timestamped run directory for outputs

    Returns:
        RunResult with execution details
    """
    from raw.discovery.workflow import snapshot_tools
    from raw.scaffold.init import load_workflow_config

    if backend is None:
        backend = default_backend

    if args is None:
        args = []

    script_path = workflow_dir / script_name

    if not script_path.exists():
        return RunResult(
            exit_code=1,
            stdout="",
            stderr=f"Script not found: {script_path}",
            duration_seconds=0.0,
        )

    # Snapshot tools for unpublished workflows (tools are already frozen for published)
    config = load_workflow_config(workflow_dir)
    if config and config.status != "published":
        snapshot_tools(workflow_dir)

    hash_warnings = verify_tool_hashes(workflow_dir)
    stderr_prefix = ""
    if hash_warnings:
        stderr_prefix = (
            "⚠ Tool hash warnings:\n" + "\n".join(f"  - {w}" for w in hash_warnings) + "\n\n"
        )

    if isolate_run:
        run_dir = create_run_directory(workflow_dir)
    else:
        run_dir = workflow_dir

    result = backend.run(script_path, args, cwd=run_dir, timeout=timeout)

    if isolate_run:
        output_log = f"=== STDOUT ===\n{result.stdout}\n\n=== STDERR ===\n{result.stderr}"
        (run_dir / "output.log").write_text(output_log)

        save_run_manifest(
            run_dir=run_dir,
            workflow_id=workflow_dir.name,
            exit_code=result.exit_code,
            duration_seconds=result.duration_seconds,
            args=args,
        )

    if stderr_prefix:
        return RunResult(
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=stderr_prefix + result.stderr,
            duration_seconds=result.duration_seconds,
            timed_out=result.timed_out,
        )

    return result


def run_dry(
    workflow_dir: Path,
    args: list[str] | None = None,
    backend: ExecutionBackend | None = None,
    timeout: float | None = None,
) -> RunResult:
    """Run a workflow in dry-run mode with mock data.

    Dry runs execute dry_run.py with a default timeout and validate
    that the mocks/ directory exists. Dry runs do not create isolated
    run directories since they are for testing purposes.

    Args:
        workflow_dir: Path to workflow directory
        args: Arguments to pass to the script
        backend: Execution backend to use
        timeout: Maximum execution time (defaults to DRY_RUN_TIMEOUT_SECONDS)

    Returns:
        RunResult with execution details
    """
    mocks_dir = workflow_dir / "mocks"
    mocks_warning = ""
    if not mocks_dir.exists():
        mocks_warning = "Warning: mocks/ directory not found. Dry runs should use mock data.\n"

    if timeout is None:
        timeout = DRY_RUN_TIMEOUT_SECONDS

    result = run_workflow(
        workflow_dir=workflow_dir,
        script_name="dry_run.py",
        args=args,
        backend=backend,
        timeout=timeout,
        isolate_run=False,  # Dry runs don't need isolated directories
    )

    if mocks_warning and result.exit_code == 0:
        return RunResult(
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=mocks_warning + result.stderr,
            duration_seconds=result.duration_seconds,
            timed_out=result.timed_out,
        )

    return result

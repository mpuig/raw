"""Execution backend implementations.

Concrete implementations of ExecutionBackend and RunStorage protocols.
"""

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from raw.engine.protocols import ExecutionBackend, RunResult, RunStorage


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

    # PEP 723 defines a standard format for inline script metadata.
    # We use regex rather than a TOML parser because the metadata is
    # embedded in Python comments, not a standalone TOML file.
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

    # Filter out pydantic and rich because raw_runtime already provides them.
    # Including them would cause version conflicts and slow down execution
    # as uv would need to resolve potentially incompatible versions.
    filtered = [d for d in dep_strings if not d.startswith(("pydantic", "rich"))]

    return filtered


class SubprocessBackend(ExecutionBackend):
    """Execute workflows via uv run subprocess.

    Uses uv run to execute PEP 723 scripts with inline dependencies.
    Parses dependencies from the script and adds them via --with flags.
    """

    def run(
        self,
        script_path: Path,
        args: list[str],
        cwd: Path | None = None,
        timeout: float | None = None,
    ) -> RunResult:
        """Execute a script via uv run."""
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
            # TimeoutExpired.stdout can be str (text=True) or bytes (text=False).
            # We always run with text=True, but handle bytes defensively in case
            # the behavior changes or we're mocked in tests.
            stdout = e.stdout if isinstance(e.stdout, str) else (e.stdout.decode() if e.stdout else "")
            return RunResult(
                # Exit code 124 is the Unix standard for timeout (used by GNU timeout).
                # This allows callers to distinguish timeouts from other failures.
                exit_code=124,
                stdout=stdout,
                stderr=f"Timeout: execution exceeded {timeout}s limit",
                duration_seconds=duration,
                timed_out=True,
            )


class LocalRunStorage(RunStorage):
    """Local filesystem storage for run directories and manifests."""

    def create_run_directory(self, workflow_dir: Path) -> Path:
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

    def save_manifest(
        self,
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

    def save_output_log(self, run_dir: Path, stdout: str, stderr: str) -> None:
        """Save execution output to log file."""
        output_log = f"=== STDOUT ===\n{stdout}\n\n=== STDERR ===\n{stderr}"
        (run_dir / "output.log").write_text(output_log)

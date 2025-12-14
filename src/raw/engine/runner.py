"""Workflow runner with dependency injection.

WorkflowRunner encapsulates workflow execution with injected dependencies
for execution backend and run storage, following clean architecture principles.
"""

from pathlib import Path

from raw.engine.protocols import ExecutionBackend, RunResult, RunStorage


# Default timeout for dry runs (mock data should execute quickly)
DRY_RUN_TIMEOUT_SECONDS = 60


class WorkflowRunner:
    """Executes workflows with injected dependencies.

    Separates execution orchestration from:
    - Backend execution (subprocess, docker, k8s)
    - Storage management (local, S3, etc.)

    This enables testing and alternative deployment strategies.
    """

    def __init__(
        self,
        backend: ExecutionBackend,
        storage: RunStorage,
    ) -> None:
        """Initialize runner with dependencies.

        Args:
            backend: Execution backend for running scripts
            storage: Storage backend for run directories and manifests
        """
        self._backend = backend
        self._storage = storage

    def run(
        self,
        workflow_dir: Path,
        script_name: str = "run.py",
        args: list[str] | None = None,
        timeout: float | None = None,
        isolate_run: bool = True,
    ) -> RunResult:
        """Run a workflow script.

        Args:
            workflow_dir: Path to workflow directory
            script_name: Name of script to run (run.py, dry_run.py)
            args: Arguments to pass to the script
            timeout: Maximum execution time in seconds (None for no limit)
            isolate_run: Create timestamped run directory for outputs

        Returns:
            RunResult with execution details
        """
        from raw.discovery.workflow import snapshot_tools
        from raw.scaffold.init import load_workflow_config

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

        # Snapshot tools for unpublished workflows
        config = load_workflow_config(workflow_dir)
        if config and config.status != "published":
            snapshot_tools(workflow_dir)

        hash_warnings = self._verify_tool_hashes(workflow_dir)
        stderr_prefix = ""
        if hash_warnings:
            stderr_prefix = (
                "⚠ Tool hash warnings:\n" + "\n".join(f"  - {w}" for w in hash_warnings) + "\n\n"
            )

        if isolate_run:
            run_dir = self._storage.create_run_directory(workflow_dir)
        else:
            run_dir = workflow_dir

        result = self._backend.run(script_path, args, cwd=run_dir, timeout=timeout)

        if isolate_run:
            self._storage.save_output_log(run_dir, result.stdout, result.stderr)
            self._storage.save_manifest(
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
        self,
        workflow_dir: Path,
        args: list[str] | None = None,
        timeout: float | None = None,
    ) -> RunResult:
        """Run a workflow in dry-run mode with mock data.

        Dry runs execute dry_run.py with a default timeout and validate
        that the mocks/ directory exists. Dry runs do not create isolated
        run directories since they are for testing purposes.

        Args:
            workflow_dir: Path to workflow directory
            args: Arguments to pass to the script
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

        result = self.run(
            workflow_dir=workflow_dir,
            script_name="dry_run.py",
            args=args,
            timeout=timeout,
            isolate_run=False,
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

    def _verify_tool_hashes(self, workflow_dir: Path) -> list[str]:
        """Verify tool hashes for a published workflow.

        Returns list of warnings for tools with mismatched hashes.
        """
        from raw.discovery.workflow import load_workflow_config
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

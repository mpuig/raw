"""FastAPI server for RAW daemon mode.

Provides HTTP API for:
- Triggering workflows via webhooks
- Human-in-the-loop approvals via connected workflows
- Real-time run status and dashboard
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from raw.discovery.workflow import find_workflow, list_workflows
from raw.engine.server_dashboard import (
    build_approvals_html,
    build_runs_html,
    build_workflows_html,
)
from raw.engine.server_models import (
    ApprovalRequest,
    CompleteRequest,
    Event,
    RegisterRequest,
    WaitingRequest,
    WorkflowRun,
    WorkflowTriggerRequest,
)
from raw.engine.server_registry import RunRegistry


class RAWServer:
    """RAW daemon server managing workflow execution and approvals."""

    def __init__(self) -> None:
        from raw_runtime.bus import ApprovalRegistry, AsyncEventBus

        self.event_bus = AsyncEventBus()
        self.approval_registry = ApprovalRegistry()  # Legacy, kept for compatibility
        self.run_registry = RunRegistry()  # New connected workflow registry
        self.active_runs: dict[str, WorkflowRun] = {}  # Legacy subprocess runs
        self._bus_task: asyncio.Task[None] | None = None
        self._stale_checker_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the event bus and background tasks."""
        self._bus_task = asyncio.create_task(self.event_bus.start())
        self._stale_checker_task = asyncio.create_task(self._check_stale_runs())

    async def stop(self) -> None:
        """Stop all background tasks."""
        if self._stale_checker_task:
            self._stale_checker_task.cancel()
            try:
                await self._stale_checker_task
            except asyncio.CancelledError:
                pass
        await self.event_bus.stop()
        if self._bus_task:
            await self._bus_task

    async def _check_stale_runs(self) -> None:
        """Background task to detect stale runs (no heartbeat for 60s)."""
        while True:
            await asyncio.sleep(30)
            now = datetime.now(timezone.utc)
            for run in self.run_registry.list_runs():
                if run.status in ("running", "waiting"):
                    elapsed = (now - run.last_heartbeat).total_seconds()
                    if elapsed > 60:
                        run.status = "stale"

    async def trigger_workflow(
        self,
        workflow_id: str,
        args: list[str] | None = None,
    ) -> dict[str, Any]:
        """Trigger a workflow execution in the background.

        Returns run metadata immediately; workflow executes asynchronously.
        The spawned workflow will connect back via RAW_SERVER_URL.
        """
        workflow_dir = find_workflow(workflow_id)
        if not workflow_dir:
            raise ValueError(f"Workflow not found: {workflow_id}")

        import uuid
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
        run_py = workflow_dir / "run.py"

        if not run_py.exists():
            raise ValueError(f"Workflow has no run.py: {workflow_id}")

        # Pass server URL to subprocess so it can connect back
        import os

        env = os.environ.copy()
        env["RAW_SERVER_URL"] = f"http://127.0.0.1:{os.environ.get('RAW_PORT', '8000')}"

        cmd = ["uv", "run", "python", str(run_py)] + (args or [])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=workflow_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        run = WorkflowRun(
            workflow_id=workflow_id,
            run_id=run_id,
            started_at=datetime.now(timezone.utc),
            process=process,
        )
        self.active_runs[f"{workflow_id}:{run_id}"] = run

        asyncio.create_task(self._monitor_run(run))

        return {
            "workflow_id": workflow_id,
            "run_id": run_id,
            "status": "started",
            "message": f"Workflow {workflow_id} triggered",
        }

    async def _monitor_run(self, run: WorkflowRun) -> None:
        """Monitor a running workflow and update status on completion."""
        if run.process is None:
            return

        await run.process.wait()
        run.status = "success" if run.process.returncode == 0 else "failed"
        run.process = None


# Template directory
TEMPLATES_DIR = Path(__file__).parent / "templates"


def _get_jinja_env() -> Environment:
    """Get Jinja2 environment for server templates."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )


def create_app(server: RAWServer | None = None) -> Any:
    """Create FastAPI application for RAW server."""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import HTMLResponse
    except ImportError as e:
        raise ImportError("FastAPI not installed. Install with: uv add raw[serve]") from e

    if server is None:
        server = RAWServer()

    app = FastAPI(
        title="RAW Server",
        description="Run Agentic Workflows - Daemon Mode",
        version="0.2.0",
    )

    @app.on_event("startup")
    async def startup() -> None:
        await server.start()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await server.stop()

    # --- Dashboard ---

    @app.get("/", response_class=HTMLResponse)
    async def dashboard() -> str:
        """HTML dashboard showing runs, approvals, and workflows."""
        # Collect approval data
        approvals = []
        for run_id, waiting in server.run_registry.list_waiting():
            if waiting.event_type == "approval":
                run = server.run_registry.get(run_id)
                approvals.append({
                    "run_id": run_id,
                    "workflow_id": run.workflow_id if run else "unknown",
                    "step_name": waiting.step_name,
                    "prompt": waiting.prompt or "Approval required",
                    "options": waiting.options or ["approve", "reject"],
                    "context": waiting.context,
                })

        # Collect run data (connected + legacy)
        all_runs = []
        for r in server.run_registry.list_runs():
            all_runs.append({
                "id": r.run_id,
                "wf": r.workflow_id,
                "status": r.status,
                "time": r.registered_at.strftime("%H:%M:%S"),
                "mode": "connected",
            })
        for r in server.active_runs.values():
            all_runs.append({
                "id": r.run_id,
                "wf": r.workflow_id,
                "status": r.status,
                "time": r.started_at.strftime("%H:%M:%S"),
                "mode": "subprocess",
            })

        workflows = list_workflows()

        # Render dashboard template
        env = _get_jinja_env()
        template = env.get_template("dashboard.html")
        return template.render(
            approval_count=len(approvals),
            approvals_html=build_approvals_html(approvals),
            run_count=len(all_runs),
            runs_html=build_runs_html(all_runs),
            workflow_count=len(workflows),
            workflows_html=build_workflows_html(workflows),
        )

    @app.get("/api/status")
    async def api_status() -> dict[str, Any]:
        """JSON health check endpoint."""
        connected = server.run_registry.list_runs()
        waiting = [r for r in connected if r.status == "waiting"]
        return {
            "status": "ok",
            "service": "raw-server",
            "connected_runs": len(connected),
            "waiting_approvals": len(waiting),
            "legacy_runs": len(server.active_runs),
        }

    @app.get("/workflows")
    async def get_workflows() -> list[dict[str, Any]]:
        """List all workflows."""
        return list_workflows()

    # --- Connected Workflow Endpoints ---

    @app.post("/runs/register")
    async def register_run(request: RegisterRequest) -> dict[str, Any]:
        """Register a connected workflow run."""
        run = server.run_registry.register(
            run_id=request.run_id,
            workflow_id=request.workflow_id,
            pid=request.pid,
        )
        return {
            "status": "registered",
            "run_id": run.run_id,
            "server_time": datetime.now(timezone.utc).isoformat(),
        }

    @app.post("/runs/{run_id}/waiting")
    async def mark_waiting(run_id: str, request: WaitingRequest) -> dict[str, Any]:
        """Mark a run as waiting for an event."""
        run = server.run_registry.get(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

        server.run_registry.mark_waiting(
            run_id=run_id,
            event_type=request.event_type,
            step_name=request.step_name,
            prompt=request.prompt,
            options=request.options,
            context=request.context,
            timeout_seconds=request.timeout_seconds,
        )
        return {"status": "waiting", "run_id": run_id, "step_name": request.step_name}

    @app.get("/runs/{run_id}/events")
    async def poll_events(run_id: str) -> list[dict[str, Any]]:
        """Poll for pending events (returns and clears queue)."""
        run = server.run_registry.get(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

        events = server.run_registry.pop_events(run_id)
        return [e.model_dump() for e in events]

    @app.post("/runs/{run_id}/heartbeat")
    async def heartbeat(run_id: str) -> dict[str, Any]:
        """Keep-alive signal from a connected run."""
        if not server.run_registry.heartbeat(run_id):
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        return {"status": "ok"}

    @app.post("/runs/{run_id}/complete")
    async def complete_run(run_id: str, request: CompleteRequest) -> dict[str, Any]:
        """Mark a run as completed and cleanup."""
        run = server.run_registry.get(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

        server.run_registry.complete(run_id, request.status)
        return {"status": request.status, "run_id": run_id}

    @app.post("/runs/{run_id}/cancel")
    async def cancel_run(run_id: str) -> dict[str, Any]:
        """Cancel a running workflow."""
        import os
        import signal

        # Check connected runs first
        run = server.run_registry.get(run_id)
        if run:
            if run.status in ("completed", "failed"):
                raise HTTPException(
                    status_code=400, detail=f"Run already {run.status}: {run_id}"
                )
            # Try to kill the process
            try:
                os.kill(run.pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass  # Process may already be dead
            server.run_registry.complete(run_id, "failed")
            return {"status": "cancelled", "run_id": run_id}

        # Check legacy subprocess runs
        for key, legacy_run in list(server.active_runs.items()):
            if legacy_run.run_id == run_id:
                if legacy_run.process:
                    legacy_run.process.terminate()
                legacy_run.status = "cancelled"
                return {"status": "cancelled", "run_id": run_id}

        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    # --- Active Runs ---

    @app.get("/runs")
    async def get_runs() -> list[dict[str, Any]]:
        """List all runs (connected + legacy subprocess)."""
        runs = []

        # Connected runs
        for run in server.run_registry.list_runs():
            runs.append(
                {
                    "run_id": run.run_id,
                    "workflow_id": run.workflow_id,
                    "status": run.status,
                    "registered_at": run.registered_at.isoformat(),
                    "last_heartbeat": run.last_heartbeat.isoformat(),
                    "waiting_for": run.waiting_for.model_dump() if run.waiting_for else None,
                    "mode": "connected",
                }
            )

        # Legacy subprocess runs
        for key, run in server.active_runs.items():
            runs.append(
                {
                    "run_id": run.run_id,
                    "workflow_id": run.workflow_id,
                    "status": run.status,
                    "started_at": run.started_at.isoformat(),
                    "mode": "subprocess",
                }
            )

        return runs

    # --- Approvals ---

    @app.get("/approvals")
    async def get_pending_approvals() -> list[dict[str, Any]]:
        """List all pending approval requests."""
        approvals = []

        # From connected runs
        for run_id, waiting in server.run_registry.list_waiting():
            if waiting.event_type == "approval":
                run = server.run_registry.get(run_id)
                approvals.append(
                    {
                        "run_id": run_id,
                        "workflow_id": run.workflow_id if run else "unknown",
                        "step_name": waiting.step_name,
                        "prompt": waiting.prompt,
                        "options": waiting.options,
                        "context": waiting.context,
                        "timeout_at": waiting.timeout_at.isoformat(),
                    }
                )

        return approvals

    @app.post("/approve/{run_id}/{step_name}")
    async def approve_step(
        run_id: str,
        step_name: str,
        request: ApprovalRequest | None = None,
    ) -> dict[str, Any]:
        """Approve or reject a pending step."""
        decision = request.decision if request else "approve"

        # Check if run exists and is waiting
        run = server.run_registry.get(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

        if not run.waiting_for or run.waiting_for.step_name != step_name:
            raise HTTPException(
                status_code=404,
                detail=f"No pending approval for {run_id}:{step_name}",
            )

        # Push approval event to the run's queue
        event = Event(
            event_type="approval",
            step_name=step_name,
            payload={"decision": decision},
        )
        server.run_registry.push_event(run_id, event)

        # Clear waiting state
        run.status = "running"
        run.waiting_for = None

        return {
            "run_id": run_id,
            "step_name": step_name,
            "decision": decision,
            "status": "delivered",
        }

    # --- Webhook Triggers ---

    @app.post("/webhook/{workflow_id}")
    async def trigger_webhook(
        workflow_id: str,
        request: WorkflowTriggerRequest | None = None,
    ) -> dict[str, Any]:
        """Trigger a workflow via webhook."""
        try:
            args = request.args if request else []
            result = await server.trigger_workflow(workflow_id, args)
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/send/{run_id}/{step_name}")
    async def send_webhook_data(
        run_id: str,
        step_name: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send webhook data to a waiting workflow run.

        Use this to deliver external data to a workflow that called wait_for_webhook().
        """
        run = server.run_registry.get(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

        if not run.waiting_for or run.waiting_for.step_name != step_name:
            raise HTTPException(
                status_code=404,
                detail=f"Run {run_id} is not waiting for webhook at step: {step_name}",
            )

        if run.waiting_for.event_type != "webhook":
            raise HTTPException(
                status_code=400,
                detail=f"Run {run_id} is waiting for {run.waiting_for.event_type}, not webhook",
            )

        event = Event(
            event_type="webhook",
            step_name=step_name,
            payload=payload or {},
        )
        server.run_registry.push_event(run_id, event)

        run.status = "running"
        run.waiting_for = None

        return {
            "run_id": run_id,
            "step_name": step_name,
            "status": "delivered",
            "payload_keys": list((payload or {}).keys()),
        }

    return app


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the RAW server with uvicorn."""
    import logging
    import os

    try:
        import uvicorn
    except ImportError as e:
        raise ImportError("uvicorn not installed. Install with: uv add raw[serve]") from e

    # Store port for subprocess env injection
    os.environ["RAW_PORT"] = str(port)

    # Filter out noisy polling endpoints from access logs
    class QuietAccessFilter(logging.Filter):
        """Filter out repetitive polling requests from logs."""

        QUIET_PATHS = {"/events", "/heartbeat", "/?"}

        def filter(self, record: logging.LogRecord) -> bool:
            msg = record.getMessage()
            return not any(path in msg for path in self.QUIET_PATHS)

    logging.getLogger("uvicorn.access").addFilter(QuietAccessFilter())

    app = create_app()
    uvicorn.run(app, host=host, port=port)

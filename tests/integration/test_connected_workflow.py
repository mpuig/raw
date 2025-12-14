"""Integration tests for connected workflow mode.

These tests verify the server ↔ workflow communication:
1. Workflow registers with server on startup
2. Workflow polls server for approval events
3. Server delivers approvals to waiting workflows
"""

import os
import subprocess
import sys
import time

import httpx
import pytest

# Skip if FastAPI not available
pytest.importorskip("fastapi")
pytest.importorskip("uvicorn")


# free_port fixture is provided by tests/conftest.py


@pytest.fixture
def raw_server(free_port, tmp_path):
    """Start RAW server in background."""
    # Create minimal .raw structure
    raw_dir = tmp_path / ".raw"
    raw_dir.mkdir()
    (raw_dir / "config.yaml").write_text("version: 1\n")
    (raw_dir / "workflows").mkdir()

    env = os.environ.copy()
    env["RAW_PORT"] = str(free_port)

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "raw.engine.server:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(free_port),
        ],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start (use /api/status for JSON response)
    base_url = f"http://127.0.0.1:{free_port}"
    for _ in range(30):
        try:
            resp = httpx.get(f"{base_url}/api/status", timeout=1.0)
            if resp.status_code == 200:
                break
        except httpx.RequestError:
            pass
        time.sleep(0.1)
    else:
        proc.terminate()
        stdout, stderr = proc.communicate()
        print(f"Server stdout: {stdout.decode()}")
        print(f"Server stderr: {stderr.decode()}")
        pytest.fail("Server failed to start")

    yield base_url

    proc.terminate()
    proc.wait(timeout=5)


class TestRunRegistry:
    """Test server-side run registry endpoints."""

    def test_register_run(self, raw_server):
        """Workflow can register with server."""
        client = httpx.Client(base_url=raw_server)

        resp = client.post(
            "/runs/register",
            json={
                "run_id": "test-run-123",
                "workflow_id": "test-workflow",
                "pid": 12345,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "registered"
        assert data["run_id"] == "test-run-123"

    def test_waiting_and_poll(self, raw_server):
        """Workflow can mark waiting and poll for events."""
        client = httpx.Client(base_url=raw_server)

        # Register
        client.post(
            "/runs/register",
            json={
                "run_id": "test-run-456",
                "workflow_id": "test-workflow",
                "pid": 12345,
            },
        )

        # Mark waiting
        resp = client.post(
            "/runs/test-run-456/waiting",
            json={
                "event_type": "approval",
                "step_name": "deploy",
                "prompt": "Deploy to prod?",
                "options": ["approve", "reject"],
            },
        )
        assert resp.status_code == 200

        # Check approvals list
        resp = client.get("/approvals")
        assert resp.status_code == 200
        approvals = resp.json()
        assert len(approvals) == 1
        assert approvals[0]["step_name"] == "deploy"

        # Poll events (empty initially)
        resp = client.get("/runs/test-run-456/events")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_approval_delivery(self, raw_server):
        """Approval is delivered to waiting workflow."""
        client = httpx.Client(base_url=raw_server)

        # Register and wait
        client.post(
            "/runs/register",
            json={
                "run_id": "test-run-789",
                "workflow_id": "test-workflow",
                "pid": 12345,
            },
        )
        client.post(
            "/runs/test-run-789/waiting",
            json={
                "event_type": "approval",
                "step_name": "review",
            },
        )

        # Send approval
        resp = client.post(
            "/approve/test-run-789/review",
            json={
                "decision": "approve",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "delivered"

        # Poll should return the event
        resp = client.get("/runs/test-run-789/events")
        events = resp.json()
        assert len(events) == 1
        assert events[0]["event_type"] == "approval"
        assert events[0]["payload"]["decision"] == "approve"

        # Second poll should be empty (events consumed)
        resp = client.get("/runs/test-run-789/events")
        assert resp.json() == []

    def test_heartbeat(self, raw_server):
        """Heartbeat updates last_heartbeat timestamp."""
        client = httpx.Client(base_url=raw_server)

        client.post(
            "/runs/register",
            json={
                "run_id": "test-run-hb",
                "workflow_id": "test-workflow",
                "pid": 12345,
            },
        )

        resp = client.post("/runs/test-run-hb/heartbeat")
        assert resp.status_code == 200

    def test_complete_run(self, raw_server):
        """Workflow can mark itself as complete."""
        client = httpx.Client(base_url=raw_server)

        client.post(
            "/runs/register",
            json={
                "run_id": "test-run-done",
                "workflow_id": "test-workflow",
                "pid": 12345,
            },
        )

        resp = client.post(
            "/runs/test-run-done/complete",
            json={
                "status": "success",
            },
        )
        assert resp.status_code == 200

        # Check runs list
        resp = client.get("/runs")
        runs = resp.json()
        run = next(r for r in runs if r["run_id"] == "test-run-done")
        assert run["status"] == "completed"


class TestServerConnection:
    """Test client-side ServerConnection class."""

    def test_connect_and_disconnect(self, raw_server):
        """ServerConnection can connect and disconnect."""
        from raw_runtime.connection import ServerConnection

        conn = ServerConnection(server_url=raw_server)
        assert conn.connect("conn-test-1", "test-workflow")
        assert conn.is_connected

        conn.disconnect("success")
        assert not conn.is_connected

    def test_wait_for_event(self, raw_server):
        """wait_for_event receives approval from server."""
        import threading

        from raw_runtime.connection import ServerConnection

        conn = ServerConnection(server_url=raw_server)
        conn.connect("conn-test-2", "test-workflow")

        result = {"decision": None}

        def wait_thread():
            try:
                event = conn.wait_for_event(
                    event_type="approval",
                    step_name="test-step",
                    timeout_seconds=5,
                )
                result["decision"] = event.get("decision")
            except TimeoutError:
                result["decision"] = "timeout"

        thread = threading.Thread(target=wait_thread)
        thread.start()

        # Give workflow time to register waiting
        time.sleep(0.5)

        # Send approval
        client = httpx.Client(base_url=raw_server)
        client.post("/approve/conn-test-2/test-step", json={"decision": "approve"})

        thread.join(timeout=3)
        conn.disconnect()

        assert result["decision"] == "approve"

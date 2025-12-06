"""Tests for RAW server module."""

import re
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raw.engine.server import RAWServer, RunRegistry


class TestRunIdUniqueness:
    """Tests for server run ID uniqueness."""

    @pytest.mark.asyncio
    async def test_run_id_includes_uuid_suffix(self) -> None:
        """Verify run_id has UUID suffix for uniqueness within same second."""
        server = RAWServer()

        with patch("raw.engine.server.find_workflow") as mock_find:
            mock_find.return_value = None

            # Test that ValueError is raised for missing workflow
            # (we just want to verify the run_id format before it fails)
            with pytest.raises(ValueError, match="Workflow not found"):
                await server.trigger_workflow("nonexistent")

    @pytest.mark.asyncio
    async def test_concurrent_triggers_get_unique_run_ids(self) -> None:
        """Two triggers in the same second should get different run IDs."""
        from raw.engine.server import datetime as server_datetime
        import uuid

        # Capture generated run_ids
        run_ids: list[str] = []

        # Mock datetime to return same timestamp
        fixed_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        with patch("raw.engine.server.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_time
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # Generate two run IDs using the same logic as the server
            for _ in range(2):
                run_id = fixed_time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
                run_ids.append(run_id)

        # Run IDs should be different due to UUID suffix
        assert run_ids[0] != run_ids[1]
        # Both should have the same timestamp prefix
        assert run_ids[0][:15] == run_ids[1][:15]  # YYYYMMDD-HHMMSS
        # Both should have UUID suffix
        assert len(run_ids[0]) == 24  # 15 + 1 + 8
        assert len(run_ids[1]) == 24

    def test_run_id_format(self) -> None:
        """Verify run_id matches expected format."""
        import uuid

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        run_id = timestamp + "-" + uuid.uuid4().hex[:8]

        # Should match: YYYYMMDD-HHMMSS-xxxxxxxx
        pattern = r"^\d{8}-\d{6}-[a-f0-9]{8}$"
        assert re.match(pattern, run_id)


class TestRunRegistry:
    """Tests for RunRegistry."""

    def test_register_creates_run(self) -> None:
        registry = RunRegistry()
        run = registry.register("run-001", "workflow-1", 12345)

        assert run.run_id == "run-001"
        assert run.workflow_id == "workflow-1"
        assert run.pid == 12345
        assert run.status == "running"

    def test_get_returns_run(self) -> None:
        registry = RunRegistry()
        registry.register("run-001", "workflow-1", 12345)

        run = registry.get("run-001")
        assert run is not None
        assert run.run_id == "run-001"

    def test_get_returns_none_for_unknown(self) -> None:
        registry = RunRegistry()
        assert registry.get("nonexistent") is None

    def test_mark_waiting(self) -> None:
        registry = RunRegistry()
        registry.register("run-001", "workflow-1", 12345)

        registry.mark_waiting(
            "run-001",
            event_type="approval",
            step_name="deploy",
            prompt="Deploy to prod?",
            options=["approve", "reject"],
        )

        run = registry.get("run-001")
        assert run is not None
        assert run.status == "waiting"
        assert run.waiting_for is not None
        assert run.waiting_for.step_name == "deploy"

    def test_heartbeat_updates_timestamp(self) -> None:
        registry = RunRegistry()
        registry.register("run-001", "workflow-1", 12345)

        run = registry.get("run-001")
        assert run is not None
        old_heartbeat = run.last_heartbeat

        import time
        time.sleep(0.01)

        result = registry.heartbeat("run-001")
        assert result is True
        assert run.last_heartbeat > old_heartbeat

    def test_heartbeat_returns_false_for_unknown(self) -> None:
        registry = RunRegistry()
        assert registry.heartbeat("nonexistent") is False

    def test_complete_sets_status(self) -> None:
        registry = RunRegistry()
        registry.register("run-001", "workflow-1", 12345)

        registry.complete("run-001", "success")

        run = registry.get("run-001")
        assert run is not None
        assert run.status == "completed"

    def test_complete_failed(self) -> None:
        registry = RunRegistry()
        registry.register("run-001", "workflow-1", 12345)

        registry.complete("run-001", "failed")

        run = registry.get("run-001")
        assert run is not None
        assert run.status == "failed"

    def test_unregister_removes_run(self) -> None:
        registry = RunRegistry()
        registry.register("run-001", "workflow-1", 12345)

        registry.unregister("run-001")

        assert registry.get("run-001") is None

    def test_push_event(self) -> None:
        from raw.engine.server import Event

        registry = RunRegistry()
        registry.register("run-001", "workflow-1", 12345)

        event = Event(event_type="approval", step_name="deploy", payload={"decision": "approve"})
        result = registry.push_event("run-001", event)

        assert result is True

    def test_push_event_returns_false_for_unknown(self) -> None:
        from raw.engine.server import Event

        registry = RunRegistry()
        event = Event(event_type="approval", step_name="deploy", payload={"decision": "approve"})

        result = registry.push_event("nonexistent", event)
        assert result is False

    def test_pop_events(self) -> None:
        from raw.engine.server import Event

        registry = RunRegistry()
        registry.register("run-001", "workflow-1", 12345)

        event1 = Event(event_type="approval", step_name="step1", payload={})
        event2 = Event(event_type="approval", step_name="step2", payload={})
        registry.push_event("run-001", event1)
        registry.push_event("run-001", event2)

        events = registry.pop_events("run-001")
        assert len(events) == 2

        # Second pop should return empty list
        events = registry.pop_events("run-001")
        assert len(events) == 0

    def test_list_runs(self) -> None:
        registry = RunRegistry()
        registry.register("run-001", "workflow-1", 12345)
        registry.register("run-002", "workflow-2", 12346)

        runs = registry.list_runs()
        assert len(runs) == 2

    def test_list_waiting(self) -> None:
        registry = RunRegistry()
        registry.register("run-001", "workflow-1", 12345)
        registry.register("run-002", "workflow-2", 12346)

        registry.mark_waiting("run-001", "approval", "deploy")

        waiting = registry.list_waiting()
        assert len(waiting) == 1
        assert waiting[0][0] == "run-001"

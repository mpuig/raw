"""Tests for orchestrator abstraction."""

import pytest

from raw_runtime.orchestrator import (
    HttpOrchestrator,
    LocalOrchestrator,
    Orchestrator,
    OrchestratorRunInfo,
    OrchestratorRunStatus,
    get_orchestrator,
    set_orchestrator,
)


class TestOrchestratorProtocol:
    """Test that implementations satisfy the Orchestrator protocol."""

    def test_local_orchestrator_is_orchestrator(self):
        assert isinstance(LocalOrchestrator(), Orchestrator)

    def test_http_orchestrator_is_orchestrator(self, monkeypatch):
        monkeypatch.setenv("RAW_SERVER_URL", "http://localhost:8000")
        assert isinstance(HttpOrchestrator(), Orchestrator)


class TestOrchestratorRunStatus:
    """Tests for OrchestratorRunStatus enum."""

    def test_status_values(self):
        assert OrchestratorRunStatus.PENDING == "pending"
        assert OrchestratorRunStatus.RUNNING == "running"
        assert OrchestratorRunStatus.WAITING == "waiting"
        assert OrchestratorRunStatus.COMPLETED == "completed"
        assert OrchestratorRunStatus.FAILED == "failed"
        assert OrchestratorRunStatus.TIMEOUT == "timeout"


class TestOrchestratorRunInfo:
    """Tests for OrchestratorRunInfo dataclass."""

    def test_basic_creation(self):
        info = OrchestratorRunInfo(
            run_id="run-123",
            workflow_id="test-workflow",
            status=OrchestratorRunStatus.RUNNING,
        )
        assert info.run_id == "run-123"
        assert info.workflow_id == "test-workflow"
        assert info.status == OrchestratorRunStatus.RUNNING
        assert info.started_at is None
        assert info.exit_code is None

    def test_with_all_fields(self):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        info = OrchestratorRunInfo(
            run_id="run-456",
            workflow_id="my-workflow",
            status=OrchestratorRunStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            exit_code=0,
            error=None,
            metadata={"foo": "bar"},
        )
        assert info.exit_code == 0
        assert info.metadata == {"foo": "bar"}
        assert info.ended_at == now  # Test the alias property


class TestLocalOrchestrator:
    """Tests for LocalOrchestrator implementation."""

    @pytest.fixture
    def orchestrator(self):
        return LocalOrchestrator()

    def test_trigger_nonexistent_workflow(self, orchestrator):
        with pytest.raises(ValueError, match="Workflow not found"):
            orchestrator.trigger("nonexistent-workflow-12345")

    def test_get_status_not_found(self, orchestrator):
        with pytest.raises(KeyError, match="Run not found"):
            orchestrator.get_status("nonexistent-run")

    def test_wait_for_completion_not_found(self, orchestrator):
        with pytest.raises(KeyError, match="Run not found"):
            orchestrator.wait_for_completion("nonexistent-run")

    def test_list_runs_empty(self, orchestrator):
        runs = orchestrator.list_runs()
        assert runs == []

    def test_list_runs_with_filter(self, orchestrator):
        # No runs yet, filters should work
        runs = orchestrator.list_runs(workflow_id="test")
        assert runs == []

        runs = orchestrator.list_runs(status=OrchestratorRunStatus.RUNNING)
        assert runs == []


class TestHttpOrchestrator:
    """Tests for HttpOrchestrator initialization."""

    def test_requires_server_url(self, monkeypatch):
        monkeypatch.delenv("RAW_SERVER_URL", raising=False)
        with pytest.raises(ValueError, match="RAW_SERVER_URL not set"):
            HttpOrchestrator()

    def test_uses_env_var(self, monkeypatch):
        monkeypatch.setenv("RAW_SERVER_URL", "http://example.com:9000")
        orch = HttpOrchestrator()
        assert orch.server_url == "http://example.com:9000"

    def test_explicit_url(self, monkeypatch):
        monkeypatch.delenv("RAW_SERVER_URL", raising=False)
        orch = HttpOrchestrator(server_url="http://custom:8080")
        assert orch.server_url == "http://custom:8080"

    def test_status_mapping(self, monkeypatch):
        monkeypatch.setenv("RAW_SERVER_URL", "http://localhost:8000")
        orch = HttpOrchestrator()

        assert orch._map_status("running") == OrchestratorRunStatus.RUNNING
        assert orch._map_status("waiting") == OrchestratorRunStatus.WAITING
        assert orch._map_status("completed") == OrchestratorRunStatus.COMPLETED
        assert orch._map_status("failed") == OrchestratorRunStatus.FAILED
        assert orch._map_status("success") == OrchestratorRunStatus.COMPLETED
        assert orch._map_status("unknown_status") == OrchestratorRunStatus.UNKNOWN
        assert orch._map_status(None) == OrchestratorRunStatus.UNKNOWN


class TestGlobalOrchestrator:
    """Tests for global orchestrator getter/setter."""

    def test_get_orchestrator_local_default(self, monkeypatch):
        monkeypatch.delenv("RAW_SERVER_URL", raising=False)
        set_orchestrator(None)
        orch = get_orchestrator()
        assert isinstance(orch, LocalOrchestrator)

    def test_get_orchestrator_http_when_url_set(self, monkeypatch):
        monkeypatch.setenv("RAW_SERVER_URL", "http://localhost:8000")
        set_orchestrator(None)
        orch = get_orchestrator()
        assert isinstance(orch, HttpOrchestrator)
        set_orchestrator(None)

    def test_set_and_get_orchestrator(self):
        local = LocalOrchestrator()
        set_orchestrator(local)
        assert get_orchestrator() is local
        set_orchestrator(None)

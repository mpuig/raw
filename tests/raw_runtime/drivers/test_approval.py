"""Tests for human-in-the-loop approval."""

from raw_runtime.approval import (
    AutoApprovalHandler,
    get_approval_handler,
    set_approval_handler,
    wait_for_approval,
)
from raw_runtime.bus import LocalEventBus
from raw_runtime.context import WorkflowContext, set_workflow_context
from raw_runtime.events import (
    ApprovalReceivedEvent,
    ApprovalRequestedEvent,
    Event,
    EventType,
)


class TestAutoApprovalHandler:
    """Tests for AutoApprovalHandler."""

    def test_auto_approve(self) -> None:
        handler = AutoApprovalHandler(decision="approve")
        result = handler.request_approval(
            step_name="test",
            prompt="Approve?",
            options=["approve", "reject"],
            context={},
            timeout_seconds=None,
        )
        assert result == "approve"

    def test_auto_reject(self) -> None:
        handler = AutoApprovalHandler(decision="reject")
        result = handler.request_approval(
            step_name="test",
            prompt="Approve?",
            options=["approve", "reject"],
            context={},
            timeout_seconds=None,
        )
        assert result == "reject"


class TestWaitForApproval:
    """Tests for wait_for_approval function."""

    def setup_method(self) -> None:
        """Set up auto-approval handler for tests."""
        set_approval_handler(AutoApprovalHandler(decision="approve"))

    def teardown_method(self) -> None:
        """Reset approval handler."""
        set_approval_handler(None)
        set_workflow_context(None)

    def test_returns_decision(self) -> None:
        decision = wait_for_approval(
            prompt="Deploy to production?",
            step_name="deploy",
        )
        assert decision == "approve"

    def test_emits_events_with_context(self) -> None:
        events: list[Event] = []
        bus = LocalEventBus()
        bus.subscribe(lambda e: events.append(e))

        context = WorkflowContext(
            workflow_id="test-workflow",
            short_name="test",
            event_bus=bus,
        )
        set_workflow_context(context)

        wait_for_approval(
            prompt="Continue?",
            step_name="checkpoint",
            context={"version": "1.0"},
        )

        assert len(events) == 2
        request_event = events[0]
        assert isinstance(request_event, ApprovalRequestedEvent)
        assert request_event.event_type == EventType.APPROVAL_REQUESTED
        assert request_event.prompt == "Continue?"
        assert request_event.step_name == "checkpoint"

        response_event = events[1]
        assert isinstance(response_event, ApprovalReceivedEvent)
        assert response_event.event_type == EventType.APPROVAL_RECEIVED
        assert response_event.decision == "approve"

    def test_default_options(self) -> None:
        events: list[Event] = []
        bus = LocalEventBus()
        bus.subscribe(lambda e: events.append(e))

        context = WorkflowContext(
            workflow_id="test-workflow",
            short_name="test",
            event_bus=bus,
        )
        set_workflow_context(context)

        wait_for_approval(prompt="Continue?")

        request_event = events[0]
        assert isinstance(request_event, ApprovalRequestedEvent)
        assert request_event.options == ["approve", "reject"]

    def test_custom_options(self) -> None:
        handler = AutoApprovalHandler(decision="rollback")
        set_approval_handler(handler)

        events: list[Event] = []
        bus = LocalEventBus()
        bus.subscribe(lambda e: events.append(e))

        context = WorkflowContext(
            workflow_id="test-workflow",
            short_name="test",
            event_bus=bus,
        )
        set_workflow_context(context)

        decision = wait_for_approval(
            prompt="What action?",
            options=["continue", "rollback", "abort"],
        )

        assert decision == "rollback"
        request_event = events[0]
        assert isinstance(request_event, ApprovalRequestedEvent)
        assert request_event.options == ["continue", "rollback", "abort"]


class TestApprovalHandlerGlobal:
    """Tests for global approval handler management."""

    def teardown_method(self) -> None:
        set_approval_handler(None)

    def test_default_handler_is_console(self) -> None:
        from raw_runtime.approval import ConsoleApprovalHandler

        handler = get_approval_handler()
        assert isinstance(handler, ConsoleApprovalHandler)

    def test_set_custom_handler(self) -> None:
        custom = AutoApprovalHandler(decision="custom")
        set_approval_handler(custom)
        assert get_approval_handler() is custom


# --- Async approval tests ---

import asyncio

import pytest

from raw_runtime.approval import set_approval_registry, wait_for_approval_async
from raw_runtime.bus import ApprovalRegistry


@pytest.mark.asyncio
class TestWaitForApprovalAsync:
    """Tests for wait_for_approval_async."""

    async def test_async_approval_flow(self) -> None:
        """Test full async approval flow with registry."""
        registry = ApprovalRegistry()
        set_approval_registry(registry)

        bus = LocalEventBus()
        events: list = []
        bus.subscribe(lambda e: events.append(e))

        ctx = WorkflowContext(workflow_id="test-wf", short_name="test", event_bus=bus)
        set_workflow_context(ctx)

        # Start approval task in background
        task = asyncio.create_task(wait_for_approval_async("Deploy?", step_name="deploy"))

        # Verify request pending (includes run_id from context)
        await asyncio.sleep(0.01)
        assert registry.is_pending("test-wf", "deploy", ctx.run_id)
        assert len(events) == 1
        assert isinstance(events[0], ApprovalRequestedEvent)

        # Resolve externally (must include run_id)
        registry.resolve("test-wf", "deploy", "approve", ctx.run_id)

        # Verify result
        result = await task
        assert result == "approve"
        assert len(events) == 2
        assert isinstance(events[1], ApprovalReceivedEvent)
        assert events[1].decision == "approve"

    async def test_async_approval_timeout(self) -> None:
        """Test approval timeout."""
        registry = ApprovalRegistry()
        set_approval_registry(registry)

        ctx = WorkflowContext(workflow_id="test-wf", short_name="test")
        set_workflow_context(ctx)

        with pytest.raises(TimeoutError):
            await wait_for_approval_async("Quick?", timeout_seconds=0.01)

    def teardown_method(self) -> None:
        set_approval_registry(None)
        set_workflow_context(None)

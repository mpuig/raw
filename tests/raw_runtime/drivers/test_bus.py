"""Tests for event bus implementations."""

import asyncio

from raw_runtime.bus import AsyncEventBus, LocalEventBus, NullEventBus
from raw_runtime.events import (
    Event,
    EventType,
    StepCompletedEvent,
    StepStartedEvent,
    WorkflowStartedEvent,
)


class TestLocalEventBus:
    """Tests for LocalEventBus."""

    def test_emit_to_handler(self) -> None:
        bus = LocalEventBus()
        received: list[Event] = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(handler)

        event = WorkflowStartedEvent(
            workflow_id="test",
            workflow_name="test",
        )
        bus.emit(event)

        assert len(received) == 1
        assert received[0] == event

    def test_filter_by_event_type(self) -> None:
        bus = LocalEventBus()
        started_events: list[Event] = []
        completed_events: list[Event] = []

        def started_handler(event: Event) -> None:
            started_events.append(event)

        def completed_handler(event: Event) -> None:
            completed_events.append(event)

        bus.subscribe(started_handler, event_types=[EventType.STEP_STARTED])
        bus.subscribe(completed_handler, event_types=[EventType.STEP_COMPLETED])

        bus.emit(StepStartedEvent(workflow_id="test", step_name="step1"))
        bus.emit(
            StepCompletedEvent(
                workflow_id="test", step_name="step1", duration_seconds=1.0, result_type="str"
            )
        )
        bus.emit(StepStartedEvent(workflow_id="test", step_name="step2"))

        assert len(started_events) == 2
        assert len(completed_events) == 1

    def test_unsubscribe(self) -> None:
        bus = LocalEventBus()
        received: list[Event] = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(handler)
        bus.emit(WorkflowStartedEvent(workflow_id="test", workflow_name="test"))
        assert len(received) == 1

        bus.unsubscribe(handler)
        bus.emit(WorkflowStartedEvent(workflow_id="test2", workflow_name="test2"))
        assert len(received) == 1  # No new events

    def test_clear(self) -> None:
        bus = LocalEventBus()
        received: list[Event] = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(handler)
        bus.clear()
        bus.emit(WorkflowStartedEvent(workflow_id="test", workflow_name="test"))
        assert len(received) == 0

    def test_multiple_handlers(self) -> None:
        bus = LocalEventBus()
        handler1_received: list[Event] = []
        handler2_received: list[Event] = []

        def handler1(event: Event) -> None:
            handler1_received.append(event)

        def handler2(event: Event) -> None:
            handler2_received.append(event)

        bus.subscribe(handler1)
        bus.subscribe(handler2)

        bus.emit(WorkflowStartedEvent(workflow_id="test", workflow_name="test"))

        assert len(handler1_received) == 1
        assert len(handler2_received) == 1


class TestNullEventBus:
    """Tests for NullEventBus."""

    def test_emit_does_nothing(self) -> None:
        bus = NullEventBus()
        # Should not raise
        bus.emit(WorkflowStartedEvent(workflow_id="test", workflow_name="test"))

    def test_subscribe_does_nothing(self) -> None:
        bus = NullEventBus()
        called = False

        def handler(event: Event) -> None:  # noqa: ARG001
            nonlocal called
            called = True

        bus.subscribe(handler)
        bus.emit(WorkflowStartedEvent(workflow_id="test", workflow_name="test"))
        # Handler should not be called because NullEventBus discards everything
        assert not called


class TestAsyncEventBus:
    """Tests for AsyncEventBus."""

    async def test_emit_async_adds_to_queue(self) -> None:
        bus = AsyncEventBus()
        event = WorkflowStartedEvent(workflow_id="test", workflow_name="test")
        await bus.emit_async(event)
        assert bus._queue.qsize() == 1

    async def test_sync_handler_called(self) -> None:
        bus = AsyncEventBus()
        received: list[Event] = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(handler)
        event = WorkflowStartedEvent(workflow_id="test", workflow_name="test")
        await bus.emit_async(event)

        # Process the event
        await bus._dispatch(event)
        assert len(received) == 1
        assert received[0] == event

    async def test_async_handler_called(self) -> None:
        bus = AsyncEventBus()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe_async(handler)
        event = WorkflowStartedEvent(workflow_id="test", workflow_name="test")

        await bus._dispatch(event)
        assert len(received) == 1
        assert received[0] == event

    async def test_filter_by_event_type(self) -> None:
        bus = AsyncEventBus()
        started_events: list[Event] = []
        completed_events: list[Event] = []

        async def started_handler(event: Event) -> None:
            started_events.append(event)

        async def completed_handler(event: Event) -> None:
            completed_events.append(event)

        bus.subscribe_async(started_handler, event_types=[EventType.STEP_STARTED])
        bus.subscribe_async(completed_handler, event_types=[EventType.STEP_COMPLETED])

        await bus._dispatch(StepStartedEvent(workflow_id="test", step_name="step1"))
        await bus._dispatch(
            StepCompletedEvent(
                workflow_id="test", step_name="step1", duration_seconds=1.0, result_type="str"
            )
        )
        await bus._dispatch(StepStartedEvent(workflow_id="test", step_name="step2"))

        assert len(started_events) == 2
        assert len(completed_events) == 1

    async def test_start_processes_queue(self) -> None:
        bus = AsyncEventBus()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe_async(handler)

        event = WorkflowStartedEvent(workflow_id="test", workflow_name="test")
        await bus.emit_async(event)

        # Start processing in background, then stop
        async def run_and_stop() -> None:
            await asyncio.sleep(0.01)
            await bus.stop()

        await asyncio.gather(bus.start(), run_and_stop())

        assert len(received) == 1
        assert received[0] == event

    async def test_stop_halts_processing(self) -> None:
        bus = AsyncEventBus()
        await bus.stop()
        assert not bus._running

    async def test_unsubscribe_sync(self) -> None:
        bus = AsyncEventBus()
        received: list[Event] = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(handler)
        bus.unsubscribe(handler)

        event = WorkflowStartedEvent(workflow_id="test", workflow_name="test")
        await bus._dispatch(event)
        assert len(received) == 0

    async def test_unsubscribe_async(self) -> None:
        bus = AsyncEventBus()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe_async(handler)
        bus.unsubscribe_async(handler)

        event = WorkflowStartedEvent(workflow_id="test", workflow_name="test")
        await bus._dispatch(event)
        assert len(received) == 0

    async def test_clear_removes_all_handlers(self) -> None:
        bus = AsyncEventBus()

        def sync_handler(event: Event) -> None:  # noqa: ARG001
            pass

        async def async_handler(event: Event) -> None:  # noqa: ARG001
            pass

        bus.subscribe(sync_handler)
        bus.subscribe_async(async_handler)
        bus.clear()

        assert len(bus._handlers) == 0
        assert len(bus._sync_handlers) == 0

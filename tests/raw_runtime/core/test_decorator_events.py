"""Tests for RAW runtime decorators events."""

import pytest

from raw_runtime import WorkflowContext, raw_step, retry, set_workflow_context
from raw_runtime.bus import LocalEventBus
from raw_runtime.events import StepCompletedEvent, StepFailedEvent, StepRetryEvent, StepStartedEvent


class TestDecoratorEvents:
    """Tests that decorators emit correct events."""

    def setup_method(self) -> None:
        self.bus = LocalEventBus()
        self.events = []
        self.bus.subscribe(lambda e: self.events.append(e))

        self.ctx = WorkflowContext(workflow_id="test-wf", short_name="test", event_bus=self.bus)
        set_workflow_context(self.ctx)

    def teardown_method(self) -> None:
        set_workflow_context(None)

    def test_raw_step_events_success(self) -> None:
        """Test step start/complete events."""

        @raw_step("my_step")
        def my_step() -> str:
            return "ok"

        my_step()

        assert len(self.events) == 2
        assert isinstance(self.events[0], StepStartedEvent)
        assert self.events[0].step_name == "my_step"

        assert isinstance(self.events[1], StepCompletedEvent)
        assert self.events[1].step_name == "my_step"
        assert self.events[1].result_type == "str"

    def test_raw_step_events_failure(self) -> None:
        """Test step start/failed events."""

        @raw_step("fail_step")
        def fail_step() -> None:
            raise ValueError("oops")

        with pytest.raises(ValueError):
            fail_step()

        assert len(self.events) == 2
        assert isinstance(self.events[0], StepStartedEvent)

        assert isinstance(self.events[1], StepFailedEvent)
        assert self.events[1].step_name == "fail_step"
        assert self.events[1].error == "oops"

    def test_retry_events(self) -> None:
        """Test retry events are emitted."""

        @raw_step("retry_step")
        @retry(retries=1, base_delay=0.01)
        def retry_step() -> None:
            raise ValueError("fail")

        with pytest.raises(ValueError):
            retry_step()

        # Sequence: Start -> Retry -> Failed
        # Note: raw_step wraps retry, so Start happens first
        # Wait, usually @retry wraps @raw_step implementation logic?
        # No, typically: @raw_step @retry def func()
        # raw_step calls retry_wrapper calls func

        # Let's check event types present
        event_types = [type(e) for e in self.events]
        assert StepStartedEvent in event_types
        assert StepRetryEvent in event_types
        assert StepFailedEvent in event_types

        retry_event = next(e for e in self.events if isinstance(e, StepRetryEvent))
        assert retry_event.step_name == "retry_step"
        assert retry_event.attempt == 1

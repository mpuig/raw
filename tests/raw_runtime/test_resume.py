"""Tests for workflow resume functionality."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from raw_runtime.context import WorkflowContext
from raw_runtime.journal import LocalJournalWriter
from raw_runtime.models import RunStatus, StepStatus
from raw_runtime.resume import (
    configure_context_for_resume,
    prepare_resume_state,
)


class TestPrepareResumeState:
    """Tests for prepare_resume_state()."""

    def test_prepare_resume_state_from_successful_steps(self, tmp_path: Path) -> None:
        """Test preparing resume state from journal with successful steps."""
        journal_path = tmp_path / "events.jsonl"

        # Write journal with workflow + 2 successful steps
        from raw_runtime.events import (
            StepCompletedEvent,
            StepStartedEvent,
            WorkflowStartedEvent,
        )

        with LocalJournalWriter(journal_path) as writer:
            writer.write_event(
                WorkflowStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    workflow_name="TestWorkflow",
                    timestamp=datetime.now(timezone.utc),
                )
            )
            writer.write_event(
                StepStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    step_name="step1",
                    timestamp=datetime.now(timezone.utc),
                )
            )
            writer.write_event(
                StepCompletedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    step_name="step1",
                    duration_seconds=1.0,
                    result_type="str",
                    timestamp=datetime.now(timezone.utc),
                )
            )
            writer.write_event(
                StepStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    step_name="step2",
                    timestamp=datetime.now(timezone.utc),
                )
            )
            writer.write_event(
                StepCompletedEvent(
                    workflow_id="test-workflow",
                    run_id="run_123",
                    step_name="step2",
                    duration_seconds=1.0,
                    result_type="str",
                    timestamp=datetime.now(timezone.utc),
                )
            )

        # Prepare resume state
        completed_steps, previous_run_id = prepare_resume_state(journal_path)

        assert completed_steps == {"step1", "step2"}
        assert previous_run_id == "run_123"

    def test_prepare_resume_state_with_failed_step(self, tmp_path: Path) -> None:
        """Test resume state excludes failed steps."""
        journal_path = tmp_path / "events.jsonl"

        from raw_runtime.events import (
            StepCompletedEvent,
            StepFailedEvent,
            StepStartedEvent,
            WorkflowStartedEvent,
        )

        with LocalJournalWriter(journal_path) as writer:
            writer.write_event(
                WorkflowStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_456",
                    workflow_name="TestWorkflow",
                )
            )
            # Step1: Success
            writer.write_event(
                StepStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_456",
                    step_name="step1",
                )
            )
            writer.write_event(
                StepCompletedEvent(
                    workflow_id="test-workflow",
                    run_id="run_456",
                    step_name="step1",
                    duration_seconds=1.0,
                    result_type="str",
                )
            )
            # Step2: Failed
            writer.write_event(
                StepStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_456",
                    step_name="step2",
                )
            )
            writer.write_event(
                StepFailedEvent(
                    workflow_id="test-workflow",
                    run_id="run_456",
                    step_name="step2",
                    error="Something went wrong",
                    duration_seconds=0.5,
                )
            )

        completed_steps, previous_run_id = prepare_resume_state(journal_path)

        # Only step1 completed, step2 failed so should not be in completed set
        assert completed_steps == {"step1"}
        assert previous_run_id == "run_456"

    def test_prepare_resume_state_with_incomplete_steps(self, tmp_path: Path) -> None:
        """Test resume state with steps that started but didn't complete (crashed)."""
        journal_path = tmp_path / "events.jsonl"

        from raw_runtime.events import StepStartedEvent, WorkflowStartedEvent

        with LocalJournalWriter(journal_path) as writer:
            writer.write_event(
                WorkflowStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_789",
                    workflow_name="TestWorkflow",
                )
            )
            # Step started but never completed (crash)
            writer.write_event(
                StepStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_789",
                    step_name="step1",
                )
            )

        completed_steps, previous_run_id = prepare_resume_state(journal_path)

        # No steps completed
        assert completed_steps == set()
        assert previous_run_id == "run_789"

    def test_prepare_resume_state_missing_journal(self, tmp_path: Path) -> None:
        """Test error when journal doesn't exist."""
        journal_path = tmp_path / "nonexistent.jsonl"

        with pytest.raises(ValueError, match="Journal not found"):
            prepare_resume_state(journal_path)

    def test_prepare_resume_state_corrupt_journal(self, tmp_path: Path) -> None:
        """Test error with corrupt journal."""
        journal_path = tmp_path / "events.jsonl"
        journal_path.write_text("not valid json\n")

        with pytest.raises(ValueError, match="Failed to read journal"):
            prepare_resume_state(journal_path)


class TestConfigureContextForResume:
    """Tests for configure_context_for_resume()."""

    def test_configure_context_for_resume(self, tmp_path: Path) -> None:
        """Test configuring context for resume."""
        journal_path = tmp_path / "events.jsonl"

        # Create journal with completed steps
        from raw_runtime.events import (
            StepCompletedEvent,
            StepStartedEvent,
            WorkflowStartedEvent,
        )

        with LocalJournalWriter(journal_path) as writer:
            writer.write_event(
                WorkflowStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_original",
                    workflow_name="TestWorkflow",
                )
            )
            writer.write_event(
                StepStartedEvent(
                    workflow_id="test-workflow",
                    run_id="run_original",
                    step_name="fetch",
                )
            )
            writer.write_event(
                StepCompletedEvent(
                    workflow_id="test-workflow",
                    run_id="run_original",
                    step_name="fetch",
                    duration_seconds=1.0,
                    result_type="str",
                )
            )

        # Create new context and configure for resume
        context = WorkflowContext(
            workflow_id="test-workflow",
            short_name="test",
            parameters={},
        )

        configure_context_for_resume(context, journal_path)

        # Verify context configured correctly
        assert context.resume_completed_steps == {"fetch"}
        assert context.resumed_from_run_id == "run_original"


class TestResumeIntegration:
    """Integration tests for resume with decorator."""

    def test_decorator_skips_completed_steps(self, tmp_path: Path) -> None:
        """Test that @step decorator skips steps in resume_completed_steps."""
        from raw_runtime.bus import LocalEventBus
        from raw_runtime.decorators import raw_step
        from raw_runtime.events import StepSkippedEvent

        # Create context with resume state
        bus = LocalEventBus()
        events = []
        bus.subscribe(lambda e: events.append(e))

        context = WorkflowContext(
            workflow_id="test",
            short_name="test",
            event_bus=bus,
        )
        context.resume_completed_steps = {"step1", "step2"}
        context.resumed_from_run_id = "run_previous"

        # Define workflow with steps
        from raw_runtime.context import set_workflow_context

        set_workflow_context(context)

        @raw_step("step1")
        def step1():
            return "step1_result"

        @raw_step("step2")
        def step2():
            return "step2_result"

        @raw_step("step3")
        def step3():
            return "step3_result"

        # Execute steps
        result1 = step1()
        result2 = step2()
        result3 = step3()

        # step1 and step2 should return None (skipped), step3 should execute
        assert result1 is None
        assert result2 is None
        assert result3 == "step3_result"

        # Verify events: 2 skipped, 1 started + 1 completed
        skip_events = [e for e in events if isinstance(e, StepSkippedEvent)]
        assert len(skip_events) == 2
        assert skip_events[0].step_name == "step1"
        assert skip_events[1].step_name == "step2"
        assert "run_previous" in skip_events[0].reason

        # step3 should have normal execution events
        from raw_runtime.events import StepCompletedEvent, StepStartedEvent

        step3_events = [
            e for e in events if hasattr(e, "step_name") and e.step_name == "step3"
        ]
        assert len(step3_events) == 2
        assert isinstance(step3_events[0], StepStartedEvent)
        assert isinstance(step3_events[1], StepCompletedEvent)

    def test_end_to_end_resume_workflow(self, tmp_path: Path) -> None:
        """Test complete resume flow: crash → resume → completion."""
        from raw_runtime.bus import LocalEventBus
        from raw_runtime.context import set_workflow_context
        from raw_runtime.decorators import raw_step
        from raw_runtime.events import WorkflowStartedEvent

        # === FIRST RUN: Crash after step1 ===
        run1_journal = tmp_path / "run1_events.jsonl"
        bus1 = LocalEventBus()

        # Set up journal handler
        from raw_runtime.handlers import JournalEventHandler

        journal_handler = JournalEventHandler(run1_journal)
        bus1.subscribe(journal_handler)

        context1 = WorkflowContext(
            workflow_id="test-workflow",
            short_name="test",
            event_bus=bus1,
        )
        set_workflow_context(context1)

        # Emit workflow started
        context1.emit(
            WorkflowStartedEvent(
                workflow_id="test-workflow",
                run_id=context1.run_id,
                workflow_name="test",
            )
        )

        @raw_step("step1")
        def step1():
            return "step1_done"

        @raw_step("step2")
        def step2():
            return "step2_done"

        # Execute step1, then "crash" before step2
        step1()
        # (Don't execute step2 - simulate crash)

        # === SECOND RUN: Resume from step2 ===
        run2_journal = tmp_path / "run2_events.jsonl"
        bus2 = LocalEventBus()
        journal_handler2 = JournalEventHandler(run2_journal)
        bus2.subscribe(journal_handler2)

        context2 = WorkflowContext(
            workflow_id="test-workflow",
            short_name="test",
            event_bus=bus2,
        )

        # Configure for resume
        configure_context_for_resume(context2, run1_journal)

        set_workflow_context(context2)

        # Emit workflow started for resumed run
        context2.emit(
            WorkflowStartedEvent(
                workflow_id="test-workflow",
                run_id=context2.run_id,
                workflow_name="test",
            )
        )

        # Execute both steps - step1 should be skipped, step2 should execute
        result1 = step1()
        result2 = step2()

        assert result1 is None  # Skipped
        assert result2 == "step2_done"  # Executed

        # Verify step results in context
        assert len(context2._steps) == 2
        assert context2._steps[0].status == StepStatus.SKIPPED
        assert context2._steps[0].name == "step1"
        assert context2._steps[1].status == StepStatus.SUCCESS
        assert context2._steps[1].name == "step2"

        # Verify resumed_from linkage
        assert context2.resumed_from_run_id == context1.run_id

"""Tests for HumanInterface implementations."""

from io import StringIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from raw_runtime.drivers.human import AutoInterface, ConsoleInterface, ServerInterface
from raw_runtime.protocols.human import AsyncHumanInterface, HumanInterface


class TestHumanInterfaceProtocol:
    """Tests that implementations satisfy the HumanInterface protocol."""

    def test_console_interface_satisfies_protocol(self) -> None:
        interface = ConsoleInterface()
        assert isinstance(interface, HumanInterface)

    def test_auto_interface_satisfies_protocol(self) -> None:
        interface = AutoInterface()
        assert isinstance(interface, HumanInterface)

    def test_server_interface_satisfies_protocol(self) -> None:
        interface = ServerInterface()
        assert isinstance(interface, HumanInterface)

    def test_server_interface_satisfies_async_protocol(self) -> None:
        interface = ServerInterface()
        assert isinstance(interface, AsyncHumanInterface)


class TestAutoInterface:
    """Tests for AutoInterface."""

    def test_default_response(self) -> None:
        interface = AutoInterface()
        result = interface.request_input("Choose an option", options=["approve", "reject"])
        assert result == "approve"

    def test_custom_default_response(self) -> None:
        interface = AutoInterface(default_response="reject")
        result = interface.request_input("Choose an option", options=["approve", "reject"])
        assert result == "reject"

    def test_default_not_in_options_uses_first(self) -> None:
        interface = AutoInterface(default_response="unknown")
        result = interface.request_input("Choose an option", options=["yes", "no"])
        assert result == "yes"

    def test_no_options_returns_default(self) -> None:
        interface = AutoInterface(default_response="custom_value")
        result = interface.request_input("Enter something", input_type="text")
        assert result == "custom_value"

    def test_pattern_matching_response(self) -> None:
        interface = AutoInterface(
            default_response="default",
            responses={"deploy": "yes", "delete": "no"},
        )
        assert interface.request_input("Should I deploy?") == "yes"
        assert interface.request_input("Should I delete?") == "no"
        assert interface.request_input("Random question?") == "default"

    def test_pattern_matching_case_insensitive(self) -> None:
        interface = AutoInterface(
            responses={"PRODUCTION": "approve"},
        )
        result = interface.request_input("Deploy to production?", options=["approve", "reject"])
        assert result == "approve"

    def test_send_notification_silent(self) -> None:
        interface = AutoInterface()
        # Should not raise
        interface.send_notification("Test message", severity="warning", context={"key": "value"})


class TestConsoleInterface:
    """Tests for ConsoleInterface."""

    def test_send_notification_info(self) -> None:
        output = StringIO()
        console = MagicMock()
        console.print = lambda *args, **kwargs: output.write(str(args[0]) + "\n")

        interface = ConsoleInterface(console=console)
        interface.send_notification("Test message", severity="info")

        assert "[blue]ℹ[/] Test message" in output.getvalue()

    def test_send_notification_warning(self) -> None:
        output = StringIO()
        console = MagicMock()
        console.print = lambda *args, **kwargs: output.write(str(args[0]) + "\n")

        interface = ConsoleInterface(console=console)
        interface.send_notification("Warning message", severity="warning")

        assert "[yellow]⚠[/] Warning message" in output.getvalue()

    def test_send_notification_error(self) -> None:
        output = StringIO()
        console = MagicMock()
        console.print = lambda *args, **kwargs: output.write(str(args[0]) + "\n")

        interface = ConsoleInterface(console=console)
        interface.send_notification("Error message", severity="error")

        assert "[red]✗[/] Error message" in output.getvalue()

    def test_send_notification_success(self) -> None:
        output = StringIO()
        console = MagicMock()
        console.print = lambda *args, **kwargs: output.write(str(args[0]) + "\n")

        interface = ConsoleInterface(console=console)
        interface.send_notification("Success message", severity="success")

        assert "[green]✓[/] Success message" in output.getvalue()

    def test_send_notification_with_context(self) -> None:
        output = StringIO()
        console = MagicMock()
        console.print = lambda *args, **kwargs: output.write(str(args[0]) + "\n")

        interface = ConsoleInterface(console=console)
        interface.send_notification("Message", context={"key": "value"})

        output_text = output.getvalue()
        assert "key:" in output_text
        assert "value" in output_text


class TestServerInterface:
    """Tests for ServerInterface."""

    def test_request_input_raises_not_implemented(self) -> None:
        output = StringIO()
        console = MagicMock()
        console.print = lambda *args, **kwargs: output.write(str(args[0]) + "\n" if args else "\n")

        interface = ServerInterface(console=console)

        with pytest.raises(NotImplementedError) as exc_info:
            interface.request_input("Choose", options=["a", "b"])

        assert "async mode" in str(exc_info.value)

    def test_request_input_async_requires_registry(self) -> None:
        interface = ServerInterface()

        with pytest.raises(RuntimeError) as exc_info:
            import asyncio

            asyncio.run(interface.request_input_async("Choose"))

        assert "approval_registry" in str(exc_info.value)

    def test_send_notification(self) -> None:
        output = StringIO()
        console = MagicMock()
        console.print = lambda *args, **kwargs: output.write(str(args[0]) + "\n")

        interface = ServerInterface(console=console)
        interface.send_notification("Test message", severity="info")

        output_text = output.getvalue()
        assert "[notification]" in output_text
        assert "Test message" in output_text

    @pytest.mark.asyncio
    async def test_send_notification_async(self) -> None:
        output = StringIO()
        console = MagicMock()
        console.print = lambda *args, **kwargs: output.write(str(args[0]) + "\n")

        interface = ServerInterface(console=console)
        await interface.send_notification_async("Async message", severity="success")

        output_text = output.getvalue()
        assert "Async message" in output_text


class TestServerInterfaceAsync:
    """Async tests for ServerInterface with mock registry."""

    @pytest.mark.asyncio
    async def test_request_input_async_success(self) -> None:
        import asyncio

        mock_registry = MagicMock()
        future: asyncio.Future[str] = asyncio.Future()
        future.set_result("approve")
        mock_registry.request.return_value = future

        output = StringIO()
        console = MagicMock()
        console.print = lambda *args, **kwargs: output.write(str(args[0]) + "\n" if args else "\n")

        interface = ServerInterface(approval_registry=mock_registry, console=console)

        result = await interface.request_input_async(
            "Approve deployment?",
            options=["approve", "reject"],
            workflow_id="test-workflow",
            step_name="deploy",
        )

        assert result == "approve"
        mock_registry.request.assert_called_once_with("test-workflow", "deploy")

    @pytest.mark.asyncio
    async def test_request_input_async_timeout(self) -> None:
        import asyncio

        mock_registry = MagicMock()
        # Future that never completes
        future: asyncio.Future[str] = asyncio.Future()
        mock_registry.request.return_value = future

        output = StringIO()
        console = MagicMock()
        console.print = lambda *args, **kwargs: output.write(str(args[0]) + "\n" if args else "\n")

        interface = ServerInterface(approval_registry=mock_registry, console=console)

        with pytest.raises(TimeoutError) as exc_info:
            await interface.request_input_async(
                "Approve?",
                timeout_seconds=0.1,
                workflow_id="test",
                step_name="step",
            )

        assert "timed out" in str(exc_info.value)
        mock_registry.cancel.assert_called_once_with("test", "step", "Timeout")

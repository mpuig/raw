"""HumanInterface implementations."""

import asyncio
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


class ConsoleInterface:
    """Human interface using console (stdin/stdout).

    Used for interactive `raw run` mode where the user is at a terminal.
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize with optional Rich console."""
        self._console = console or Console()

    def request_input(
        self,
        prompt: str,
        *,
        options: list[str] | None = None,
        context: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
        input_type: str = "choice",
    ) -> str:
        """Request input from user via console.

        Args:
            prompt: Question to ask
            options: Available choices (for choice/approval types)
            context: Additional context to display
            timeout_seconds: Ignored for console (blocking input)
            input_type: Type of input ("choice", "text", "approval", "confirm")

        Returns:
            User's response
        """
        self._console.print()

        if context:
            context_lines = "\n".join(f"  [dim]{k}:[/] {v}" for k, v in context.items())
            self._console.print(Panel(context_lines, title="Context", border_style="dim"))

        if input_type == "confirm":
            options = options or ["yes", "no"]
            self._console.print(f"[bold]{prompt}[/]")
            response = Prompt.ask(
                "Confirm",
                choices=options,
                default=options[0] if options else "yes",
                console=self._console,
            )
        elif input_type == "text":
            response = Prompt.ask(f"[bold]{prompt}[/]", console=self._console)
        elif options:
            self._console.print(f"[bold]{prompt}[/]")
            self._console.print(f"[dim]Options: {', '.join(options)}[/]")
            default = options[0] if options else ""
            response = Prompt.ask(
                "Choice",
                choices=options,
                default=default,
                console=self._console,
            )
        else:
            response = Prompt.ask(f"[bold]{prompt}[/]", console=self._console)

        return response

    def send_notification(
        self,
        message: str,
        *,
        severity: str = "info",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Send notification to console.

        Args:
            message: Notification message
            severity: Message severity ("info", "warning", "error", "success")
            context: Additional context to include
        """
        style_map = {
            "info": ("blue", "ℹ"),
            "warning": ("yellow", "⚠"),
            "error": ("red", "✗"),
            "success": ("green", "✓"),
        }
        color, icon = style_map.get(severity, ("blue", "ℹ"))

        self._console.print(f"[{color}]{icon}[/] {message}")

        if context:
            for key, value in context.items():
                self._console.print(f"  [dim]{key}:[/] {value}")


class AutoInterface:
    """Human interface that auto-responds without user interaction.

    Useful for testing and CI/CD pipelines where human input isn't available.
    """

    def __init__(
        self,
        default_response: str = "approve",
        responses: dict[str, str] | None = None,
    ) -> None:
        """Initialize with default and per-prompt responses.

        Args:
            default_response: Default response for all prompts
            responses: Map of prompt substrings to specific responses
        """
        self._default = default_response
        self._responses = responses or {}

    def request_input(
        self,
        prompt: str,
        *,
        options: list[str] | None = None,
        context: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
        input_type: str = "choice",
    ) -> str:
        """Auto-respond to input requests."""
        for pattern, response in self._responses.items():
            if pattern.lower() in prompt.lower():
                return response

        if options and self._default in options:
            return self._default
        if options:
            return options[0]
        return self._default

    def send_notification(
        self,
        message: str,
        *,
        severity: str = "info",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Notifications are silently ignored in auto mode."""
        pass


class ServerInterface:
    """Human interface for server/daemon mode.

    Used with `raw serve` where approvals come via HTTP API.
    Notifications are logged rather than displayed.
    """

    def __init__(
        self,
        approval_registry: Any = None,
        console: Console | None = None,
    ) -> None:
        """Initialize with approval registry for async waiting.

        Args:
            approval_registry: ApprovalRegistry for Future-based waiting
            console: Console for logging notifications
        """
        self._registry = approval_registry
        self._console = console or Console()

    def request_input(
        self,
        prompt: str,
        *,
        options: list[str] | None = None,
        context: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
        input_type: str = "choice",
    ) -> str:
        """Request input via server - blocks until API response.

        In server mode, this logs the request and waits for the
        approval to be delivered via the HTTP API.
        """
        self._console.print()
        self._console.print(f"[bold yellow]⏸[/] [bold]Waiting for input:[/] {prompt}")
        if options:
            self._console.print(f"[dim]Options: {', '.join(options)}[/]")
        if context:
            self._console.print("[dim]Context:[/]")
            for key, value in context.items():
                self._console.print(f"  [dim]{key}:[/] {value}")
        self._console.print("[dim]Response can be submitted via HTTP API[/]")

        raise NotImplementedError(
            "ServerInterface.request_input requires async mode. "
            "Use request_input_async or wrap in asyncio.run()."
        )

    async def request_input_async(
        self,
        prompt: str,
        *,
        options: list[str] | None = None,
        context: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
        input_type: str = "choice",
        workflow_id: str = "unknown",
        step_name: str = "input",
    ) -> str:
        """Async request input - waits for API response via Future."""
        if self._registry is None:
            raise RuntimeError("ServerInterface requires approval_registry for async mode")

        self._console.print()
        self._console.print(f"[bold yellow]⏸[/] [bold]Waiting for input:[/] {prompt}")
        if options:
            self._console.print(f"[dim]Options: {', '.join(options)}[/]")

        future = self._registry.request(workflow_id, step_name)

        try:
            if timeout_seconds:
                response: str = await asyncio.wait_for(future, timeout=timeout_seconds)
            else:
                response = await future
            self._console.print(f"[green]✓[/] Received response: {response}")
            return response
        except asyncio.TimeoutError:
            self._registry.cancel(workflow_id, step_name, "Timeout")
            self._console.print("[red]✗[/] Request timeout")
            raise TimeoutError(f"Input request timed out after {timeout_seconds}s") from None

    def send_notification(
        self,
        message: str,
        *,
        severity: str = "info",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log notification to console."""
        style_map = {
            "info": ("blue", "ℹ"),
            "warning": ("yellow", "⚠"),
            "error": ("red", "✗"),
            "success": ("green", "✓"),
        }
        color, icon = style_map.get(severity, ("blue", "ℹ"))

        self._console.print(f"[{color}]{icon}[/] [dim][notification][/] {message}")

    async def send_notification_async(
        self,
        message: str,
        *,
        severity: str = "info",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Async notification - same as sync for now."""
        self.send_notification(message, severity=severity, context=context)

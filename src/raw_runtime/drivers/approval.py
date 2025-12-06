"""Approval handler implementations."""

from typing import Any

from rich.console import Console
from rich.prompt import Confirm, Prompt


class ConsoleApprovalHandler:
    """Interactive console approval for `raw run`.

    Prompts the user via stdin and returns their decision immediately.
    """

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def request_approval(
        self,
        step_name: str,
        prompt: str,
        options: list[str],
        context: dict[str, Any],
        timeout_seconds: float | None,  # noqa: ARG002
    ) -> str:
        """Request approval via console prompt."""
        self.console.print()
        self.console.print(f"[bold yellow]⏸[/] [bold]Approval Required:[/] {step_name}")
        self.console.print(f"  {prompt}")

        if context:
            self.console.print("[dim]Context:[/]")
            for key, value in context.items():
                self.console.print(f"  [dim]{key}:[/] {value}")

        if len(options) == 2 and set(options) == {"approve", "reject"}:
            approved = Confirm.ask("Approve?", default=False)
            return "approve" if approved else "reject"
        else:
            self.console.print(f"[dim]Options: {', '.join(options)}[/]")
            choice = Prompt.ask("Decision", choices=options)
            return choice


class AutoApprovalHandler:
    """Auto-approve all requests (for testing)."""

    def __init__(self, decision: str = "approve") -> None:
        self.decision = decision

    def request_approval(
        self,
        step_name: str,  # noqa: ARG002
        prompt: str,  # noqa: ARG002
        options: list[str],  # noqa: ARG002
        context: dict[str, Any],  # noqa: ARG002
        timeout_seconds: float | None,  # noqa: ARG002
    ) -> str:
        """Auto-approve without prompting."""
        return self.decision

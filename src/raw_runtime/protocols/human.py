"""HumanInterface protocol definition.

Abstracts human interaction channels for workflows, enabling:
- Console prompts (raw run)
- Web dashboard (raw serve)
- Slack/Teams integrations
- Email notifications
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class HumanInterface(Protocol):
    """Protocol for human interaction channels.

    Implementations handle the mechanics of communicating with humans
    across different channels (console, web, Slack, email, etc.).
    """

    def request_input(
        self,
        prompt: str,
        *,
        options: list[str] | None = None,
        context: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
        input_type: str = "choice",
    ) -> str:
        """Request input from a human.

        Args:
            prompt: Question or request to show the user
            options: Available choices (for choice/approval types)
            context: Additional context to display
            timeout_seconds: Maximum time to wait for response
            input_type: Type of input ("choice", "text", "approval", "confirm")

        Returns:
            The user's response

        Raises:
            TimeoutError: If timeout is exceeded
        """
        ...

    def send_notification(
        self,
        message: str,
        *,
        severity: str = "info",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Send a notification to the human.

        Args:
            message: Notification message
            severity: Message severity ("info", "warning", "error", "success")
            context: Additional context to include
        """
        ...


@runtime_checkable
class AsyncHumanInterface(Protocol):
    """Async version of HumanInterface for non-blocking operations."""

    async def request_input_async(
        self,
        prompt: str,
        *,
        options: list[str] | None = None,
        context: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
        input_type: str = "choice",
    ) -> str:
        """Async version of request_input."""
        ...

    async def send_notification_async(
        self,
        message: str,
        *,
        severity: str = "info",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Async version of send_notification."""
        ...

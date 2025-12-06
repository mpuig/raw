"""ApprovalHandler protocol definition."""

from typing import Any, Protocol


class ApprovalHandler(Protocol):
    """Protocol for approval handlers."""

    def request_approval(
        self,
        step_name: str,
        prompt: str,
        options: list[str],
        context: dict[str, Any],
        timeout_seconds: float | None,
    ) -> str:
        """Request approval and return the decision.

        Args:
            step_name: Name of the step requiring approval
            prompt: Question to ask the user
            options: Available choices
            context: Additional context to show
            timeout_seconds: Maximum time to wait

        Returns:
            The user's decision (one of the options)
        """
        ...

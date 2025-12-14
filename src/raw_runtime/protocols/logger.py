"""Logger protocol for workflow output abstraction.

Defines abstractions for logging output that can be swapped in different contexts.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class WorkflowLogger(Protocol):
    """Protocol for workflow logging output.

    Allows swapping Rich console for non-CLI contexts (testing, batch execution).
    """

    def print(self, message: str) -> None:
        """Print a message to the output.

        Args:
            message: Message to print (may contain Rich markup)
        """
        ...


class RichConsoleLogger:
    """Default logger implementation using Rich console."""

    def __init__(self) -> None:
        from rich.console import Console

        self._console = Console()

    def print(self, message: str) -> None:
        self._console.print(message)


class NullLogger:
    """Silent logger for testing or batch execution."""

    def print(self, message: str) -> None:
        pass


class ListLogger:
    """Logger that captures messages to a list for testing."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def print(self, message: str) -> None:
        self.messages.append(message)


# Module-level default logger
_default_logger: WorkflowLogger | None = None


def get_logger() -> WorkflowLogger:
    """Get the current workflow logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = RichConsoleLogger()
    return _default_logger


def set_logger(logger: WorkflowLogger | None) -> None:
    """Set the workflow logger.

    Args:
        logger: Logger to use, or None to reset to default
    """
    global _default_logger
    _default_logger = logger

"""Composition root for engine dependency injection.

Centralizes the creation and wiring of engine components.
This is the single place where concrete implementations are bound to protocols,
following the Composition Root pattern from clean architecture.

Usage:
    # Default usage (production)
    runner = Container.workflow_runner()

    # Testing with mocks
    Container.set_backend(MockBackend())
    Container.set_storage(MockStorage())
    runner = Container.workflow_runner()

    # Reset to defaults
    Container.reset()
"""

from typing import TypeVar

from raw.engine.backends import LocalRunStorage, SubprocessBackend
from raw.engine.protocols import ExecutionBackend, RunStorage
from raw.engine.runner import WorkflowRunner

T = TypeVar("T")


class Container:
    """Service container for engine dependencies.

    Provides lazy initialization of default implementations and
    allows overriding for testing purposes.
    """

    _backend: ExecutionBackend | None = None
    _storage: RunStorage | None = None

    @classmethod
    def backend(cls) -> ExecutionBackend:
        """Get the execution backend.

        Returns SubprocessBackend by default.
        """
        if cls._backend is None:
            cls._backend = SubprocessBackend()
        return cls._backend

    @classmethod
    def storage(cls) -> RunStorage:
        """Get the run storage.

        Returns LocalRunStorage by default.
        """
        if cls._storage is None:
            cls._storage = LocalRunStorage()
        return cls._storage

    @classmethod
    def workflow_runner(cls) -> WorkflowRunner:
        """Create a WorkflowRunner with current dependencies.

        This is the main factory method for workflow execution.
        """
        return WorkflowRunner(
            backend=cls.backend(),
            storage=cls.storage(),
        )

    @classmethod
    def set_backend(cls, backend: ExecutionBackend | None) -> None:
        """Override the execution backend.

        Pass None to reset to default on next access.
        """
        cls._backend = backend

    @classmethod
    def set_storage(cls, storage: RunStorage | None) -> None:
        """Override the run storage.

        Pass None to reset to default on next access.
        """
        cls._storage = storage

    @classmethod
    def reset(cls) -> None:
        """Reset all overrides to defaults.

        Call this in test teardown to ensure clean state.
        """
        cls._backend = None
        cls._storage = None


# Convenience functions for common operations


def get_runner() -> WorkflowRunner:
    """Get a WorkflowRunner with default dependencies.

    Shorthand for Container.workflow_runner().
    """
    return Container.workflow_runner()

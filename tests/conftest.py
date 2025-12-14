"""Shared pytest fixtures for RAW tests.

Provides common fixtures for mocking engine components and utilities.
"""

import socket

import pytest

from raw.engine import Container
from raw.engine.mocks import MockBackend, MockStorage
from raw.engine.protocols import RunResult


@pytest.fixture
def mock_backend() -> MockBackend:
    """Fixture that sets up and tears down a mock backend via Container.

    Yields:
        MockBackend instance configured to return successful results
    """
    result = RunResult(
        exit_code=0,
        stdout="success",
        stderr="",
        duration_seconds=0.1,
    )
    backend = MockBackend(result)
    Container.set_backend(backend)
    yield backend
    Container.reset()


@pytest.fixture
def mock_storage() -> MockStorage:
    """Fixture that sets up and tears down a mock storage via Container.

    Yields:
        MockStorage instance for tracking filesystem operations
    """
    storage = MockStorage()
    Container.set_storage(storage)
    yield storage
    Container.reset()


@pytest.fixture
def failing_backend() -> MockBackend:
    """Fixture that provides a mock backend configured to return failures.

    Yields:
        MockBackend instance configured to return exit code 1
    """
    result = RunResult(
        exit_code=1,
        stdout="",
        stderr="Error: test failure",
        duration_seconds=0.1,
    )
    backend = MockBackend(result)
    Container.set_backend(backend)
    yield backend
    Container.reset()


@pytest.fixture
def free_port() -> int:
    """Get a free port for testing server components.

    Returns:
        Available port number
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

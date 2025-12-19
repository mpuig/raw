"""Base protocol and models for queue backends."""

from datetime import datetime
from typing import Any, AsyncIterator, Protocol

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Immutable message model for queue operations.

    Represents a single message in the queue with all necessary metadata
    for processing, acknowledgment, and tracking.
    """

    id: str = Field(..., description="Unique message identifier")
    payload: dict[str, Any] = Field(..., description="Message payload data")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional message metadata"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Message creation timestamp"
    )
    receipt_handle: str | None = Field(
        None, description="Backend-specific receipt handle for acknowledgment"
    )
    retry_count: int = Field(0, description="Number of processing attempts")

    class Config:
        frozen = True  # Immutable for safety


class QueueConfig(BaseModel):
    """Base configuration for queue backends.

    Provides common settings that all queue backends should support.
    Backend-specific configs should inherit from this.
    """

    max_retries: int = Field(3, description="Maximum retry attempts for failed messages")
    visibility_timeout: int = Field(
        30, description="Message visibility timeout in seconds"
    )
    batch_size: int = Field(10, description="Number of messages to fetch per batch")
    poll_interval: float = Field(
        1.0, description="Polling interval in seconds between batch fetches"
    )


class QueueBackend(Protocol):
    """Protocol for async queue operations.

    Defines the contract that all queue backend implementations must follow.
    This enables loose coupling and easy testing through mock implementations.
    """

    async def publish(self, payload: dict[str, Any], metadata: dict[str, Any] | None = None) -> str:
        """Publish a message to the queue.

        Args:
            payload: Message payload data
            metadata: Optional metadata to attach to the message

        Returns:
            Message ID assigned by the backend

        Raises:
            ServiceError: If publishing fails
        """
        ...

    async def publish_batch(self, messages: list[dict[str, Any]]) -> list[str]:
        """Publish multiple messages in a single batch operation.

        Args:
            messages: List of message payloads to publish

        Returns:
            List of message IDs in the same order as input

        Raises:
            ServiceError: If batch publishing fails
        """
        ...

    async def consume(self) -> AsyncIterator[Message]:
        """Consume messages from the queue.

        Yields:
            Messages as they become available

        Raises:
            ServiceError: If consuming fails
        """
        ...

    async def ack(self, message: Message) -> None:
        """Acknowledge successful processing of a message.

        Args:
            message: The message to acknowledge

        Raises:
            ServiceError: If acknowledgment fails
        """
        ...

    async def nack(self, message: Message, requeue: bool = True) -> None:
        """Negative acknowledge - signal failed processing.

        Args:
            message: The message that failed processing
            requeue: Whether to requeue the message for retry

        Raises:
            ServiceError: If negative acknowledgment fails
        """
        ...

    async def close(self) -> None:
        """Close the queue connection and cleanup resources.

        Should be called when shutting down to ensure graceful cleanup.
        """
        ...

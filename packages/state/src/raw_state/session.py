"""Session management for conversations and workflows."""

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from raw_state.backends.base import StateBackend


class Session(BaseModel):
    """Represents a conversation or workflow session.

    Immutable data structure containing session metadata and state.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, str] = Field(default_factory=dict)

    class Config:
        frozen = True

    def update(self, **kwargs: Any) -> "Session":
        """Create new session with updated fields.

        Args:
            **kwargs: Fields to update

        Returns:
            New Session instance with updated values

        Note:
            Automatically updates updated_at timestamp.
        """
        updates = kwargs.copy()
        updates["updated_at"] = datetime.now(timezone.utc)
        return self.model_copy(update=updates)


class SessionManager:
    """Manages session lifecycle with automatic serialization.

    Provides high-level interface for creating, retrieving, and managing
    conversation/workflow sessions. Handles JSON serialization and TTL
    management automatically.
    """

    def __init__(self, backend: StateBackend, prefix: str = "session:"):
        """Initialize session manager.

        Args:
            backend: State backend implementation (Redis/PostgreSQL)
            prefix: Key prefix for namespacing sessions (default: "session:")

        Note:
            Prefix allows multiple session types (conversations, workflows)
            to coexist in the same backend.
        """
        self.backend = backend
        self.prefix = prefix

    def _make_key(self, session_id: str) -> str:
        """Generate storage key from session ID.

        Args:
            session_id: Unique session identifier

        Returns:
            Prefixed key for backend storage
        """
        return f"{self.prefix}{session_id}"

    async def create_session(
        self,
        data: dict[str, Any] | None = None,
        metadata: dict[str, str] | None = None,
        ttl: int | None = None,
    ) -> Session:
        """Create new session with optional TTL.

        Args:
            data: Initial session data
            metadata: Session metadata (e.g., user_id, conversation_type)
            ttl: Optional time-to-live in seconds

        Returns:
            Newly created Session instance
        """
        session = Session(
            data=data or {},
            metadata=metadata or {},
        )
        key = self._make_key(session.id)
        value = session.model_dump_json()
        await self.backend.set(key, value, ttl=ttl)
        return session

    async def get_session(self, session_id: str) -> Session | None:
        """Retrieve session by ID.

        Args:
            session_id: Unique session identifier

        Returns:
            Session instance if found, None otherwise
        """
        key = self._make_key(session_id)
        value = await self.backend.get(key)
        if value is None:
            return None

        data = json.loads(value)
        return Session(**data)

    async def update_session(
        self,
        session_id: str,
        data: dict[str, Any] | None = None,
        metadata: dict[str, str] | None = None,
        ttl: int | None = None,
    ) -> Session | None:
        """Update existing session.

        Args:
            session_id: Unique session identifier
            data: Updated session data (merged with existing)
            metadata: Updated metadata (merged with existing)
            ttl: Optional new TTL in seconds

        Returns:
            Updated Session instance, or None if not found
        """
        session = await self.get_session(session_id)
        if session is None:
            return None

        # Merge updates with existing data
        updated_data = session.data.copy()
        if data is not None:
            updated_data.update(data)

        updated_metadata = session.metadata.copy()
        if metadata is not None:
            updated_metadata.update(metadata)

        # Create updated session
        updated_session = session.update(
            data=updated_data,
            metadata=updated_metadata,
        )

        # Save back to storage
        key = self._make_key(session_id)
        value = updated_session.model_dump_json()
        await self.backend.set(key, value, ttl=ttl)

        return updated_session

    async def delete_session(self, session_id: str) -> bool:
        """Delete session by ID.

        Args:
            session_id: Unique session identifier

        Returns:
            True if session was deleted, False if not found
        """
        key = self._make_key(session_id)
        return await self.backend.delete(key)

    async def exists(self, session_id: str) -> bool:
        """Check if session exists.

        Args:
            session_id: Unique session identifier

        Returns:
            True if session exists, False otherwise
        """
        key = self._make_key(session_id)
        return await self.backend.exists(key)

    async def set_ttl(self, session_id: str, ttl: int) -> bool:
        """Set TTL on existing session.

        Args:
            session_id: Unique session identifier
            ttl: Time-to-live in seconds

        Returns:
            True if TTL was set, False if session not found
        """
        key = self._make_key(session_id)
        return await self.backend.expire(key, ttl)

    async def list_sessions(self, pattern: str = "*") -> list[str]:
        """List session IDs matching pattern.

        Args:
            pattern: Pattern to match session IDs (default: "*" for all)

        Returns:
            List of matching session IDs (without prefix)
        """
        key_pattern = f"{self.prefix}{pattern}"
        keys = await self.backend.keys(key_pattern)

        # Strip prefix from keys to get session IDs
        prefix_len = len(self.prefix)
        return [key[prefix_len:] for key in keys]

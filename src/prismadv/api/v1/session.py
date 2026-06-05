"""Session management for multi-user support."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Session:
    """User session with isolated storage."""

    id: str
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        """Update last accessed time."""
        self.last_accessed = time.time()

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if session is expired based on last access time.

        Args:
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if session has expired
        """
        return (time.time() - self.last_accessed) > ttl_seconds


class SessionManager:
    """Manages user sessions with automatic cleanup.

    Thread-safe for concurrent access (uses dict which is thread-safe in CPython).
    """

    def __init__(self, ttl_seconds: int = 3600):
        """Initialize session manager.

        Args:
            ttl_seconds: Session time-to-live in seconds (default 1 hour)
        """
        self._sessions: dict[str, Session] = {}
        self._ttl_seconds = ttl_seconds

    def create_session(self) -> Session:
        """Create a new session.

        Returns:
            New Session instance
        """
        session_id = str(uuid.uuid4())
        session = Session(id=session_id)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        """Get session by ID and update last accessed time.

        Args:
            session_id: Session identifier

        Returns:
            Session if found and not expired, None otherwise
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if session.is_expired(self._ttl_seconds):
            # Remove expired session
            self._sessions.pop(session_id, None)
            return None

        # Touch session to update last accessed time
        session.touch()
        return session

    def get_or_create_session(self, session_id: str | None) -> Session:
        """Get existing session or create new one.

        Args:
            session_id: Optional session identifier

        Returns:
            Existing or new Session instance
        """
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session

        # Create new session if not found or expired
        return self.create_session()

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if not found
        """
        return self._sessions.pop(session_id, None) is not None

    def cleanup_expired(self) -> int:
        """Remove all expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        expired = [
            sid
            for sid, session in self._sessions.items()
            if session.is_expired(self._ttl_seconds)
        ]

        for sid in expired:
            self._sessions.pop(sid, None)

        return len(expired)

    def session_count(self) -> int:
        """Get current number of active sessions.

        Returns:
            Number of sessions
        """
        return len(self._sessions)

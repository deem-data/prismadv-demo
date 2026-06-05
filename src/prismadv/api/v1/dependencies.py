"""FastAPI dependencies for session and storage management."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Cookie, Depends, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from prismadv.api.v1.session import Session, SessionManager
from prismadv.api.v1.storage import SessionStorage, StorageManager

# Shared rate limiter instance — used by app.py and route decorators
limiter = Limiter(key_func=get_remote_address)

logger = logging.getLogger(__name__)


def _clear_litellm_cache() -> None:
    """Clear litellm's in-memory response cache for a clean session start."""
    try:
        import litellm
        if litellm.cache is not None:
            litellm.cache.cache.flush_cache()
            logger.debug("Cleared litellm response cache for new session")
    except Exception:
        pass

# Global instances (initialized in app.py)
_session_manager: SessionManager | None = None
_storage_manager: StorageManager | None = None


def init_managers(session_manager: SessionManager, storage_manager: StorageManager) -> None:
    """Initialize global manager instances.

    Called from app.py during startup.

    Args:
        session_manager: SessionManager instance
        storage_manager: StorageManager instance
    """
    global _session_manager, _storage_manager
    _session_manager = session_manager
    _storage_manager = storage_manager


def get_session_manager() -> SessionManager:
    """Get the global SessionManager instance.

    Returns:
        SessionManager instance

    Raises:
        RuntimeError: If managers not initialized
    """
    if _session_manager is None:
        raise RuntimeError("SessionManager not initialized. Call init_managers() first.")
    return _session_manager


def get_storage_manager() -> StorageManager:
    """Get the global StorageManager instance.

    Returns:
        StorageManager instance

    Raises:
        RuntimeError: If managers not initialized
    """
    if _storage_manager is None:
        raise RuntimeError("StorageManager not initialized. Call init_managers() first.")
    return _storage_manager


def get_session(
    response: Response,
    session_id: Annotated[str | None, Cookie()] = None,
    session_manager: SessionManager = Depends(get_session_manager),
) -> Session:
    """Get or create user session from cookie.

    This dependency automatically handles session creation and validation,
    and sets the session cookie in the response.

    Args:
        response: FastAPI Response object to set cookie
        session_id: Session ID from cookie (optional)
        session_manager: SessionManager instance

    Returns:
        Valid Session instance (existing or new)
    """
    # Detect whether this is a genuinely new session so we can clear litellm cache
    existing = session_manager.get_session(session_id) if session_id else None
    session = existing if existing else session_manager.create_session()
    if existing is None:
        _clear_litellm_cache()

    # Set session cookie in response
    response.set_cookie(
        key="session_id",
        value=session.id,
        max_age=3600,  # 1 hour
        httponly=True,
        samesite="lax",
    )

    return session


def get_storage(
    session: Session = Depends(get_session),
    storage_manager: StorageManager = Depends(get_storage_manager),
) -> SessionStorage:
    """Get session-isolated storage.

    Args:
        session: Current session
        storage_manager: StorageManager instance

    Returns:
        SessionStorage for current session
    """
    return storage_manager.get_storage(session.id)

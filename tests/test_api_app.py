"""Tests for FastAPI application."""

import pytest


def test_session_manager():
    """Test SessionManager basic functionality."""
    from prismadv.api.v1.session import SessionManager

    manager = SessionManager(ttl_seconds=10)

    # Create session
    session = manager.create_session()
    assert session.id is not None
    assert manager.session_count() == 1

    # Get session
    retrieved = manager.get_session(session.id)
    assert retrieved is not None
    assert retrieved.id == session.id

    # Get non-existent session
    assert manager.get_session("nonexistent") is None


def test_session_expiry():
    """Test session expiration."""
    import time

    from prismadv.api.v1.session import SessionManager

    manager = SessionManager(ttl_seconds=1)  # 1 second TTL

    # Create session
    session = manager.create_session()
    assert manager.get_session(session.id) is not None

    # Wait for expiry
    time.sleep(1.1)

    # Session should be expired
    assert manager.get_session(session.id) is None
    assert manager.session_count() == 0


def test_storage_manager():
    """Test StorageManager basic functionality."""
    from prismadv.api.v1.storage import StorageManager

    manager = StorageManager()

    # Get storage for session
    storage1 = manager.get_storage("session-1")
    assert storage1.session_id == "session-1"
    assert manager.storage_count() == 1

    # Store file
    file_id = storage1.store_file("test.txt", "hello world")
    assert file_id is not None

    # Retrieve file
    stored_file = storage1.get_file(file_id)
    assert stored_file is not None
    assert stored_file.name == "test.txt"
    assert stored_file.content == "hello world"

    # Different session has different storage
    storage2 = manager.get_storage("session-2")
    assert storage2.get_file(file_id) is None  # File not in session-2


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
def test_app_health_check():
    """Test FastAPI app health check."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app

    with TestClient(app) as client:
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "prismadv-api"


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
def test_session_cookie():
    """Test session cookie creation."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app

    with TestClient(app) as client:
        # First request should create session
        response1 = client.get("/api/v1/session/info")
        assert response1.status_code == 200
        data1 = response1.json()
        session_id1 = data1["sessionId"]
        assert session_id1 is not None

        # Session cookie should be set
        assert "session_id" in response1.cookies

        # Second request with same cookie should return same session
        response2 = client.get("/api/v1/session/info")
        data2 = response2.json()
        session_id2 = data2["sessionId"]

        assert session_id2 == session_id1  # Same session

"""Tests for file upload endpoints."""

import io

import pytest


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
def test_upload_task_file_python():
    """Test uploading Python task file."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app

    with TestClient(app) as client:
        # Create fake Python file
        content = "def hello():\n    print('Hello, World!')\n"
        files = {"file": ("test.py", io.BytesIO(content.encode()), "text/plain")}

        response = client.post("/api/v1/files/task", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test.py"
        assert data["language"] == "python"
        assert data["content"] == content
        assert data["size"] == len(content)
        assert "id" in data
        assert "uploadedAt" in data


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
def test_upload_task_file_sql():
    """Test uploading SQL task file."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app

    with TestClient(app) as client:
        content = "SELECT * FROM users WHERE age > 18;"
        files = {"file": ("query.sql", io.BytesIO(content.encode()), "text/plain")}

        response = client.post("/api/v1/files/task", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "query.sql"
        assert data["language"] == "sql"
        assert data["content"] == content


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
def test_upload_task_file_with_custom_name():
    """Test uploading file with custom name."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app

    with TestClient(app) as client:
        content = "print('test')"
        files = {"file": ("original.py", io.BytesIO(content.encode()), "text/plain")}
        data_form = {"name": "custom_name.py"}

        response = client.post("/api/v1/files/task", files=files, data=data_form)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "custom_name.py"


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
def test_upload_task_file_invalid_extension():
    """Test uploading file with invalid extension."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app

    with TestClient(app) as client:
        content = "test content"
        files = {"file": ("test.txt", io.BytesIO(content.encode()), "text/plain")}

        response = client.post("/api/v1/files/task", files=files)

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
def test_upload_dataset_file():
    """Test uploading CSV dataset."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app

    with TestClient(app) as client:
        # Create fake CSV
        csv_content = "name,age,city\nAlice,30,NYC\nBob,25,LA\n"
        files = {"file": ("data.csv", io.BytesIO(csv_content.encode()), "text/csv")}

        response = client.post("/api/v1/files/dataset", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "data.csv"
        assert data["rowCount"] == 2
        assert data["columnCount"] == 3
        assert len(data["columns"]) == 3
        assert data["columns"][0]["name"] == "name"
        assert data["columns"][1]["name"] == "age"
        assert data["columns"][2]["name"] == "city"
        assert "id" in data


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
def test_upload_dataset_empty():
    """Test uploading empty CSV."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app

    with TestClient(app) as client:
        files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}

        response = client.post("/api/v1/files/dataset", files=files)

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
def test_upload_dataset_invalid_extension():
    """Test uploading non-CSV file as dataset."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app

    with TestClient(app) as client:
        content = "not a csv"
        files = {"file": ("data.txt", io.BytesIO(content.encode()), "text/plain")}

        response = client.post("/api/v1/files/dataset", files=files)

        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
def test_session_isolation_for_files():
    """Test that different sessions have isolated file storage."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app

    # Client 1 uploads a file
    with TestClient(app) as client1:
        content1 = "print('client1')"
        files1 = {"file": ("test1.py", io.BytesIO(content1.encode()), "text/plain")}
        response1 = client1.post("/api/v1/files/task", files=files1)
        assert response1.status_code == 201
        file_id1 = response1.json()["id"]

    # Client 2 (different session) uploads a file
    with TestClient(app) as client2:
        content2 = "print('client2')"
        files2 = {"file": ("test2.py", io.BytesIO(content2.encode()), "text/plain")}
        response2 = client2.post("/api/v1/files/task", files=files2)
        assert response2.status_code == 201
        file_id2 = response2.json()["id"]

    # File IDs should be different (different sessions)
    assert file_id1 != file_id2

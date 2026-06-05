"""Tests for constraint generation endpoint."""

import io
import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
def test_generate_constraints_files_not_found():
    """Test constraint generation with non-existent files."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app

    with TestClient(app) as client:
        request_data = {
            "taskFileId": "nonexistent-task",
            "datasetId": "nonexistent-dataset",
        }

        response = client.post("/api/v1/constraints/generate", json=request_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
@pytest.mark.skipif(
    not pytest.importorskip("dspy", reason="DSPy not installed"),
    reason="DSPy not installed",
)
def test_generate_constraints_missing_api_key():
    """Test constraint generation reports failure via job status when API key missing."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app

    with TestClient(app) as client:
        # Upload task file
        task_content = "df = df[df['age'] > 18]"
        task_files = {"file": ("task.py", io.BytesIO(task_content.encode()), "text/plain")}
        task_response = client.post("/api/v1/files/task", files=task_files)
        task_id = task_response.json()["id"]

        # Upload dataset
        csv_content = "age,name\n25,Alice\n30,Bob\n"
        dataset_files = {"file": ("data.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        dataset_response = client.post("/api/v1/files/dataset", files=dataset_files)
        dataset_id = dataset_response.json()["id"]

        # Mock create_lm_from_env to raise error (simulating missing API key)
        with patch("prismadv.api.v1.routes.constraints.create_lm_from_env") as mock_lm:
            mock_lm.side_effect = ValueError("No API key found")

            request_data = {
                "taskFileId": task_id,
                "datasetId": dataset_id,
            }
            response = client.post("/api/v1/constraints/generate", json=request_data)

            # Endpoint returns 200 with processing status (async)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processing"
            job_id = data["jobId"]

            # Poll for job status - should fail
            for _ in range(10):
                time.sleep(0.1)
                status_response = client.get(f"/api/v1/constraints/jobs/{job_id}")
                status_data = status_response.json()
                if status_data["status"] == "failed":
                    break

            assert status_data["status"] == "failed"
            assert "Failed" in status_data["currentStep"]


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
@pytest.mark.skipif(
    not pytest.importorskip("dspy", reason="DSPy not installed"),
    reason="DSPy not installed",
)
def test_generate_constraints_success_mocked():
    """Test successful constraint generation with mocked LLM."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app
    from prismadv.generation import GenerationContext
    from prismadv.ir import AssumptionIR, ConstraintIR, SourceSpan

    with TestClient(app) as client:
        # Upload task file
        task_content = "df = df[df['age'] > 18]"
        task_files = {"file": ("task.py", io.BytesIO(task_content.encode()), "text/plain")}
        task_response = client.post("/api/v1/files/task", files=task_files)
        task_id = task_response.json()["id"]

        # Upload dataset
        csv_content = "age,name\n25,Alice\n30,Bob\n"
        dataset_files = {"file": ("data.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        dataset_response = client.post("/api/v1/files/dataset", files=dataset_files)
        dataset_id = dataset_response.json()["id"]

        # Use the real profile from the dataset upload
        # Create a minimal mock context using MagicMock for profile
        with patch("prismadv.api.v1.routes.constraints.create_lm_from_env") as mock_lm, \
             patch("prismadv.api.v1.routes.constraints.GenerationOrchestrator") as mock_orch:

            # Mock LM creation
            mock_lm.return_value = MagicMock()

            # Mock orchestrator to return a simple context
            mock_instance = MagicMock()
            mock_context = MagicMock(spec=GenerationContext)
            mock_context.task_code = task_content
            mock_context.task_file_name = "task.py"
            mock_context.dataset_path = "/tmp/data.csv"
            mock_context.task_description = "Analysis of data.csv"
            mock_context.accessed_columns = ["age"]
            mock_context.assumptions = [
                AssumptionIR(
                    id="assumption-1",
                    text="Age must be greater than 18",
                    sources=[SourceSpan(file="task.py", start_line=1, end_line=1)],
                    columns=["age"],
                    constraint_type="range",
                )
            ]
            mock_context.constraints = [
                ConstraintIR(
                    id="constraint-1",
                    assumption_ids=["assumption-1"],
                    column="age",
                    columns=["age"],
                    column_type="numerical",
                    type="range",
                    label="age (range)",
                )
            ]
            # Mock the profile with a simple MagicMock
            mock_context.dataset_profile = MagicMock()
            mock_context.dataset_profile.dataset.columns = []
            mock_context.llm_cost = 0.001  # Mock LLM cost
            mock_context.cost_breakdown = {"column_detection": 0.0001, "assumption_extraction": 0.0005, "constraint_generation": 0.0004}
            mock_context.warnings = []

            mock_instance.generate.return_value = mock_context
            mock_orch.return_value = mock_instance

            # Generate constraints - returns immediately with processing status
            request_data = {
                "taskFileId": task_id,
                "datasetId": dataset_id,
            }
            response = client.post("/api/v1/constraints/generate", json=request_data)

            assert response.status_code == 200
            data = response.json()

            # Initial response should be processing
            assert data["status"] == "processing"
            assert "jobId" in data
            job_id = data["jobId"]

            # Poll for completion
            for _ in range(20):  # Max 2 seconds
                time.sleep(0.1)
                status_response = client.get(f"/api/v1/constraints/jobs/{job_id}")
                status_data = status_response.json()
                if status_data["status"] == "completed":
                    break

            # Verify final response
            assert status_data["status"] == "completed"
            assert "result" in status_data

            result = status_data["result"]
            assert "constraints" in result
            assert "flowGraph" in result
            assert "codeAnnotations" in result
            assert "statistics" in result

            # Verify constraints were returned
            assert len(result["constraints"]) > 0


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
@pytest.mark.skipif(
    not pytest.importorskip("dspy", reason="DSPy not installed"),
    reason="DSPy not installed",
)
def test_generate_constraints_with_options():
    """Test constraint generation with custom options starts async processing."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app

    with TestClient(app) as client:
        # Upload task file
        task_content = "df = df[df['age'] > 18]"
        task_files = {"file": ("task.py", io.BytesIO(task_content.encode()), "text/plain")}
        task_response = client.post("/api/v1/files/task", files=task_files)
        task_id = task_response.json()["id"]

        # Upload dataset
        csv_content = "age,name\n25,Alice\n30,Bob\n"
        dataset_files = {"file": ("data.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        dataset_response = client.post("/api/v1/files/dataset", files=dataset_files)
        dataset_id = dataset_response.json()["id"]

        # Request with options - should return processing immediately
        request_data = {
            "taskFileId": task_id,
            "datasetId": dataset_id,
            "options": {
                "llmProvider": "openai",
                "model": "gpt-4o-mini",
            },
        }

        response = client.post("/api/v1/constraints/generate", json=request_data)

        # Async endpoint always returns 200 with processing status
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "jobId" in data


@pytest.mark.skipif(
    not pytest.importorskip("fastapi", reason="FastAPI not installed"),
    reason="FastAPI not installed",
)
def test_get_job_status_not_found():
    """Test getting status of non-existent job."""
    from fastapi.testclient import TestClient

    from prismadv.api.v1.app import app

    with TestClient(app) as client:
        response = client.get("/api/v1/constraints/jobs/nonexistent-job-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

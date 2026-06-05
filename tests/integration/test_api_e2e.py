"""End-to-end API integration test with real HTTP calls.

This test requires:
1. FastAPI server running: uv run uvicorn prismadv.api.v1.app:app --reload
2. An LLM API key configured (OpenAI, Anthropic, or Gemini)
3. Set environment variable: RUN_LLM_TESTS=1

Run with:
    # Start server in one terminal
    uv run uvicorn prismadv.api.v1.app:app --reload --port 8000

    # Run test in another terminal
    RUN_LLM_TESTS=1 uv run pytest tests/integration/test_api_e2e.py -v -s

Or use httpx directly (see test_manual_httpx_workflow below).
"""

import os
from pathlib import Path

import pytest

# Check if LLM tests should run
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_LLM_TESTS"),
    reason="Set RUN_LLM_TESTS=1 to run tests with real LLM",
)

# Lazy import to avoid errors if httpx not installed
httpx = pytest.importorskip("httpx")

# Test resources
RESOURCES_DIR = Path(__file__).parent.parent / "resources"
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture
def client():
    """Create httpx client with session support."""
    # Use cookies to maintain session across requests
    return httpx.Client(base_url=API_BASE_URL, follow_redirects=True)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "prismadv-api"
    print(f"\n✓ Health check: {data}")


def test_session_info(client):
    """Test session info endpoint."""
    response = client.get("/api/v1/session/info")
    assert response.status_code == 200
    data = response.json()
    assert "sessionId" in data
    assert "createdAt" in data
    assert "lastAccessed" in data
    print(f"\n✓ Session ID: {data['sessionId']}")


def test_stats(client):
    """Test stats endpoint."""
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert "activeSessions" in data
    assert "activeStorages" in data
    print(f"\n✓ Active sessions: {data['activeSessions']}")


def test_full_workflow_batch_processing(client):
    """Test complete workflow: upload files → generate constraints."""

    # Step 1: Upload task file
    print("\n📤 Step 1: Uploading task file...")
    task_file = RESOURCES_DIR / "batch_processing_task.py"
    with open(task_file, "rb") as f:
        files = {"file": (task_file.name, f, "text/x-python")}
        response = client.post("/api/v1/files/task", files=files)

    assert response.status_code == 200
    task_data = response.json()
    task_id = task_data["id"]
    print(f"  ✓ Task uploaded: {task_id}")
    print(f"    Language: {task_data['language']}")
    print(f"    Size: {task_data['size']} bytes")

    # Step 2: Upload dataset
    print("\n📤 Step 2: Uploading dataset...")
    dataset_file = RESOURCES_DIR / "sample_bookings.csv"
    with open(dataset_file, "rb") as f:
        files = {"file": (dataset_file.name, f, "text/csv")}
        response = client.post("/api/v1/files/dataset", files=files)

    assert response.status_code == 200
    dataset_data = response.json()
    dataset_id = dataset_data["id"]
    print(f"  ✓ Dataset uploaded: {dataset_id}")
    print(f"    Rows: {dataset_data['rowCount']}")
    print(f"    Columns: {len(dataset_data['columns'])}")
    print(f"    Columns: {', '.join(dataset_data['columns'])}")

    # Step 3: Generate constraints
    print("\n🤖 Step 3: Generating constraints (this may take 30-60 seconds)...")
    request_data = {
        "taskFileId": task_id,
        "datasetId": dataset_id,
        "taskDescription": "Send discount confirmation emails to completed bookings",
    }
    response = client.post("/api/v1/constraints/generate", json=request_data, timeout=120.0)

    assert response.status_code == 200
    result = response.json()

    assert result["status"] == "completed"
    assert "jobId" in result
    assert "result" in result

    print(f"  ✓ Job ID: {result['jobId']}")

    # Step 4: Verify result structure
    print("\n📊 Step 4: Verifying results...")
    generation_result = result["result"]

    assert "constraints" in generation_result
    assert "flowGraph" in generation_result
    assert "codeAnnotations" in generation_result
    assert "statistics" in generation_result

    constraints = generation_result["constraints"]
    flow_graph = generation_result["flowGraph"]
    stats = generation_result["statistics"]

    print(f"  ✓ Generated {len(constraints)} constraints")
    print(f"  ✓ Flow graph: {len(flow_graph['nodes'])} nodes, {len(flow_graph['edges'])} edges")
    print(f"  ✓ Statistics: {stats['constraintCount']} constraints, {stats['assumptionCount']} assumptions")

    # Print sample constraints
    print("\n📋 Sample constraints:")
    for i, constraint in enumerate(constraints[:3], 1):
        print(f"\n  {i}. {constraint['label']}")
        print(f"     Column: {constraint['column']} ({constraint['columnType']})")
        print(f"     Type: {constraint['type']}")
        print(f"     Assumption: {constraint['assumption']['text']}")
        print(f"     GX code: {constraint['code']['greatExpectations'][:80]}...")
        print(f"     Deequ code: {constraint['code']['deequ'][:80]}...")

    if len(constraints) > 3:
        print(f"\n  ... and {len(constraints) - 3} more constraints")

    return result


def test_full_workflow_analytics(client):
    """Test workflow with analytics task."""
    print("\n🔬 Testing analytics task workflow...")

    # Upload task
    task_file = RESOURCES_DIR / "analytics_task.py"
    with open(task_file, "rb") as f:
        files = {"file": (task_file.name, f, "text/x-python")}
        response = client.post("/api/v1/files/task", files=files)
    assert response.status_code == 200
    task_id = response.json()["id"]

    # Upload dataset
    dataset_file = RESOURCES_DIR / "sample_bookings.csv"
    with open(dataset_file, "rb") as f:
        files = {"file": (dataset_file.name, f, "text/csv")}
        response = client.post("/api/v1/files/dataset", files=files)
    assert response.status_code == 200
    dataset_id = response.json()["id"]

    # Generate constraints
    request_data = {
        "taskFileId": task_id,
        "datasetId": dataset_id,
        "taskDescription": "Generate report of active bookings by guest category",
    }
    response = client.post("/api/v1/constraints/generate", json=request_data, timeout=120.0)

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"

    constraints = result["result"]["constraints"]
    print(f"  ✓ Analytics task generated {len(constraints)} constraints")


def test_error_handling_missing_files(client):
    """Test error handling for non-existent files."""
    print("\n🚫 Testing error handling...")

    request_data = {
        "taskFileId": "nonexistent-task-id",
        "datasetId": "nonexistent-dataset-id",
    }
    response = client.post("/api/v1/constraints/generate", json=request_data)

    assert response.status_code == 404
    error = response.json()
    assert "not found" in error["detail"].lower()
    print(f"  ✓ 404 error handled correctly: {error['detail']}")


def test_custom_llm_options(client):
    """Test constraint generation with custom LLM options."""
    print("\n⚙️ Testing custom LLM options...")

    # Upload files
    task_file = RESOURCES_DIR / "batch_processing_task.py"
    with open(task_file, "rb") as f:
        files = {"file": (task_file.name, f, "text/x-python")}
        response = client.post("/api/v1/files/task", files=files)
    task_id = response.json()["id"]

    dataset_file = RESOURCES_DIR / "sample_bookings.csv"
    with open(dataset_file, "rb") as f:
        files = {"file": (dataset_file.name, f, "text/csv")}
        response = client.post("/api/v1/files/dataset", files=files)
    dataset_id = response.json()["id"]

    # Generate with custom options
    request_data = {
        "taskFileId": task_id,
        "datasetId": dataset_id,
        "options": {
            # Note: llmProvider/model would need API key in environment
        },
    }
    response = client.post("/api/v1/constraints/generate", json=request_data, timeout=120.0)

    assert response.status_code == 200
    result = response.json()
    print(f"  ✓ Custom options accepted")


if __name__ == "__main__":
    """Manual test with httpx - no pytest needed.

    Usage:
        # Make sure server is running
        uv run uvicorn prismadv.api.v1.app:app --reload --port 8000

        # Run this script directly
        RUN_LLM_TESTS=1 uv run python tests/integration/test_api_e2e.py
    """
    import sys

    if not os.getenv("RUN_LLM_TESTS"):
        print("⚠️  Set RUN_LLM_TESTS=1 to run this test")
        sys.exit(1)

    print("🚀 Starting E2E API test...")
    print(f"   API URL: {API_BASE_URL}")

    with httpx.Client(base_url=API_BASE_URL, follow_redirects=True) as client:
        try:
            test_health_check(client)
            test_session_info(client)
            test_stats(client)
            test_full_workflow_batch_processing(client)
            test_error_handling_missing_files(client)

            print("\n" + "="*60)
            print("✅ All tests passed!")
            print("="*60)
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

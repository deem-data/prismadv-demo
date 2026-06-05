"""Integration test for GenerationOrchestrator with real LLM.

This test requires:
1. DSPy installed: uv sync --extra dspy
2. An LLM API key configured (OpenAI, Anthropic, Google Gemini)
3. Set environment variable to enable: RUN_LLM_TESTS=1

Run with:
    # OpenAI
    RUN_LLM_TESTS=1 OPENAI_API_KEY=sk-... uv run pytest tests/integration/test_orchestrator_real_llm.py -v -s

    # Anthropic
    RUN_LLM_TESTS=1 ANTHROPIC_API_KEY=sk-ant-... uv run pytest tests/integration/test_orchestrator_real_llm.py -v -s

    # Google Gemini
    RUN_LLM_TESTS=1 GOOGLE_API_KEY=... uv run pytest tests/integration/test_orchestrator_real_llm.py -v -s
"""

import os
from pathlib import Path

import pytest

# Check if LLM tests should run
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_LLM_TESTS"),
    reason="Set RUN_LLM_TESTS=1 to run tests with real LLM",
)

# Lazy import to avoid import errors when DSPy not installed
dspy = pytest.importorskip("dspy")

from prismadv.generation import GenerationOrchestrator, generation_context_to_api
from prismadv.llm import create_lm_from_env


# Test fixtures
RESOURCES_DIR = Path(__file__).parent.parent / "resources"
DATASET_PATH = RESOURCES_DIR / "sample_bookings.csv"


@pytest.fixture
def lm():
    """Initialize DSPy LM from environment variables using factory.

    Auto-detects API keys and uses cheap models by default:
    - OPENAI_API_KEY → gpt-4o-mini
    - ANTHROPIC_API_KEY → claude-3-5-haiku
    - GOOGLE_API_KEY or GEMINI_API_KEY → gemini-2.5-flash

    Override with LLM_MODEL environment variable.
    """
    try:
        return create_lm_from_env()
    except ValueError as e:
        pytest.skip(str(e))


@pytest.fixture
def orchestrator(lm):
    """Create orchestrator with real LLM."""
    return GenerationOrchestrator(lm=lm, max_parallel_llm_calls=3)


def test_batch_processing_task(orchestrator):
    """Test constraint generation for batch processing task."""
    task_file = RESOURCES_DIR / "batch_processing_task.py"
    task_code = task_file.read_text()

    context = orchestrator.generate(
        task_code=task_code,
        task_file_name=task_file.name,
        dataset_path=DATASET_PATH,
        task_description="Send discount confirmation emails to completed bookings",
    )

    # Verify basic structure
    assert context.task_file_name == "batch_processing_task.py"
    assert len(context.accessed_columns) > 0
    assert len(context.assumptions) > 0
    assert len(context.constraints) > 0

    # Convert to API format
    result = generation_context_to_api(context)

    # Check constraints
    print(f"\n✓ Generated {len(result.constraints)} constraints")
    for constraint in result.constraints:
        print(f"  - {constraint.label}: {constraint.type}")
        print(f"    GX: {constraint.code.great_expectations}")
        print(f"    Deequ: {constraint.code.deequ}")

    # Check flow graph
    assert len(result.flow_graph.nodes) > 0
    assert len(result.flow_graph.edges) > 0
    print(f"\n✓ Flow graph: {len(result.flow_graph.nodes)} nodes, {len(result.flow_graph.edges)} edges")

    # Check code annotations
    assert len(result.code_annotations) > 0
    print(f"✓ Code annotations: {len(result.code_annotations)} lines annotated")

    # Verify statistics
    assert result.statistics.constraint_count == len(result.constraints)
    # Note: assumption count may be less than constraint count since one assumption can generate multiple constraints
    assert result.statistics.assumption_count > 0


def test_analytics_task(orchestrator):
    """Test constraint generation for analytics task."""
    task_file = RESOURCES_DIR / "analytics_task.py"
    task_code = task_file.read_text()

    context = orchestrator.generate(
        task_code=task_code,
        task_file_name=task_file.name,
        dataset_path=DATASET_PATH,
        task_description="Generate report of active bookings by guest category",
    )

    assert len(context.accessed_columns) > 0
    assert len(context.assumptions) > 0
    assert len(context.constraints) > 0

    result = generation_context_to_api(context)

    print(f"\n✓ Generated {len(result.constraints)} constraints for analytics task")
    for constraint in result.constraints:
        print(f"  - {constraint.label}")


def test_ml_task(orchestrator):
    """Test constraint generation for ML task."""
    task_file = RESOURCES_DIR / "ml_task.py"
    task_code = task_file.read_text()

    context = orchestrator.generate(
        task_code=task_code,
        task_file_name=task_file.name,
        dataset_path=DATASET_PATH,
        task_description="Train logistic regression model to predict booking completion",
    )

    assert len(context.accessed_columns) > 0
    assert len(context.assumptions) > 0
    assert len(context.constraints) > 0

    result = generation_context_to_api(context)

    print(f"\n✓ Generated {len(result.constraints)} constraints for ML task")
    for constraint in result.constraints:
        print(f"  - {constraint.label}")

    # ML task should detect revenue normalization requires non-zero std dev
    constraint_types = [c.type for c in result.constraints]
    assert len(constraint_types) > 0  # Should have some constraints


def test_full_pipeline_output(orchestrator):
    """Test complete pipeline output structure."""
    task_file = RESOURCES_DIR / "batch_processing_task.py"
    task_code = task_file.read_text()

    context = orchestrator.generate(
        task_code=task_code,
        task_file_name=task_file.name,
        dataset_path=DATASET_PATH,
        task_description="Send discount confirmation emails",
    )

    result = generation_context_to_api(context)

    # Verify all required fields are present
    assert result.constraints is not None
    assert result.flow_graph is not None
    assert result.code_annotations is not None
    assert result.statistics is not None

    # Verify constraint structure
    for constraint in result.constraints:
        assert constraint.id
        assert constraint.column
        assert constraint.type
        assert constraint.column_type
        assert constraint.label
        assert constraint.code.great_expectations
        assert constraint.code.deequ
        assert constraint.assumption.text
        assert len(constraint.assumption.source_code_lines) > 0
        assert constraint.assumption.source_file

    print("\n✓ All required fields present and valid")

"""Tests for generation orchestrator."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Skip all tests if dspy is not installed
dspy = pytest.importorskip("dspy")

from prismadv.generation import GenerationOrchestrator, GenerationContext
from prismadv.profiling import ProfilerBackend


@pytest.fixture
def mock_lm():
    """Create a mock dspy.LM for testing."""
    return MagicMock(spec=dspy.LM)


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file for testing."""
    csv_path = tmp_path / "test_data.csv"
    csv_path.write_text("age,name\n25,Alice\n30,Bob\n")
    return csv_path


def test_orchestrator_initialization(mock_lm):
    """Test that orchestrator initializes correctly."""
    orchestrator = GenerationOrchestrator(
        lm=mock_lm,
        profiler_backend=ProfilerBackend.BUILTIN,
    )

    assert orchestrator._lm == mock_lm
    assert orchestrator._profiler_backend == ProfilerBackend.BUILTIN
    assert orchestrator._column_detector is not None
    assert orchestrator._data_flow_detector is not None
    assert orchestrator._assumption_extractor is not None
    assert orchestrator._constraint_generator is not None
    assert orchestrator._flow_graph_builder is not None


def test_orchestrator_generate_returns_context(mock_lm, sample_csv):
    """Test that generate returns a GenerationContext."""
    orchestrator = GenerationOrchestrator(
        lm=mock_lm,
        profiler_backend=ProfilerBackend.BUILTIN,
    )

    # Mock all the components to avoid actual LLM calls
    orchestrator._column_detector.detect = MagicMock(return_value=["age", "name"])
    orchestrator._data_flow_detector.detect_parallel = MagicMock(return_value={"age": [], "name": []})
    orchestrator._assumption_extractor.extract_parallel = MagicMock(return_value=[])
    orchestrator._constraint_generator.generate_parallel = MagicMock(return_value=[])

    context = orchestrator.generate(
        task_code="df['age'] > 18",
        task_file_name="test.py",
        dataset_path=sample_csv,
        task_description="Filter adults",
    )

    assert isinstance(context, GenerationContext)
    assert context.task_code == "df['age'] > 18"
    assert context.task_file_name == "test.py"
    assert context.task_description == "Filter adults"
    assert context.accessed_columns == ["age", "name"]
    assert context.dataset_profile is not None


def test_generation_context_stores_all_data(sample_csv):
    """Test that GenerationContext stores all required data."""
    from unittest.mock import MagicMock

    # Create a mock profile
    profile = MagicMock()
    profile.dataset.row_count = 2

    context = GenerationContext(
        task_code="test code",
        task_file_name="test.py",
        dataset_path=str(sample_csv),
        dataset_profile=profile,
        task_description="test task",
        accessed_columns=["age"],
        assumptions=[],
        constraints=[],
    )

    assert context.task_code == "test code"
    assert context.task_file_name == "test.py"
    assert context.dataset_profile is not None
    assert context.accessed_columns == ["age"]
    assert context.assumptions == []
    assert context.constraints == []


def test_orchestrator_profiles_dataset(mock_lm, sample_csv):
    """Test that orchestrator profiles the dataset."""
    orchestrator = GenerationOrchestrator(
        lm=mock_lm,
        profiler_backend=ProfilerBackend.BUILTIN,
    )

    # Mock LLM components
    orchestrator._column_detector.detect = MagicMock(return_value=["age"])
    orchestrator._data_flow_detector.detect_parallel = MagicMock(return_value={"age": []})
    orchestrator._assumption_extractor.extract_parallel = MagicMock(return_value=[])
    orchestrator._constraint_generator.generate_parallel = MagicMock(return_value=[])

    context = orchestrator.generate(
        task_code="test",
        task_file_name="test.py",
        dataset_path=sample_csv,
        task_description="test",
    )

    # Check that profiling happened
    assert context.dataset_profile is not None
    assert context.dataset_profile.dataset.row_count == 2
    assert len(context.dataset_profile.dataset.columns) == 2


def test_orchestrator_calls_all_pipeline_stages(mock_lm, sample_csv):
    """Test that orchestrator calls all pipeline stages in order."""
    orchestrator = GenerationOrchestrator(lm=mock_lm)

    # Mock all stages
    orchestrator._column_detector.detect = MagicMock(return_value=["age", "name"])
    orchestrator._data_flow_detector.detect_parallel = MagicMock(return_value={"age": [], "name": []})
    orchestrator._assumption_extractor.extract_parallel = MagicMock(return_value=[])
    orchestrator._constraint_generator.generate_parallel = MagicMock(return_value=[])

    orchestrator.generate(
        task_code="test code",
        task_file_name="test.py",
        dataset_path=sample_csv,
        task_description="test task",
    )

    # Verify all stages were called
    orchestrator._column_detector.detect.assert_called_once()
    orchestrator._data_flow_detector.detect_parallel.assert_called_once()
    orchestrator._assumption_extractor.extract_parallel.assert_called_once()
    orchestrator._constraint_generator.generate_parallel.assert_called_once()

    # Verify they were called with correct arguments
    detect_call = orchestrator._column_detector.detect.call_args
    assert detect_call.kwargs["code_script"] == "test code"
    assert detect_call.kwargs["downstream_task_description"] == "test task"

    extract_call = orchestrator._assumption_extractor.extract_parallel.call_args
    assert extract_call.kwargs["code_script"] == "test code"
    assert extract_call.kwargs["accessed_columns"] == ["age", "name"]
    assert extract_call.kwargs["source_file"] == "test.py"

    data_flow_call = orchestrator._data_flow_detector.detect_parallel.call_args
    assert data_flow_call.kwargs["code_script"] == "test code"
    assert data_flow_call.kwargs["accessed_columns"] == ["age", "name"]

    generate_call = orchestrator._constraint_generator.generate_parallel.call_args
    assert generate_call.kwargs["code_script"] == "test code"
    assert generate_call.kwargs["accessed_columns"] == ["age", "name"]


def test_orchestrator_cost_breakdown_includes_data_flow(mock_lm, sample_csv):
    """Test that cost breakdown includes data_flow_detection key."""
    orchestrator = GenerationOrchestrator(lm=mock_lm)

    orchestrator._column_detector.detect = MagicMock(return_value=["age"])
    orchestrator._data_flow_detector.detect_parallel = MagicMock(return_value={"age": []})
    orchestrator._assumption_extractor.extract_parallel = MagicMock(return_value=[])
    orchestrator._constraint_generator.generate_parallel = MagicMock(return_value=[])

    context = orchestrator.generate(
        task_code="test",
        task_file_name="test.py",
        dataset_path=sample_csv,
        task_description="test",
    )

    assert "data_flow_detection" in context.cost_breakdown
    assert "column_detection" in context.cost_breakdown
    assert "assumption_extraction" in context.cost_breakdown
    assert "constraint_generation" in context.cost_breakdown


def test_orchestrator_passes_data_flow_map_to_extractor(mock_lm, sample_csv):
    """Test that data flow results are passed to assumption extraction."""
    from prismadv.ir import SourceSpan

    orchestrator = GenerationOrchestrator(lm=mock_lm)

    flow_map = {"age": [SourceSpan(start_line=2, end_line=3)]}
    orchestrator._column_detector.detect = MagicMock(return_value=["age"])
    orchestrator._data_flow_detector.detect_parallel = MagicMock(return_value=flow_map)
    orchestrator._assumption_extractor.extract_parallel = MagicMock(return_value=[])
    orchestrator._constraint_generator.generate_parallel = MagicMock(return_value=[])

    orchestrator.generate(
        task_code="test",
        task_file_name="test.py",
        dataset_path=sample_csv,
        task_description="test",
    )

    extract_call = orchestrator._assumption_extractor.extract_parallel.call_args
    assert extract_call.kwargs["data_flow_map"] == flow_map

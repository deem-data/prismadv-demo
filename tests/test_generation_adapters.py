"""Tests for IR to API adapters."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from prismadv.api.v1.schemas import GenerationResult
from prismadv.generation.adapters import (
    assumption_ir_to_api,
    constraint_ir_to_api,
    extract_code_annotations,
    generation_context_to_api,
)
from prismadv.generation import GenerationContext
from prismadv.ir import AssumptionIR, ConstraintIR, SourceSpan


@pytest.fixture
def sample_assumption():
    """Create sample assumption for testing."""
    return AssumptionIR(
        id="assumption-1",
        text="Age must be between 18 and 65",
        sources=[
            SourceSpan(start_line=15, end_line=16, file="test.py"),
            SourceSpan(start_line=20, end_line=20, file="test.py"),
        ],
        columns=["age"],
        constraint_type="range",
    )


@pytest.fixture
def sample_constraint():
    """Create sample constraint for testing."""
    from prismadv.ir import parse_gx_expectation, parse_deequ_constraint

    return ConstraintIR(
        id="constraint-1",
        assumption_ids=["assumption-1"],
        column="age",
        columns=["age"],
        column_type="numerical",
        type="range",
        label="age (Range)",
        code_gx=parse_gx_expectation("expect_column_values_to_be_between(column='age', min_value=18, max_value=65)"),
        code_deequ=parse_deequ_constraint(".isContainedIn('age', 18.0, 65.0)"),
        data_stats={"min": 18, "max": 65},
    )


def test_assumption_ir_to_api(sample_assumption):
    """Test converting AssumptionIR to API Assumption."""
    api_assumption = assumption_ir_to_api(sample_assumption)

    assert api_assumption.text == "Age must be between 18 and 65"
    assert api_assumption.source_code_lines == [15, 20]
    assert api_assumption.source_file == "test.py"


def test_constraint_ir_to_api(sample_constraint, sample_assumption):
    """Test converting ConstraintIR to API Constraint."""
    api_constraint = constraint_ir_to_api(sample_constraint, [sample_assumption])

    assert api_constraint.id == "constraint-1"
    assert api_constraint.column == "age"
    assert api_constraint.type.value == "range"
    assert api_constraint.column_type.value == "numerical"
    assert api_constraint.label == "age (Range)"
    assert api_constraint.enabled is True

    # Check code
    assert "expect_column_values_to_be_between" in api_constraint.code.great_expectations
    assert "isContainedIn" in api_constraint.code.deequ

    # Check assumption is included
    assert api_constraint.assumption.text == sample_assumption.text


def test_extract_code_annotations(sample_constraint, sample_assumption):
    """Test extracting code annotations from constraints."""
    assumptions_map = {sample_assumption.id: sample_assumption}
    annotations = extract_code_annotations([sample_constraint], assumptions_map)

    assert len(annotations) == 2  # Two source spans

    # Check first annotation
    assert annotations[0].line_number == 15
    assert annotations[0].type.value == "range"
    assert annotations[0].column == "age"
    assert annotations[0].constraint_ids == ["constraint-1"]
    assert annotations[0].highlight is True

    # Check second annotation
    assert annotations[1].line_number == 20


def test_extract_code_annotations_skips_missing_assumptions(sample_constraint):
    """Test that annotations are skipped for missing assumptions."""
    annotations = extract_code_annotations([sample_constraint], {})  # Empty map
    assert len(annotations) == 0


def test_generation_context_to_api():
    """Test converting full GenerationContext to API GenerationResult."""
    from prismadv.api.v1.schemas import Column, ColumnType, InferredType

    # Create mock context
    assumption = AssumptionIR(
        id="assumption-1",
        text="Test assumption",
        sources=[SourceSpan(start_line=10, end_line=10, file="test.py")],
        columns=["age"],
        constraint_type="range",
    )

    constraint = ConstraintIR(
        id="constraint-1",
        assumption_ids=["assumption-1"],
        column="age",
        columns=["age"],
        column_type="numerical",
        type="range",
        label="age (Range)",
    )

    # Create mock profile - just mock the parts we need
    profile = MagicMock()
    profile.dataset.columns = [
        Column(
            name="age",
            type=InferredType.INTEGER,
            inferred_type=ColumnType.NUMERICAL,
            nullable=False,
        )
    ]

    context = GenerationContext(
        task_code="test code",
        task_file_name="test.py",
        dataset_path="/tmp/test.csv",
        dataset_profile=profile,
        task_description="test",
        accessed_columns=["age"],
        assumptions=[assumption],
        constraints=[constraint],
    )

    # Convert to API
    result = generation_context_to_api(context)

    assert isinstance(result, GenerationResult)
    assert len(result.constraints) == 1
    assert result.constraints[0].id == "constraint-1"
    assert len(result.code_annotations) == 1
    assert result.code_annotations[0].line_number == 10
    assert result.flow_graph is not None
    assert len(result.flow_graph.nodes) > 0
    assert len(result.flow_graph.edges) > 0
    assert result.statistics.constraint_count == 1
    assert result.statistics.assumption_count == 1
    assert result.statistics.columns_covered == 1


def test_generation_context_to_api_skips_constraints_without_assumptions():
    """Test that constraints without assumptions are skipped."""
    from prismadv.api.v1.schemas import Column, ColumnType, InferredType

    # Constraint with non-existent assumption
    constraint = ConstraintIR(
        id="constraint-1",
        assumption_ids=["nonexistent"],  # Not in assumptions list
        column="age",
        columns=["age"],
        column_type="numerical",
        type="range",
        label="age (Range)",
    )

    # Mock profile
    profile = MagicMock()
    profile.dataset.columns = [
        Column(
            name="age",
            type=InferredType.INTEGER,
            inferred_type=ColumnType.NUMERICAL,
            nullable=False,
        )
    ]

    context = GenerationContext(
        task_code="test",
        task_file_name="test.py",
        dataset_path="/tmp/test.csv",
        dataset_profile=profile,
        task_description="test",
        accessed_columns=["age"],
        assumptions=[],  # Empty assumptions
        constraints=[constraint],
    )

    result = generation_context_to_api(context)

    # Should have 0 constraints (skipped because no matching assumption)
    assert len(result.constraints) == 0

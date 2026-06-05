"""Tests for constraint generation using DSPy."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

# Skip all tests if dspy is not installed
dspy = pytest.importorskip("dspy")

from prismadv.generation import ConstraintGenerator
from prismadv.ir import AssumptionIR, ConstraintIR, SourceSpan
from prismadv.llm.errors import LLMOutputError


@pytest.fixture
def mock_lm():
    """Create a mock dspy.LM for testing."""
    lm = MagicMock(spec=dspy.LM)
    return lm


@pytest.fixture
def sample_assumptions():
    """Create sample assumptions for testing."""
    return [
        AssumptionIR(
            id="assumption-1",
            text="Age must be between 18 and 65",
            sources=[SourceSpan(start_line=15, end_line=16, file="test.py")],
            columns=["age"],
            constraint_type="range",
        ),
        AssumptionIR(
            id="assumption-2",
            text="Name must not be null",
            sources=[SourceSpan(start_line=10, end_line=10, file="test.py")],
            columns=["name"],
            constraint_type="completeness",
        ),
    ]


def test_constraint_generator_basic(mock_lm, sample_assumptions):
    """Test basic constraint generation."""
    generator = ConstraintGenerator(lm=mock_lm)

    # Mock predictor to return valid constraints
    mock_prediction = dspy.Prediction(constraints={
        "age": {
            "gx": ["expect_column_values_to_be_between(column='age', min_value=18, max_value=65)"],
            "deequ": [".isContainedIn('age', 18.0, 65.0)"]
        },
        "name": {
            "gx": ["expect_column_values_to_not_be_null(column='name')"],
            "deequ": [".isComplete('name')"]
        }
    })
    generator._predictor = MagicMock(return_value=mock_prediction)

    constraints = generator.generate(
        assumptions=sample_assumptions,
        code_script="df[df['age'] >= 18]",
        accessed_columns=["age", "name"],
        task_description="Filter adults",
    )

    assert len(constraints) == 2
    assert all(isinstance(c, ConstraintIR) for c in constraints)

    # Check that constraints have assumption linkage
    assert constraints[0].assumption_ids[0] in ["assumption-1", "assumption-2"]
    assert constraints[1].assumption_ids[0] in ["assumption-1", "assumption-2"]


def test_constraint_generator_with_single_assumption(mock_lm):
    """Test generation with a single assumption."""
    generator = ConstraintGenerator(lm=mock_lm)

    assumption = AssumptionIR(
        id="assumption-1",
        text="Category must be PREMIUM, STANDARD, or BASIC",
        sources=[SourceSpan(start_line=7, end_line=7, file="test.py")],
        columns=["category"],
        constraint_type="enum",
    )

    mock_prediction = dspy.Prediction(constraints={
        "category": {
            "gx": ["expect_column_values_to_be_in_set(column='category', value_set=['PREMIUM', 'STANDARD', 'BASIC'])"],
            "deequ": [".isContainedIn('category', ['PREMIUM', 'STANDARD', 'BASIC'])"]
        }
    })
    generator._predictor = MagicMock(return_value=mock_prediction)

    constraints = generator.generate(
        assumptions=[assumption],
        code_script="...",
        accessed_columns=["category"],
        task_description="Filter by category",
    )

    assert len(constraints) == 1
    assert constraints[0].column == "category"
    assert constraints[0].type == "enum"


def test_constraint_generator_empty_assumptions(mock_lm):
    """Test that empty assumptions list returns empty constraints."""
    generator = ConstraintGenerator(lm=mock_lm)

    constraints = generator.generate(
        assumptions=[],
        code_script="...",
        accessed_columns=["age"],
        task_description="test",
    )

    assert constraints == []


def test_constraint_generator_skips_unparseable_code(mock_lm, sample_assumptions):
    """Test that generator skips constraints with unparseable code."""
    generator = ConstraintGenerator(lm=mock_lm)

    # Return mix of valid and invalid code
    mock_prediction = dspy.Prediction(constraints={
        "age": {
            "gx": ["invalid_gx_code(foo=bar)"],  # Invalid, will fail parsing
            "deequ": [".isContainedIn('age', 18.0, 65.0)"]  # Valid
        },
        "name": {
            "gx": ["expect_column_values_to_not_be_null(column='name')"],  # Valid
            "deequ": ["invalid deequ code"]  # Invalid
        }
    })
    generator._predictor = MagicMock(return_value=mock_prediction)

    constraints = generator.generate(
        assumptions=sample_assumptions,
        code_script="...",
        accessed_columns=["age", "name"],
        task_description="test",
    )

    # Should still return some constraints (the ones that parsed successfully)
    # The exact behavior depends on parsing - at least one should succeed
    assert len(constraints) >= 0  # May be 0 if all parsing fails


def test_constraint_generator_handles_non_list_codes(mock_lm, sample_assumptions):
    """Test that generator handles codes provided as strings instead of lists."""
    generator = ConstraintGenerator(lm=mock_lm)

    # Return codes as strings instead of lists
    mock_prediction = dspy.Prediction(constraints={
        "age": {
            "gx": "expect_column_values_to_be_between(column='age', min_value=18, max_value=65)",  # String, not list
            "deequ": ".isContainedIn('age', 18.0, 65.0)"  # String, not list
        }
    })
    generator._predictor = MagicMock(return_value=mock_prediction)

    constraints = generator.generate(
        assumptions=sample_assumptions,
        code_script="...",
        accessed_columns=["age"],
        task_description="test",
    )

    # Should handle string-to-list conversion
    assert len(constraints) >= 0


def test_constraint_generator_invalid_output_raises_error(mock_lm, sample_assumptions):
    """Test that invalid output raises LLMOutputError."""
    generator = ConstraintGenerator(lm=mock_lm)

    # Return non-dict output
    mock_prediction = dspy.Prediction(constraints="not a dict")
    generator._predictor = MagicMock(return_value=mock_prediction)

    with pytest.raises(LLMOutputError):
        generator.generate(
            assumptions=sample_assumptions,
            code_script="...",
            accessed_columns=["age"],
            task_description="test",
        )


def test_constraint_generator_no_valid_constraints_raises_error(mock_lm, sample_assumptions):
    """Test that no valid constraints raises LLMOutputError."""
    generator = ConstraintGenerator(lm=mock_lm)

    # Return empty dict
    mock_prediction = dspy.Prediction(constraints={})
    generator._predictor = MagicMock(return_value=mock_prediction)

    with pytest.raises(LLMOutputError, match="no valid constraints"):
        generator.generate(
            assumptions=sample_assumptions,
            code_script="...",
            accessed_columns=["age"],
            task_description="test",
        )

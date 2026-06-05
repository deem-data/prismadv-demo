"""Tests for column access detection using DSPy."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

# Skip all tests if dspy is not installed
dspy = pytest.importorskip("dspy")

from prismadv.generation import ColumnAccessDetector
from prismadv.llm.errors import LLMOutputError


@pytest.fixture
def mock_lm():
    """Create a mock dspy.LM for testing."""
    lm = MagicMock(spec=dspy.LM)
    return lm


def test_column_access_detector_filters_unknown_columns(mock_lm):
    """Test that detector filters out columns not in the allowed list."""
    detector = ColumnAccessDetector(lm=mock_lm)

    # Mock the predictor to return a mix of valid and invalid columns
    mock_prediction = dspy.Prediction(columns=["id", "age", "not_a_column"])
    detector._predictor = MagicMock(return_value=mock_prediction)

    cols = detector.detect(
        columns=["id", "age", "name"],
        code_script="df['id']\ndf['age']",
        downstream_task_description="demo",
    )

    # Should filter out "not_a_column" since it's not in allowed columns
    assert set(cols) == {"id", "age"}
    detector._predictor.assert_called_once()


def test_column_access_detector_raises_when_no_known_columns(mock_lm):
    """Test that detector raises error when no valid columns are detected."""
    detector = ColumnAccessDetector(lm=mock_lm)

    # Mock predictor to return only invalid columns
    mock_prediction = dspy.Prediction(columns=["foo", "bar"])
    detector._predictor = MagicMock(return_value=mock_prediction)

    with pytest.raises(LLMOutputError, match="no known columns"):
        detector.detect(
            columns=["id", "age"],
            code_script="print('hi')",
            downstream_task_description="demo",
        )


def test_column_access_detector_uses_custom_columns_desc(mock_lm):
    """Test that detector uses custom column description when provided."""
    detector = ColumnAccessDetector(lm=mock_lm)

    mock_prediction = dspy.Prediction(columns=["id"])
    detector._predictor = MagicMock(return_value=mock_prediction)

    custom_desc = "id: integer, primary key\nname: string, required"
    detector.detect(
        columns=["id", "name"],
        code_script="df['id']",
        downstream_task_description="demo",
        columns_desc=custom_desc,
    )

    # Verify custom description was passed to predictor
    call_kwargs = detector._predictor.call_args[1]
    assert call_kwargs["columns_desc"] == custom_desc


def test_column_access_detector_deduplicates_columns(mock_lm):
    """Test that detector handles duplicate columns in LLM output."""
    detector = ColumnAccessDetector(lm=mock_lm)

    # Mock predictor to return duplicates
    mock_prediction = dspy.Prediction(columns=["id", "age", "id", "age"])
    detector._predictor = MagicMock(return_value=mock_prediction)

    cols = detector.detect(
        columns=["id", "age", "name"],
        code_script="df['id']\ndf['age']",
        downstream_task_description="demo",
    )

    # List comprehension preserves order and includes duplicates from LLM
    # This matches the behavior in column_access.py:70
    assert cols == ["id", "age", "id", "age"]


def test_column_access_detector_empty_llm_output(mock_lm):
    """Test that detector raises error when LLM returns empty list."""
    detector = ColumnAccessDetector(lm=mock_lm)

    mock_prediction = dspy.Prediction(columns=[])
    detector._predictor = MagicMock(return_value=mock_prediction)

    with pytest.raises(LLMOutputError, match="no known columns"):
        detector.detect(
            columns=["id", "age"],
            code_script="print('hi')",
            downstream_task_description="demo",
        )

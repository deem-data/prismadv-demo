"""Tests for single-column data flow detection using DSPy."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

dspy = pytest.importorskip("dspy")

from prismadv.generation import DataFlowDetector
from prismadv.ir import SourceSpan


SAMPLE_CODE = "import pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df['age'])"


@pytest.fixture
def mock_lm():
    lm = MagicMock(spec=dspy.LM)
    return lm


def test_detect_returns_source_spans(mock_lm):
    """Test that valid LLM output is converted to SourceSpan list."""
    detector = DataFlowDetector(lm=mock_lm)
    mock_prediction = dspy.Prediction(sources=[
        {"start_line": 2, "end_line": 2},
        {"start_line": 3, "end_line": 3},
    ])
    detector._predictor = MagicMock(return_value=mock_prediction)

    spans = detector.detect(
        code_script=SAMPLE_CODE,
        target_column="age",
        task_description="demo",
    )

    assert len(spans) == 2
    assert spans[0] == SourceSpan(start_line=2, end_line=2)
    assert spans[1] == SourceSpan(start_line=3, end_line=3)


def test_detect_filters_invalid_ranges(mock_lm):
    """Test that out-of-range and malformed entries are dropped."""
    detector = DataFlowDetector(lm=mock_lm)
    mock_prediction = dspy.Prediction(sources=[
        {"start_line": 0, "end_line": 1},    # start < 1
        {"start_line": 5, "end_line": 3},    # end < start
        {"start_line": 99, "end_line": 99},  # beyond total lines
        {"start_line": 1, "end_line": 1},    # valid
        {"start_line": 2, "end_line": 5},    # end clamped to 3
    ])
    detector._predictor = MagicMock(return_value=mock_prediction)

    spans = detector.detect(
        code_script=SAMPLE_CODE,
        target_column="age",
        task_description="demo",
    )

    assert len(spans) == 2
    assert spans[0] == SourceSpan(start_line=1, end_line=1)
    assert spans[1] == SourceSpan(start_line=2, end_line=3)  # clamped


def test_detect_graceful_failure_on_exception(mock_lm):
    """Test that LLM errors return empty list, not raise."""
    detector = DataFlowDetector(lm=mock_lm)
    detector._predictor = MagicMock(side_effect=RuntimeError("LLM boom"))

    spans = detector.detect(
        code_script=SAMPLE_CODE,
        target_column="age",
        task_description="demo",
    )

    assert spans == []


def test_detect_empty_sources(mock_lm):
    """Test that empty LLM output returns empty list."""
    detector = DataFlowDetector(lm=mock_lm)
    mock_prediction = dspy.Prediction(sources=[])
    detector._predictor = MagicMock(return_value=mock_prediction)

    spans = detector.detect(
        code_script=SAMPLE_CODE,
        target_column="age",
        task_description="demo",
    )

    assert spans == []


def test_detect_non_list_sources(mock_lm):
    """Test that non-list sources output returns empty list."""
    detector = DataFlowDetector(lm=mock_lm)
    mock_prediction = dspy.Prediction(sources="not a list")
    detector._predictor = MagicMock(return_value=mock_prediction)

    spans = detector.detect(
        code_script=SAMPLE_CODE,
        target_column="age",
        task_description="demo",
    )

    assert spans == []


def test_detect_parallel(mock_lm):
    """Test parallel detection returns dict mapping columns to spans."""
    detector = DataFlowDetector(lm=mock_lm)

    def fake_predict(**kwargs):
        col = kwargs["target_column"]
        if col == "age":
            return dspy.Prediction(sources=[{"start_line": 3, "end_line": 3}])
        return dspy.Prediction(sources=[])

    detector._predictor = MagicMock(side_effect=fake_predict)

    result = detector.detect_parallel(
        code_script=SAMPLE_CODE,
        accessed_columns=["age", "name"],
        task_description="demo",
        max_workers=2,
    )

    assert "age" in result
    assert "name" in result
    assert len(result["age"]) == 1
    assert result["name"] == []


def test_detect_parallel_empty_columns(mock_lm):
    """Test parallel detection with no columns returns empty dict."""
    detector = DataFlowDetector(lm=mock_lm)

    result = detector.detect_parallel(
        code_script=SAMPLE_CODE,
        accessed_columns=[],
        task_description="demo",
    )

    assert result == {}

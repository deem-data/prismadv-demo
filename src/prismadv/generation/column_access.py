"""Column access detection using DSPy."""

from __future__ import annotations

from typing import Sequence

try:
    import dspy
except ImportError:
    raise ImportError(
        "dspy is required for generation module. "
        "Install with: uv sync --extra dspy"
    )

from prismadv.generation.signatures import ColumnAccessDetectionSig
from prismadv.llm import LLMOutputError


class ColumnAccessDetector:
    """Detect which columns are accessed in code using DSPy.

    This class uses DSPy to analyze code and identify which dataset columns
    are accessed, enabling focused constraint generation on relevant columns.
    """

    def __init__(self, lm: dspy.LM):
        """Initialize the detector with a DSPy language model.

        Args:
            lm: A DSPy language model instance (e.g., dspy.LM('openai/gpt-4'))
        """
        self._lm = lm
        self._predictor = dspy.Predict(ColumnAccessDetectionSig)

    def detect(
        self,
        *,
        columns: Sequence[str],
        code_script: str,
        downstream_task_description: str,
        columns_desc: str | None = None,
    ) -> list[str]:
        """Detect which columns are accessed in the given code.

        Args:
            columns: The known dataset columns (used to filter LLM output)
            code_script: The code script to analyze
            downstream_task_description: Description of the downstream task
            columns_desc: Optional formatted column description. If omitted, uses comma-separated column names.

        Returns:
            List of column names that are accessed in the code

        Raises:
            LLMOutputError: If no valid columns are detected
        """
        cols_desc = columns_desc or ", ".join(columns)

        # Use DSPy context manager to set the LM
        with dspy.context(lm=self._lm):
            result = self._predictor(
                columns_desc=cols_desc,
                code_script=code_script,
                downstream_task_description=downstream_task_description,
            )

        # Filter output to only include known columns
        candidates = result.columns
        allowed = set(columns)
        selected = [c for c in candidates if c in allowed]

        if not selected:
            raise LLMOutputError(
                f"Column access detection returned no known columns. "
                f"LLM returned: {candidates!r}, but none matched allowed columns: {list(columns)}"
            )

        return selected

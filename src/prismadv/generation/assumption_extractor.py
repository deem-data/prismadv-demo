"""Assumption extraction from code using DSPy."""

from __future__ import annotations

import logging
import uuid
from typing import Callable, Sequence

logger = logging.getLogger(__name__)

try:
    import dspy
except ImportError:
    raise ImportError(
        "dspy is required for generation module. "
        "Install with: uv sync --extra dspy"
    )

from prismadv.generation.line_numbers import _add_highlighted_line_numbers, _add_line_numbers
from prismadv.generation.signatures import AssumptionExtractionSig
from prismadv.generation.utils import run_in_parallel_with_progress
from prismadv.ir import AssumptionIR, SourceSpan
from prismadv.llm import LLMOutputError


class AssumptionExtractor:
    """Extract data quality assumptions from code using DSPy.

    This class uses DSPy to analyze code and identify implicit data quality
    constraints that the code assumes or requires, which can then be converted
    into validation rules.
    """

    def __init__(self, lm: dspy.LM):
        """Initialize the extractor with a DSPy language model.

        Args:
            lm: A DSPy language model instance
        """
        self._lm = lm
        self._predictor = dspy.Predict(AssumptionExtractionSig)

    def extract(
        self,
        *,
        code_script: str,
        columns: Sequence[str],
        accessed_columns: Sequence[str],
        task_description: str,
        columns_desc: str | None = None,
        source_file: str = "script.py",
        data_flow_sources: list[SourceSpan] | None = None,
    ) -> list[AssumptionIR]:
        """Extract assumptions from code.

        Args:
            code_script: The code to analyze
            columns: All dataset columns (for validation)
            accessed_columns: Columns known to be accessed in the code
            task_description: Description of what the code does
            columns_desc: Optional formatted column description
            source_file: Name of the source file for provenance tracking

        Returns:
            List of AssumptionIR objects with full provenance information

        Raises:
            LLMOutputError: If extraction fails or returns invalid data
        """
        cols_desc = columns_desc or ", ".join(columns)
        accessed_str = ", ".join(accessed_columns)

        # Prepend line numbers (with data-flow highlighting when available)
        if data_flow_sources:
            numbered_code = _add_highlighted_line_numbers(code_script, data_flow_sources)
        else:
            numbered_code = _add_line_numbers(code_script)

        # Use DSPy context manager to set the LM
        with dspy.context(lm=self._lm):
            result = self._predictor(
                code_script=numbered_code,
                columns_desc=cols_desc,
                accessed_columns=accessed_str,
                task_description=task_description,
            )

        # Parse the LLM output
        try:
            assumptions_raw = result.assumptions
            if not isinstance(assumptions_raw, list):
                raise ValueError(f"Expected list of assumptions, got {type(assumptions_raw)}")

            assumptions: list[AssumptionIR] = []
            allowed_columns = set(columns)

            for idx, raw in enumerate(assumptions_raw):
                if not isinstance(raw, dict):
                    continue  # Skip invalid entries

                # Extract and validate fields
                text = raw.get("text", "").strip()
                if not text:
                    continue  # Skip empty assumptions

                # Filter columns to only valid ones
                cols = raw.get("columns", [])
                if isinstance(cols, str):
                    cols = [c.strip() for c in cols.split(",")]
                valid_cols = [c for c in cols if c in allowed_columns]
                if not valid_cols:
                    continue  # Skip assumptions with no valid columns

                # LLM may return pipe-separated options (e.g. "completeness|enum|relationship").
                # Take the first token only.
                constraint_type = raw.get("type", "").strip().split("|")[0].strip()

                # Parse source lines
                source_lines = raw.get("source_lines", [])
                if isinstance(source_lines, (int, float)):
                    source_lines = [int(source_lines)]
                elif not isinstance(source_lines, list):
                    source_lines = []

                # Create source spans
                sources: list[SourceSpan] = []
                for line in source_lines:
                    try:
                        line_num = int(line)
                        if line_num > 0:
                            sources.append(SourceSpan(
                                start_line=line_num,
                                end_line=line_num,
                                file=source_file,
                            ))
                    except (ValueError, TypeError):
                        continue

                # Create AssumptionIR
                assumption = AssumptionIR(
                    id=f"assumption-{uuid.uuid4().hex[:8]}",
                    text=text,
                    sources=sources,
                    columns=valid_cols,
                    constraint_type=constraint_type or None,
                )
                assumptions.append(assumption)

            if not assumptions:
                raise LLMOutputError(
                    f"Assumption extraction returned no valid assumptions. "
                    f"Raw output: {assumptions_raw!r}"
                )

            return assumptions

        except (KeyError, TypeError, ValueError) as e:
            raise LLMOutputError(
                f"Failed to parse assumption extraction output: {e}. "
                f"Raw output: {result.assumptions!r}"
            ) from e

    def extract_parallel(
        self,
        *,
        code_script: str,
        columns: Sequence[str],
        accessed_columns: Sequence[str],
        task_description: str,
        columns_desc: str | None = None,
        source_file: str = "script.py",
        max_workers: int | None = 5,
        item_done_callback: "Callable[[int, int], None] | None" = None,
        item_result_callback: "Callable[[str, list[AssumptionIR]], None] | None" = None,
        data_flow_map: dict[str, list[SourceSpan]] | None = None,
    ) -> list[AssumptionIR]:
        """Extract assumptions in parallel for each column (faster for many columns).

        This method processes each accessed column independently in parallel,
        which is much faster when you have many columns.

        Args:
            code_script: The code to analyze
            columns: All dataset columns (for validation)
            accessed_columns: Columns known to be accessed in the code
            task_description: Description of what the code does
            columns_desc: Optional formatted column description
            source_file: Name of the source file for provenance tracking
            max_workers: Maximum number of parallel LLM calls (default 5)

        Returns:
            List of AssumptionIR objects with full provenance information

        Raises:
            LLMOutputError: If extraction fails for all columns
        """
        if not accessed_columns:
            return []

        # Create extraction function for a single column
        def extract_for_column(column: str) -> list[AssumptionIR]:
            try:
                sources = data_flow_map.get(column) if data_flow_map else None
                return self.extract(
                    code_script=code_script,
                    columns=columns,
                    accessed_columns=[column],  # Focus on single column
                    task_description=task_description,
                    columns_desc=columns_desc,
                    source_file=source_file,
                    data_flow_sources=sources if sources else None,
                )
            except LLMOutputError as e:
                logger.warning(f"Assumption extraction failed for column '{column}': {e}")
                return []

        # Run extractions in parallel
        results_per_column = run_in_parallel_with_progress(
            extract_for_column,
            accessed_columns,
            max_workers=max_workers,
            done_callback=item_done_callback,
            item_result_callback=item_result_callback,
        )

        # Flatten results, tracking how many columns yielded nothing
        all_assumptions: list[AssumptionIR] = []
        failed_columns = 0
        for col_assumptions in results_per_column:
            if col_assumptions:
                all_assumptions.extend(col_assumptions)
            else:
                failed_columns += 1

        if not all_assumptions:
            raise LLMOutputError(
                f"Parallel assumption extraction returned no valid assumptions "
                f"for any of the {len(accessed_columns)} columns"
            )

        if failed_columns:
            logger.warning(
                f"Assumption extraction skipped {failed_columns}/{len(accessed_columns)} columns due to LLM errors"
            )

        return all_assumptions

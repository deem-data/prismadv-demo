"""Single-column data flow detection using DSPy."""

from __future__ import annotations

import logging
from typing import Callable, Sequence

logger = logging.getLogger(__name__)

try:
    import dspy
except ImportError:
    raise ImportError(
        "dspy is required for generation module. "
        "Install with: uv sync --extra dspy"
    )

from prismadv.generation.line_numbers import _add_line_numbers
from prismadv.generation.signatures import DataFlowDetectionSig
from prismadv.generation.utils import run_in_parallel_with_progress
from prismadv.ir import SourceSpan


class DataFlowDetector:
    """Detect which lines of code interact with a given column.

    For each column, this uses an LLM to perform data-flow analysis on the
    code and return the line ranges that read, write, transform, or filter
    data involving that column.
    """

    def __init__(self, lm: dspy.LM):
        self._lm = lm
        self._predictor = dspy.Predict(DataFlowDetectionSig)

    def detect(
        self,
        *,
        code_script: str,
        target_column: str,
        task_description: str,
    ) -> list[SourceSpan]:
        """Detect lines interacting with *target_column*.

        Returns:
            List of SourceSpan objects for the relevant line ranges.
            Returns an empty list on LLM failure (graceful degradation).
        """
        numbered_code = _add_line_numbers(code_script)
        total_lines = len(code_script.splitlines())

        try:
            with dspy.context(lm=self._lm):
                result = self._predictor(
                    code_script=numbered_code,
                    target_column=target_column,
                    task_description=task_description,
                )

            raw_sources = result.sources
            if not isinstance(raw_sources, list):
                logger.warning(
                    "Data flow detection returned non-list for column '%s': %r",
                    target_column,
                    raw_sources,
                )
                return []

            spans: list[SourceSpan] = []
            for entry in raw_sources:
                if not isinstance(entry, dict):
                    continue
                try:
                    start = int(entry.get("start_line", 0))
                    end = int(entry.get("end_line", 0))
                except (ValueError, TypeError):
                    continue

                # Validate range
                if start < 1 or end < start or start > total_lines:
                    continue
                # Clamp end to total lines
                end = min(end, total_lines)

                spans.append(SourceSpan(start_line=start, end_line=end))

            return spans

        except Exception as e:
            logger.warning(
                "Data flow detection failed for column '%s': %s",
                target_column,
                e,
            )
            return []

    def detect_parallel(
        self,
        *,
        code_script: str,
        accessed_columns: Sequence[str],
        task_description: str,
        max_workers: int | None = 5,
        item_done_callback: Callable[[int, int], None] | None = None,
        item_result_callback: "Callable[[str, tuple[str, list[SourceSpan]]], None] | None" = None,
    ) -> dict[str, list[SourceSpan]]:
        """Detect data flow for each column in parallel.

        Returns:
            Dict mapping column name to list of SourceSpan.
            Columns that fail get an empty list.
        """
        if not accessed_columns:
            return {}

        def detect_for_column(column: str) -> tuple[str, list[SourceSpan]]:
            spans = self.detect(
                code_script=code_script,
                target_column=column,
                task_description=task_description,
            )
            return (column, spans)

        results = run_in_parallel_with_progress(
            detect_for_column,
            accessed_columns,
            max_workers=max_workers,
            done_callback=item_done_callback,
            item_result_callback=item_result_callback,
        )

        data_flow_map: dict[str, list[SourceSpan]] = {}
        for column, spans in results:
            data_flow_map[column] = spans

        return data_flow_map

"""Constraint code generation from assumptions using DSPy."""

from __future__ import annotations

import json
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

from prismadv.generation.line_numbers import _add_line_numbers
from prismadv.generation.signatures import ConstraintCodeGenerationSig
from prismadv.generation.utils import run_in_parallel_with_progress
from prismadv.ir import (
    AssumptionIR,
    ConstraintIR,
    parse_deequ_constraint,
    parse_gx_expectation,
)
from prismadv.ir.deequ import load_deequ_constraint_signatures
from prismadv.ir.gx import load_gx_expectation_signatures
from prismadv.llm import LLMOutputError


class ConstraintGenerator:
    """Generate constraint code from assumptions using DSPy.

    This class takes assumptions extracted from code and generates executable
    validation rules in both Great Expectations and Deequ formats.
    """

    def __init__(self, lm: dspy.LM):
        """Initialize the generator with a DSPy language model.

        Args:
            lm: A DSPy language model instance
        """
        self._lm = lm
        self._predictor = dspy.Predict(ConstraintCodeGenerationSig)
        self._gx_sigs = load_gx_expectation_signatures()
        self._deequ_sigs = load_deequ_constraint_signatures()

    def _format_gx_signatures(self) -> str:
        """Format GX expectation signatures for LLM prompt."""
        lines = []
        for name, sig in sorted(self._gx_sigs.items()):
            desc = sig.description or ""
            # GX has args (dict) and other_parameters (dict)
            all_params = list(sig.args.keys()) + list(sig.other_parameters.keys())
            params = ", ".join([f"{p}=..." for p in all_params])
            lines.append(f"{sig.type}({params})")
            if desc:
                lines.append(f"  # {desc}")
        return "\n".join(lines)

    def _format_deequ_signatures(self) -> str:
        """Format Deequ constraint signatures for LLM prompt."""
        lines = []
        for name, sig in sorted(self._deequ_sigs.items()):
            desc = sig.description or ""
            params = ", ".join(sig.required + [f"{p}=..." for p in sig.optional])
            lines.append(f".{name}({params})")
            if desc:
                lines.append(f"  # {desc}")
            if sig.examples:
                for ex in sig.examples[:2]:  # Show max 2 examples
                    lines.append(f"  # Example: {ex}")
        return "\n".join(lines)

    def _format_assumptions(self, assumptions: Sequence[AssumptionIR]) -> str:
        """Format assumptions as JSON for LLM prompt."""
        assumptions_list = []
        for assumption in assumptions:
            assumptions_list.append({
                "text": assumption.text,
                "columns": assumption.columns,
                "type": assumption.constraint_type,
                "sources": [
                    {"start_line": s.start_line, "end_line": s.end_line}
                    for s in assumption.sources
                ]
            })
        return json.dumps(assumptions_list, indent=2)

    def generate(
        self,
        *,
        assumptions: Sequence[AssumptionIR],
        code_script: str,
        accessed_columns: Sequence[str],
        task_description: str,
        data_stats: dict | None = None,
    ) -> list[ConstraintIR]:
        """Generate constraints from assumptions.

        Args:
            assumptions: List of extracted assumptions
            code_script: The code being analyzed
            accessed_columns: Columns accessed in the code
            task_description: Description of the downstream task
            data_stats: Optional data statistics for enrichment

        Returns:
            List of ConstraintIR objects with both GX and Deequ code

        Raises:
            LLMOutputError: If generation fails or returns invalid data
        """
        if not assumptions:
            return []

        # Format inputs for LLM
        assumptions_json = self._format_assumptions(assumptions)
        accessed_str = ", ".join(accessed_columns)
        gx_sigs_str = self._format_gx_signatures()
        deequ_sigs_str = self._format_deequ_signatures()

        # Prepend line numbers so the LLM can reference them accurately
        numbered_code = _add_line_numbers(code_script)

        # Use DSPy context manager
        with dspy.context(lm=self._lm):
            result = self._predictor(
                code_script=numbered_code,
                task_description=task_description,
                accessed_columns=accessed_str,
                assumptions=assumptions_json,
                gx_signatures=gx_sigs_str,
                deequ_signatures=deequ_sigs_str,
            )

        # Parse the LLM output
        try:
            constraints_dict = result.constraints
            if not isinstance(constraints_dict, dict):
                raise ValueError(f"Expected dict, got {type(constraints_dict)}")

            # Build mapping of assumptions by column for linkage
            assumptions_by_column: dict[str, list[AssumptionIR]] = {}
            for assumption in assumptions:
                for col in assumption.columns:
                    if col not in assumptions_by_column:
                        assumptions_by_column[col] = []
                    assumptions_by_column[col].append(assumption)

            # Parse constraints
            constraints: list[ConstraintIR] = []
            for column, codes in constraints_dict.items():
                if not isinstance(codes, dict):
                    continue

                gx_codes = codes.get("gx", [])
                deequ_codes = codes.get("deequ", [])

                if not isinstance(gx_codes, list):
                    gx_codes = [gx_codes] if gx_codes else []
                if not isinstance(deequ_codes, list):
                    deequ_codes = [deequ_codes] if deequ_codes else []

                # Get related assumptions for this column (support many-to-many)
                related_assumptions = assumptions_by_column.get(column, [])
                assumption_ids = [a.id for a in related_assumptions] if related_assumptions else []

                # Parse GX and Deequ code
                for gx_code, deequ_code in zip(gx_codes, deequ_codes):
                    # Parse each format independently, catching errors separately
                    gx_spec = None
                    if gx_code:
                        try:
                            gx_spec = parse_gx_expectation(gx_code)
                        except Exception as _e:
                            logger.debug("Skipping invalid GX code for column %s: %s", column, _e)

                    deequ_spec = None
                    if deequ_code:
                        try:
                            deequ_spec = parse_deequ_constraint(deequ_code)
                        except Exception as _e:
                            logger.debug("Skipping invalid Deequ code for column %s: %s", column, _e)

                    # Skip if both failed to parse AND no raw code available
                    if not gx_spec and not deequ_spec and not gx_code and not deequ_code:
                        continue
                    # Skip if no structured parse succeeded at all
                    if not gx_spec and not deequ_spec:
                        continue

                    # Infer constraint type from assumption or code
                    constraint_type = None
                    if related_assumptions:
                        constraint_type = related_assumptions[0].constraint_type

                    # Create ConstraintIR — preserve raw code for fallback display
                    try:
                        constraint = ConstraintIR(
                            id=f"constraint-{uuid.uuid4().hex[:8]}",
                            assumption_ids=assumption_ids,
                            column=column,
                            columns=[column],  # Single column for now
                            column_type="",  # Will be enriched later
                            type=constraint_type or "unknown",
                            code_gx=gx_spec,
                            code_deequ=deequ_spec,
                            raw_gx_code=gx_code if gx_code and not gx_spec else None,
                            raw_deequ_code=deequ_code if deequ_code and not deequ_spec else None,
                            data_stats=data_stats or {},
                            label=f"{column} ({constraint_type})" if constraint_type else column,
                        )
                        constraints.append(constraint)
                    except Exception:
                        # Skip if ConstraintIR creation fails
                        continue

            if not constraints:
                raise LLMOutputError(
                    f"Constraint generation produced no valid constraints. "
                    f"Raw output: {constraints_dict!r}"
                )

            return constraints

        except (KeyError, TypeError, ValueError) as e:
            raise LLMOutputError(
                f"Failed to parse constraint generation output: {e}. "
                f"Raw output: {result.constraints!r}"
            ) from e

    def generate_parallel(
        self,
        *,
        assumptions: Sequence[AssumptionIR],
        code_script: str,
        accessed_columns: Sequence[str],
        task_description: str,
        data_stats: dict | None = None,
        max_workers: int | None = 5,
        item_done_callback: "Callable[[int, int], None] | None" = None,
        item_result_callback: "Callable[[AssumptionIR, list[ConstraintIR]], None] | None" = None,
    ) -> list[ConstraintIR]:
        """Generate constraints in parallel per assumption (faster for many assumptions).

        This method processes each assumption independently in parallel,
        which is much faster when you have many assumptions.

        Args:
            assumptions: List of extracted assumptions
            code_script: The code being analyzed
            accessed_columns: Columns accessed in the code
            task_description: Description of the downstream task
            data_stats: Optional data statistics for enrichment
            max_workers: Maximum number of parallel LLM calls (default 5)

        Returns:
            List of ConstraintIR objects with both GX and Deequ code

        Raises:
            LLMOutputError: If generation fails for all assumptions
        """
        if not assumptions:
            return []

        # Create generation function for a single assumption
        def generate_for_assumption(assumption: AssumptionIR) -> list[ConstraintIR]:
            try:
                # Generate constraints for this assumption only
                return self.generate(
                    assumptions=[assumption],  # Single assumption
                    code_script=code_script,
                    accessed_columns=accessed_columns,
                    task_description=task_description,
                    data_stats=data_stats,
                )
            except LLMOutputError as e:
                logger.warning(f"Constraint generation failed for assumption '{assumption.text[:60]}': {e}")
                return []

        # Run generations in parallel
        results_per_assumption = run_in_parallel_with_progress(
            generate_for_assumption,
            assumptions,
            max_workers=max_workers,
            done_callback=item_done_callback,
            item_result_callback=item_result_callback,
        )

        # Flatten results
        all_constraints: list[ConstraintIR] = []
        for constraints in results_per_assumption:
            all_constraints.extend(constraints)

        if not all_constraints:
            raise LLMOutputError(
                f"Parallel constraint generation returned no valid constraints "
                f"for any of the {len(assumptions)} assumptions"
            )

        return all_constraints

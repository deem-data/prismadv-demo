"""Constraint gap analysis — decides whether existing constraints sufficiently cover an assumption."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Sequence

logger = logging.getLogger(__name__)

try:
    import dspy
except ImportError:
    raise ImportError(
        "dspy is required for generation module. "
        "Install with: uv sync --extra dspy"
    )

from prismadv.ir import AssumptionIR, ConstraintIR
from prismadv.ir.deequ import load_deequ_constraint_signatures
from prismadv.ir.gx import load_gx_expectation_signatures, parse_gx_expectation
from prismadv.ir.deequ import parse_deequ_constraint
from prismadv.generation.line_numbers import _add_line_numbers
from prismadv.generation.signatures import ConstraintCodeGenerationSig


class ConstraintGapAnalysisSig(dspy.Signature):
    """You are part of a task-aware data validation system. Your role is to analyze
    whether an assumption about data quality is ALREADY SUFFICIENTLY covered by
    existing constraints, or whether additional constraints are needed.

    You will receive:
    1. An assumption about the data (natural language)
    2. The column(s) involved
    3. Existing constraint code (Great Expectations and/or Deequ) already linked to this assumption

    Your task:
    - Analyze whether the existing constraints fully cover the assumption
    - If coverage is sufficient, return has_gap = False and explain why
    - If there are gaps (aspects of the assumption not validated), return has_gap = True
      and describe what is missing in gap_description

    Be precise: a constraint covers an assumption only if it actually validates
    the specific property described. For example, a non-null check does NOT cover
    a range assumption, even if they're on the same column.
    """

    assumption_text: str = dspy.InputField(desc="The data quality assumption to check coverage for")
    column: str = dspy.InputField(desc="The column this assumption applies to")
    existing_constraints: str = dspy.InputField(desc="JSON list of existing constraint code (GE + Deequ) already linked to this assumption")
    has_gap: bool = dspy.OutputField(desc="True if there are coverage gaps that need new constraints")
    gap_description: str = dspy.OutputField(desc="Description of what is missing, or 'Coverage is sufficient' if no gaps")


class ConstraintGapAnalyzer:
    """Analyzes whether existing constraints sufficiently cover an assumption.

    If gaps are found, generates only the missing constraints.
    If no gaps, returns an empty list with a descriptive message.
    """

    def __init__(self, lm: dspy.LM):
        self._lm = lm
        self._gap_predictor = dspy.Predict(ConstraintGapAnalysisSig)
        self._gen_predictor = dspy.Predict(ConstraintCodeGenerationSig)
        self._gx_sigs = load_gx_expectation_signatures()
        self._deequ_sigs = load_deequ_constraint_signatures()

    def analyze_and_generate(
        self,
        *,
        assumption: AssumptionIR,
        existing_constraints_code: list[dict[str, str]],
        code_script: str,
        task_description: str,
    ) -> tuple[list[ConstraintIR], str]:
        """Analyze gaps and generate only missing constraints.

        Args:
            assumption: The assumption to check coverage for
            existing_constraints_code: List of dicts with 'greatExpectations' and 'deequ' keys
            code_script: The task code being analyzed
            task_description: Description of the downstream task

        Returns:
            Tuple of (new_constraints, message).
            If no gaps: ([], "Coverage is sufficient: <reason>")
            If gaps: (new_constraints, "Generated N new constraints: <gap_description>")
        """
        # Format existing constraints for the LLM
        existing_json = json.dumps(existing_constraints_code, indent=2)

        # Step 1: Gap analysis
        with dspy.context(lm=self._lm):
            gap_result = self._gap_predictor(
                assumption_text=assumption.text,
                column=assumption.columns[0] if assumption.columns else "",
                existing_constraints=existing_json,
            )

        has_gap = gap_result.has_gap
        gap_description = gap_result.gap_description or ""

        # Normalize: DSPy may return string "True"/"False" instead of bool
        if isinstance(has_gap, str):
            has_gap = has_gap.strip().lower() in ("true", "yes", "1")

        if not has_gap:
            msg = f"Coverage is sufficient: {gap_description}" if gap_description else "Coverage is sufficient."
            logger.info(f"No constraint gaps found for assumption '{assumption.text[:60]}': {gap_description}")
            return [], msg

        logger.info(f"Constraint gaps found for assumption '{assumption.text[:60]}': {gap_description}")

        # Step 2: Generate only the missing constraints, telling the LLM what already exists
        augmented_assumption_text = (
            f"{assumption.text}\n\n"
            f"IMPORTANT: The following constraints ALREADY exist for this assumption — "
            f"do NOT regenerate them. Only generate constraints for the MISSING aspects:\n"
            f"Gap identified: {gap_description}\n\n"
            f"Existing constraints:\n{existing_json}"
        )

        assumptions_json = json.dumps([{
            "text": augmented_assumption_text,
            "columns": assumption.columns,
            "type": assumption.constraint_type or "general",
            "sources": [
                {"start_line": s.start_line, "end_line": s.end_line}
                for s in assumption.sources
            ],
        }], indent=2)

        gx_sigs_str = self._format_gx_signatures()
        deequ_sigs_str = self._format_deequ_signatures()
        numbered_code = _add_line_numbers(code_script)
        accessed_str = ", ".join(assumption.columns)

        with dspy.context(lm=self._lm):
            gen_result = self._gen_predictor(
                code_script=numbered_code,
                task_description=task_description,
                accessed_columns=accessed_str,
                assumptions=assumptions_json,
                gx_signatures=gx_sigs_str,
                deequ_signatures=deequ_sigs_str,
            )

        # Parse constraints from the LLM output
        constraints = self._parse_constraints(gen_result.constraints, assumption)

        if constraints:
            msg = f"Generated {len(constraints)} new constraint{'s' if len(constraints) != 1 else ''}: {gap_description}"
        else:
            msg = f"Gap identified ({gap_description}) but no valid constraints could be generated."

        return constraints, msg

    def _parse_constraints(
        self,
        constraints_dict: dict,
        assumption: AssumptionIR,
    ) -> list[ConstraintIR]:
        """Parse LLM output into ConstraintIR objects."""
        if not isinstance(constraints_dict, dict):
            return []

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

            for gx_code, deequ_code in zip(gx_codes, deequ_codes):
                gx_spec = None
                if gx_code:
                    try:
                        gx_spec = parse_gx_expectation(gx_code)
                    except Exception as e:
                        logger.debug("Skipping invalid GX code for column %s: %s", column, e)

                deequ_spec = None
                if deequ_code:
                    try:
                        deequ_spec = parse_deequ_constraint(deequ_code)
                    except Exception as e:
                        logger.debug("Skipping invalid Deequ code for column %s: %s", column, e)

                if not gx_spec and not deequ_spec:
                    continue

                constraint_type = assumption.constraint_type or "general"
                try:
                    constraint = ConstraintIR(
                        id=f"constraint-{uuid.uuid4().hex[:8]}",
                        assumption_ids=[assumption.id],
                        column=column,
                        columns=[column],
                        column_type="",
                        type=constraint_type,
                        code_gx=gx_spec,
                        code_deequ=deequ_spec,
                        raw_gx_code=gx_code if gx_code and not gx_spec else None,
                        raw_deequ_code=deequ_code if deequ_code and not deequ_spec else None,
                        data_stats={},
                        label=f"{column} ({constraint_type})",
                    )
                    constraints.append(constraint)
                except Exception:
                    continue

        return constraints

    def _format_gx_signatures(self) -> str:
        lines = []
        for name, sig in sorted(self._gx_sigs.items()):
            desc = sig.description or ""
            all_params = list(sig.args.keys()) + list(sig.other_parameters.keys())
            params = ", ".join([f"{p}=..." for p in all_params])
            lines.append(f"{sig.type}({params})")
            if desc:
                lines.append(f"  # {desc}")
        return "\n".join(lines)

    def _format_deequ_signatures(self) -> str:
        lines = []
        for name, sig in sorted(self._deequ_sigs.items()):
            desc = sig.description or ""
            params = ", ".join(sig.required + [f"{p}=..." for p in sig.optional])
            lines.append(f".{name}({params})")
            if desc:
                lines.append(f"  # {desc}")
            if sig.examples:
                for ex in sig.examples[:2]:
                    lines.append(f"  # Example: {ex}")
        return "\n".join(lines)

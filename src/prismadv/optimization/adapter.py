"""PrismaDV adapter for the GEPA optimization loop.

Connects the three demo LLM modules (ColumnAccessDetector, AssumptionExtractor,
ConstraintGenerator) to the GEPA evaluate / make_reflective_dataset interface.
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import dspy
except ImportError:
    raise ImportError(
        "dspy is required for the optimization module. "
        "Install with: uv sync --extra dspy"
    )

from prismadv.generation.orchestrator import GenerationContext, GenerationOrchestrator
from prismadv.generation.column_access import ColumnAccessDetector
from prismadv.generation.assumption_extractor import AssumptionExtractor
from prismadv.generation.constraint_generator import ConstraintGenerator
from prismadv.ir.constraints import ConstraintIR
from prismadv.ir.assumptions import AssumptionIR
from prismadv.optimization.injector import apply_error_config
from prismadv.optimization.metrics import ColumnOutcome, compute_cfpr, compute_fpr, unit_score
from prismadv.optimization.training import TrainingUnit
from prismadv.validation.gx_validator import GreatExpectationsValidator
from prismadv.validation.models import (
    ConstraintCode,
    ValidationConstraint,
    ValidationStatus,
)

# Component names used as keys throughout GEPA
COMPONENT_COLUMN_ACCESS = "column_access"
COMPONENT_ASSUMPTION_EXTRACTION = "assumption_extraction"
COMPONENT_CONSTRAINT_GENERATION = "constraint_generation"
ALL_COMPONENTS = [COMPONENT_COLUMN_ACCESS, COMPONENT_ASSUMPTION_EXTRACTION, COMPONENT_CONSTRAINT_GENERATION]


@dataclass
class EvaluationBatch:
    """Result of evaluating a batch of training units."""
    # Per-unit quality scores in [0, 1]
    scores: list[float]
    # Per-unit column outcomes (for CFPr / FPr computation)
    column_outcomes: list[list[ColumnOutcome]]
    # Per-unit generation contexts (set when capture_traces=True)
    contexts: list[GenerationContext | None] = field(default_factory=list)
    # Per-unit DataFrames of corrupted data (set when capture_traces=True)
    eval_dfs: list[pd.DataFrame | None] = field(default_factory=list)


def _extract_instructions(orchestrator: GenerationOrchestrator) -> dict[str, str]:
    """Extract current instruction texts from the three DSPy predictors."""
    return {
        COMPONENT_COLUMN_ACCESS: orchestrator._column_detector._predictor.signature.instructions,
        COMPONENT_ASSUMPTION_EXTRACTION: orchestrator._assumption_extractor._predictor.signature.instructions,
        COMPONENT_CONSTRAINT_GENERATION: orchestrator._constraint_generator._predictor.signature.instructions,
    }


def _patch_instructions(orchestrator: GenerationOrchestrator, candidate: dict[str, str]) -> None:
    """Patch the three DSPy predictor signatures in-place on a fresh orchestrator."""
    if COMPONENT_COLUMN_ACCESS in candidate:
        sig = orchestrator._column_detector._predictor.signature
        orchestrator._column_detector._predictor.signature = sig.with_instructions(
            candidate[COMPONENT_COLUMN_ACCESS]
        )
    if COMPONENT_ASSUMPTION_EXTRACTION in candidate:
        sig = orchestrator._assumption_extractor._predictor.signature
        orchestrator._assumption_extractor._predictor.signature = sig.with_instructions(
            candidate[COMPONENT_ASSUMPTION_EXTRACTION]
        )
    if COMPONENT_CONSTRAINT_GENERATION in candidate:
        sig = orchestrator._constraint_generator._predictor.signature
        orchestrator._constraint_generator._predictor.signature = sig.with_instructions(
            candidate[COMPONENT_CONSTRAINT_GENERATION]
        )


def _constraint_ir_to_validation(c: ConstraintIR) -> ValidationConstraint | None:
    """Convert a ConstraintIR to a ValidationConstraint for the GX validator."""
    if c.code_gx is None:
        return None
    # Build the snake_case function-call representation, e.g.:
    # "expect_column_values_to_not_be_null(column='name')"
    kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in c.code_gx.kwargs.items())
    gx_str = f"{c.code_gx.type}({kwargs_str})"

    return ValidationConstraint(
        id=c.id,
        column=c.column,
        enabled=c.enabled,
        code=ConstraintCode(great_expectations=gx_str, deequ=None),
        label=c.label,
    )


def _validate_constraints_on_df(
    constraints: list[ConstraintIR],
    df: pd.DataFrame,
) -> dict[str, bool]:
    """Run GX validation on a DataFrame. Returns {constraint_id: fires_bool}.

    'fires' = True when the constraint FAILS (i.e., the constraint catches a problem).
    """
    val_constraints = []
    id_map: dict[str, str] = {}  # val_constraint.id → constraint_ir.id (same here)
    for c in constraints:
        vc = _constraint_ir_to_validation(c)
        if vc is not None:
            val_constraints.append(vc)
            id_map[c.id] = c.id

    if not val_constraints:
        return {}

    # Write DataFrame to temp CSV for the GX validator
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        df.to_csv(tmp.name, index=False)
        tmp_path = tmp.name

    try:
        validator = GreatExpectationsValidator()
        report = validator.validate_csv(
            tmp_path,
            dataset_id="gepa-eval",
            constraints=val_constraints,
        )
    except Exception as exc:
        logger.warning("GX validation failed: %s", exc)
        return {}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    return {
        item.constraint_id: (item.status == ValidationStatus.FAILED)
        for item in report.items
    }


def _compute_column_outcomes(
    ctx: GenerationContext,
    fire_map: dict[str, bool],
    v_binary: int,
) -> list[ColumnOutcome]:
    """Build per-column outcomes from GX validation results."""
    # Group constraints by column
    col_to_constraints: dict[str, list[ConstraintIR]] = {}
    for c in ctx.constraints:
        col_to_constraints.setdefault(c.column, []).append(c)

    outcomes: list[ColumnOutcome] = []
    for col, col_constraints in col_to_constraints.items():
        constraint_fires: dict[str, bool] = {
            c.id: fire_map.get(c.id, False) for c in col_constraints
        }
        col_fires = any(constraint_fires.values())
        outcomes.append(ColumnOutcome(
            column=col,
            column_fires=col_fires,
            v_binary=v_binary,
            constraint_fires=constraint_fires,
        ))

    return outcomes


class PrismaDVAdapter:
    """Connects the PrismaDV generation pipeline to the GEPA engine.

    evaluate():
        Creates a fresh GenerationOrchestrator with the given candidate
        instructions, runs the full constraint generation pipeline on
        each training unit's clean CSV, then validates the generated
        constraints against the corrupted CSV (or clean CSV for v=1 units).

    make_reflective_dataset():
        Backtraces failing constraints to their source assumptions and code
        lines, then formats structured feedback for the instruction proposer.
    """

    def __init__(self, lm: dspy.LM, max_parallel_llm_calls: int = 3):
        self._lm = lm
        self._max_parallel = max_parallel_llm_calls

    # ------------------------------------------------------------------
    # evaluate()
    # ------------------------------------------------------------------

    def evaluate(
        self,
        batch: list[TrainingUnit],
        candidate: dict[str, str],
        capture_traces: bool = False,
        on_unit_done: Callable[[int, int], None] | None = None,
    ) -> EvaluationBatch:
        """Evaluate a candidate instruction set on a batch of training units.

        Args:
            on_unit_done: Optional callback(units_done, total_units) called after
                each unit completes. Use for sub-step progress reporting.
        """
        scores: list[float] = []
        all_col_outcomes: list[list[ColumnOutcome]] = []
        contexts: list[GenerationContext | None] = []
        eval_dfs: list[pd.DataFrame | None] = []
        total = len(batch)

        for i, unit in enumerate(batch):
            try:
                score, col_outcomes, ctx, eval_df = self._evaluate_unit(
                    unit, candidate, capture_traces
                )
            except Exception as exc:
                logger.warning("Evaluation failed for unit %s/%s/%d: %s",
                               unit.dataset, unit.task_name, unit.error_config_id, exc)
                score, col_outcomes, ctx, eval_df = 0.0, [], None, None

            scores.append(score)
            all_col_outcomes.append(col_outcomes)
            if capture_traces:
                contexts.append(ctx)
                eval_dfs.append(eval_df)

            if on_unit_done:
                on_unit_done(i + 1, total)

        return EvaluationBatch(
            scores=scores,
            column_outcomes=all_col_outcomes,
            contexts=contexts if capture_traces else [],
            eval_dfs=eval_dfs if capture_traces else [],
        )

    def _evaluate_unit(
        self,
        unit: TrainingUnit,
        candidate: dict[str, str],
        capture_traces: bool,
    ) -> tuple[float, list[ColumnOutcome], GenerationContext | None, pd.DataFrame | None]:
        # 1. Create a fresh orchestrator and patch its instructions
        orch = GenerationOrchestrator(
            lm=self._lm,
            max_parallel_llm_calls=self._max_parallel,
        )
        _patch_instructions(orch, candidate)

        # 2. Run generation on the clean CSV
        ctx = orch.generate(
            task_code=unit.task_script,
            task_file_name=f"{unit.task_name}.py",
            dataset_path=unit.clean_csv_path,
            task_description=f"Analysis task on {unit.dataset} dataset",
        )

        if not ctx.constraints:
            return 0.0, [], ctx if capture_traces else None, None

        # 3. Get the eval DataFrame (clean or corrupted)
        clean_df = pd.read_csv(unit.clean_csv_path)
        if unit.v_binary == 0 and unit.error_config:
            eval_df = apply_error_config(clean_df, unit.error_config)
        else:
            eval_df = clean_df

        # 4. Validate constraints against eval DataFrame
        fire_map = _validate_constraints_on_df(ctx.constraints, eval_df)

        # 5. Compute per-column outcomes and unit score
        col_outcomes = _compute_column_outcomes(ctx, fire_map, unit.v_binary)
        score = unit_score(col_outcomes)

        return score, col_outcomes, ctx if capture_traces else None, eval_df if capture_traces else None

    # ------------------------------------------------------------------
    # make_reflective_dataset()
    # ------------------------------------------------------------------

    def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """Build structured feedback for the instruction proposer.

        For each unit in the eval batch, identifies false-alarm constraints
        (fire on clean data when v=1) or missed-detection constraints
        (don't fire on corrupted data when v=0), then backtraces to the
        source assumptions and code lines.

        Returns:
            {component_name: [feedback_dict, ...]} for each component.
        """
        feedback: dict[str, list[dict[str, Any]]] = {comp: [] for comp in components_to_update}

        for i, (col_outcomes, ctx) in enumerate(
            zip(eval_batch.column_outcomes, eval_batch.contexts)
        ):
            if ctx is None:
                continue

            # Build assumption lookup: assumption_id → AssumptionIR
            assumption_map: dict[str, AssumptionIR] = {a.id: a for a in ctx.assumptions}

            for col_outcome in col_outcomes:
                is_false_alarm = col_outcome.column_fires and col_outcome.v_binary == 1
                is_missed = not col_outcome.column_fires and col_outcome.v_binary == 0

                if not (is_false_alarm or is_missed):
                    continue  # No actionable feedback for this column

                # Collect the problematic constraints for this column
                problem_constraints = [
                    c for c in ctx.constraints
                    if c.column == col_outcome.column
                    and col_outcome.constraint_fires.get(c.id, False) == is_false_alarm
                ]

                for c in problem_constraints[:2]:  # Limit to 2 per column
                    # Backtrace: constraint → assumptions → source lines
                    linked_assumptions = [
                        assumption_map[aid]
                        for aid in c.assumption_ids
                        if aid in assumption_map
                    ]

                    assumption_texts = [a.text for a in linked_assumptions]
                    source_lines = [
                        span.start_line
                        for a in linked_assumptions
                        for span in a.sources
                    ]
                    gx_code = (
                        f"{c.code_gx.type}({', '.join(f'{k}={repr(v)}' for k, v in c.code_gx.kwargs.items())})"
                        if c.code_gx else "N/A"
                    )

                    feedback_text = (
                        f"FALSE ALARM: constraint fires on clean data — too strict or misidentified issue"
                        if is_false_alarm
                        else f"MISSED DETECTION: constraint did not fire on corrupted data — too permissive"
                    )

                    record = {
                        "Inputs": {
                            "task_code_excerpt": ctx.task_code[:500],
                            "column": col_outcome.column,
                            "assumption_texts": assumption_texts,
                            "source_lines": source_lines,
                        },
                        "Generated Outputs": {
                            "constraint_type": c.type,
                            "gx_code": gx_code,
                            "assumption_count": len(linked_assumptions),
                        },
                        "Feedback": feedback_text,
                    }

                    # Route feedback to the appropriate component
                    if COMPONENT_CONSTRAINT_GENERATION in components_to_update:
                        feedback[COMPONENT_CONSTRAINT_GENERATION].append(record)
                    if COMPONENT_ASSUMPTION_EXTRACTION in components_to_update and assumption_texts:
                        feedback[COMPONENT_ASSUMPTION_EXTRACTION].append({
                            "Inputs": record["Inputs"],
                            "Generated Outputs": {"assumptions": assumption_texts},
                            "Feedback": feedback_text,
                        })

        return feedback

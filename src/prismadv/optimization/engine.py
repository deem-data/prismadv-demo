"""GEPA optimization engine — implements Algorithm 1 from the paper.

Selective Informative Feedback for Task Adaptation:
  - Condenses training set to units with failing constraints
  - Repeatedly samples mini-batches → proposes new instructions → accepts if improved
  - Returns the best candidate by eval-set score
"""

from __future__ import annotations

import logging
import random
from typing import Callable

logger = logging.getLogger(__name__)

try:
    import dspy
except ImportError:
    raise ImportError(
        "dspy is required for the optimization module. "
        "Install with: uv sync --extra dspy"
    )

from prismadv.generation.orchestrator import GenerationOrchestrator
from prismadv.optimization.adapter import (
    ALL_COMPONENTS,
    COMPONENT_CONSTRAINT_GENERATION,
    EvaluationBatch,
    PrismaDVAdapter,
    _extract_instructions,
)
from prismadv.optimization.metrics import compute_cfpr, compute_fpr, select_low_fpr
from prismadv.optimization.proposer import InstructionProposer
from prismadv.optimization.result import OptimizationResult
from prismadv.optimization.state import OptimizationState
from prismadv.optimization.training import TrainingUnit


def run_gepa(
    lm: dspy.LM,
    training_units: list[TrainingUnit],
    *,
    n_rounds: int = 3,
    n_train: int = 3,
    n_eval: int = 10,
    n_fb: int = 3,
    budget: int = 3,
    proposer_lm: dspy.LM | None = None,
    progress_callback: Callable[[float, str], None] | None = None,
) -> OptimizationResult:
    """Run the GEPA prompt optimization algorithm.

    Args:
        lm: DSPy language model for both generation and proposal
        training_units: Pre-loaded (task, batch) pairs with binary labels
        n_rounds: Number of optimization rounds
        n_train: Mini-batch size for training
        n_eval: Eval sample size (fixed within each round)
        n_fb: Number of low-FPr constraints to backtrace per column
        budget: Total number of full eval evaluations (across all rounds)
        progress_callback: Optional callback(progress_0_to_1, message)

    Returns:
        OptimizationResult with before/after instructions and scores
    """
    # Clear LM history so we only measure cost from this run
    if hasattr(lm, "history"):
        lm.history.clear()

    def report(progress: float, msg: str) -> None:
        logger.info("Optimization [%.0f%%] %s", progress * 100, msg)
        if progress_callback:
            progress_callback(progress, msg)

    def make_unit_callback(p_start: float, p_end: float, label: str) -> "Callable[[int, int], None]":
        """Returns an on_unit_done callback that interpolates progress between p_start and p_end."""
        def cb(done: int, total: int) -> None:
            frac = done / max(total, 1)
            report(p_start + frac * (p_end - p_start), f"{label} ({done}/{total} units)")
        return cb

    report(0.0, f"Initialising optimizer — {len(training_units)} units, {n_rounds} rounds, budget {budget}")

    if not training_units:
        raise ValueError("No training units provided for optimization")

    # Summarise datasets in the training units
    datasets_in_units = set(u.dataset for u in training_units)
    tasks_in_units = set(u.task_name for u in training_units)
    report(0.0, f"Datasets: {', '.join(sorted(datasets_in_units))} | Tasks: {len(tasks_in_units)} unique scripts")

    adapter = PrismaDVAdapter(lm=lm)
    proposer_label = "separate proposer LM" if proposer_lm else "same LM"
    proposer = InstructionProposer(lm=proposer_lm or lm)
    report(0.0, f"Execution LM: {lm.model} | Proposer: {proposer_label}")

    # -----------------------------------------------------------------------
    # Extract initial (baseline) instructions
    # -----------------------------------------------------------------------
    baseline_orch = GenerationOrchestrator(lm=lm)
    initial_candidate = _extract_instructions(baseline_orch)

    state = OptimizationState()
    budget_remaining = budget

    total_steps = n_rounds * budget + 2  # rough denominator for progress
    step = 0

    # -----------------------------------------------------------------------
    # Step 1: Score initial candidate on eval sample
    # -----------------------------------------------------------------------
    if len(training_units) > n_eval:
        eval_sample = random.sample(training_units, n_eval)
    else:
        eval_sample = list(training_units)
    report(step / total_steps, f"Step 1/3: Evaluating baseline prompts on {len(eval_sample)} eval units...")

    eval_batch_0 = adapter.evaluate(
        eval_sample, initial_candidate, capture_traces=False,
        on_unit_done=make_unit_callback(step / total_steps, (step + 1) / total_steps, "Baseline eval"),
    )
    eval_score_0 = sum(eval_batch_0.scores) / max(len(eval_batch_0.scores), 1)

    state.add_candidate(initial_candidate, eval_score_0)
    step += 1
    report(step / total_steps, f"Baseline score: {eval_score_0:.3f} (CFPr on {len(eval_sample)} units)")

    # -----------------------------------------------------------------------
    # Step 2: Condense training set (only units with failing constraints)
    # -----------------------------------------------------------------------
    report(step / total_steps, f"Step 2/3: Condensing — running constraints on {len(training_units)} units to find informative ones...")
    condensed = _condense_training_set(
        adapter, training_units, initial_candidate,
        on_unit_done=make_unit_callback(step / total_steps, (step + 1) / total_steps, "Condensing"),
    )
    if not condensed:
        logger.warning("All constraints pass on training set — using full training set")
        condensed = training_units
        report(step / total_steps, f"All constraints passed — using full set ({len(condensed)} units)")
    else:
        report(step / total_steps, f"Condensed: {len(condensed)}/{len(training_units)} units have failing constraints")
    step += 1

    # -----------------------------------------------------------------------
    # Rounds
    # -----------------------------------------------------------------------
    budget_per_round = max(1, budget_remaining // max(n_rounds, 1))

    for round_idx in range(n_rounds):
        round_budget = min(budget_per_round, budget_remaining)
        round_start_step = step

        report(
            step / total_steps,
            f"Step 3/3: Round {round_idx + 1}/{n_rounds} — {round_budget} iteration(s), best score so far: {state.best_eval_score:.3f}",
        )

        current_candidate = state.best_candidate
        round_candidates: list[tuple[dict[str, str], float]] = [(current_candidate, state.best_eval_score)]

        inner_step = 0
        while inner_step < round_budget and budget_remaining > 0:
            iter_label = f"R{round_idx + 1} iter {inner_step + 1}/{round_budget}"

            # -----------------------------------------------------------------
            # Sample mini-batch
            # -----------------------------------------------------------------
            if len(condensed) > n_train:
                minibatch = random.sample(condensed, n_train)
            else:
                minibatch = list(condensed)
            mb_tasks = [u.task_name for u in minibatch]
            report(
                (step + inner_step) / total_steps,
                f"{iter_label}: Sampled mini-batch of {len(minibatch)} units — {', '.join(mb_tasks)}",
            )

            # -----------------------------------------------------------------
            # Evaluate current candidate on mini-batch (with traces)
            # -----------------------------------------------------------------
            report(
                (step + inner_step) / total_steps,
                f"{iter_label}: Running generation pipeline + validation on mini-batch...",
            )

            eval_train = adapter.evaluate(minibatch, current_candidate, capture_traces=True)
            train_score_before = sum(eval_train.scores) / max(len(eval_train.scores), 1)

            # Flatten all column outcomes for CFPr / FPr
            all_outcomes = [o for outcomes in eval_train.column_outcomes for o in outcomes]
            n_false_alarms = sum(1 for o in all_outcomes if o.column_fires and o.v_binary == 1)
            n_missed = sum(1 for o in all_outcomes if not o.column_fires and o.v_binary == 0)
            fpr = compute_fpr(all_outcomes)
            low_fpr_constraints = select_low_fpr(fpr, n_fb)

            report(
                (step + inner_step) / total_steps,
                f"{iter_label}: Train score {train_score_before:.3f} | {n_false_alarms} false alarms, {n_missed} missed detections across {len(all_outcomes)} columns",
            )

            # -----------------------------------------------------------------
            # Build reflective dataset and propose new instructions
            # -----------------------------------------------------------------
            reflective_ds = adapter.make_reflective_dataset(
                current_candidate,
                eval_train,
                ALL_COMPONENTS,
            )
            n_feedback = sum(len(v) for v in reflective_ds.values())
            report(
                (step + inner_step) / total_steps,
                f"{iter_label}: Built {n_feedback} feedback examples — proposing new instructions...",
            )

            new_candidate = proposer.propose(
                current_candidate=current_candidate,
                reflective_dataset=reflective_ds,
                components_to_update=ALL_COMPONENTS,
            )

            # -----------------------------------------------------------------
            # Evaluate new candidate on SAME mini-batch (without traces)
            # -----------------------------------------------------------------
            report(
                (step + inner_step) / total_steps,
                f"{iter_label}: Evaluating proposed instructions on same mini-batch...",
            )
            eval_new = adapter.evaluate(minibatch, new_candidate, capture_traces=False)
            train_score_after = sum(eval_new.scores) / max(len(eval_new.scores), 1)

            logger.info(
                "Round %d iter %d: train score before=%.3f after=%.3f",
                round_idx + 1, inner_step + 1, train_score_before, train_score_after,
            )

            # -----------------------------------------------------------------
            # Accept only if training score doesn't decrease
            # -----------------------------------------------------------------
            if train_score_after >= train_score_before:
                report(
                    (step + inner_step) / total_steps,
                    f"{iter_label}: Train improved {train_score_before:.3f} → {train_score_after:.3f} — scoring on full eval set...",
                )
                # Score on eval sample
                eval_new_full = adapter.evaluate(eval_sample, new_candidate, capture_traces=False)
                eval_score_new = sum(eval_new_full.scores) / max(len(eval_new_full.scores), 1)

                state.add_candidate(new_candidate, eval_score_new)
                state.record_round(
                    round_idx + 1,
                    iteration=inner_step + 1,
                    train_score_before=train_score_before,
                    train_score_after=train_score_after,
                    eval_score=eval_score_new,
                    accepted=True,
                )
                round_candidates.append((new_candidate, eval_score_new))
                current_candidate = new_candidate  # Explore from accepted candidate
                budget_remaining -= 1

                improved_marker = "NEW BEST" if eval_score_new >= state.best_eval_score else "accepted"
                report(
                    (step + inner_step + 1) / total_steps,
                    f"{iter_label}: ACCEPTED ({improved_marker}) — eval score {eval_score_new:.3f} (best: {state.best_eval_score:.3f})",
                )
            else:
                state.record_round(
                    round_idx + 1,
                    iteration=inner_step + 1,
                    train_score_before=train_score_before,
                    train_score_after=train_score_after,
                    accepted=False,
                )
                report(
                    (step + inner_step + 1) / total_steps,
                    f"{iter_label}: REJECTED — train score dropped {train_score_before:.3f} → {train_score_after:.3f}",
                )

            inner_step += 1

        step += budget_per_round

    # -----------------------------------------------------------------------
    # Final result
    # -----------------------------------------------------------------------
    best = state.best_candidate
    eval_score_final = state.best_eval_score

    llm_cost = _calculate_lm_cost(lm)
    report(1.0, f"Optimization complete. Score: {eval_score_0:.3f} → {eval_score_final:.3f}")

    return OptimizationResult(
        before_instructions=initial_candidate,
        after_instructions=best,
        eval_score_before=eval_score_0,
        eval_score_after=eval_score_final,
        n_rounds_completed=n_rounds,
        improved=eval_score_final > eval_score_0,
        llm_cost=llm_cost,
        history=state.history,
    )


def _calculate_lm_cost(lm: dspy.LM) -> float:
    """Calculate total cost from a DSPy LM's history using litellm pricing."""
    try:
        import litellm
        total = 0.0
        for entry in getattr(lm, "history", []):
            response = entry.get("response")
            if not response:
                continue
            try:
                total += litellm.completion_cost(completion_response=response)
            except Exception:
                raw = getattr(response, "usage", None)
                if raw:
                    try:
                        total += litellm.completion_cost(
                            model=getattr(response, "model", None) or lm.model,
                            prompt_tokens=getattr(raw, "prompt_tokens", 0) or 0,
                            completion_tokens=getattr(raw, "completion_tokens", 0) or 0,
                        )
                    except Exception:
                        pass
        return total
    except Exception:
        return 0.0


def _condense_training_set(
    adapter: PrismaDVAdapter,
    units: list[TrainingUnit],
    candidate: dict[str, str],
    on_unit_done: "Callable[[int, int], None] | None" = None,
) -> list[TrainingUnit]:
    """Return only training units where at least one column constraint fires.

    Condensation reduces the search space to informative units (those that
    produce failing constraints under the current prompts).
    """
    # Evaluate all units (without traces for speed)
    eval_batch = adapter.evaluate(units, candidate, capture_traces=False, on_unit_done=on_unit_done)
    condensed: list[TrainingUnit] = []
    for unit, col_outcomes in zip(units, eval_batch.column_outcomes):
        if any(o.column_fires for o in col_outcomes):
            condensed.append(unit)
    return condensed

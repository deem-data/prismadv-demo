"""Result type for GEPA optimization runs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OptimizationResult:
    """Immutable result of one GEPA optimization run."""

    # Prompt instructions before and after optimization
    before_instructions: dict[str, str]
    after_instructions: dict[str, str]

    # Aggregated quality scores (mean detection rate across eval set)
    eval_score_before: float
    eval_score_after: float

    # Metadata
    n_rounds_completed: int
    improved: bool

    # Total LLM cost incurred during the optimization run (USD)
    llm_cost: float = 0.0

    # Per-round history for debugging / display
    history: list[dict] = field(default_factory=list)

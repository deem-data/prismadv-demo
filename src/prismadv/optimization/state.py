"""Optimization state tracking for the GEPA engine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OptimizationState:
    """Mutable state for one GEPA optimization run.

    Tracks the genealogy of program candidates (each candidate is a dict
    mapping component name → instruction text) and their scores on the
    eval sample.
    """

    # Each candidate: {"column_access": str, "assumption_extraction": str, "constraint_generation": str}
    program_candidates: list[dict[str, str]] = field(default_factory=list)

    # Mean score on eval sample for each candidate (index matches program_candidates)
    eval_scores: list[float] = field(default_factory=list)

    # Index of the best candidate so far
    best_idx: int = 0

    # Per-round history (for display / debugging)
    history: list[dict] = field(default_factory=list)

    @property
    def best_candidate(self) -> dict[str, str]:
        if not self.program_candidates:
            raise IndexError("No candidates in state")
        return self.program_candidates[self.best_idx]

    @property
    def best_eval_score(self) -> float:
        if not self.eval_scores:
            return 0.0
        return self.eval_scores[self.best_idx]

    def add_candidate(self, candidate: dict[str, str], eval_score: float) -> int:
        """Register a new candidate and return its index."""
        idx = len(self.program_candidates)
        self.program_candidates.append(candidate)
        self.eval_scores.append(eval_score)
        if eval_score > self.best_eval_score:
            self.best_idx = idx
        return idx

    def record_round(self, round_num: int, **kwargs) -> None:
        self.history.append({"round": round_num, **kwargs})

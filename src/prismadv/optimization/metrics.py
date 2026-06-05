"""CFPr / FPr metric computations for GEPA.

Column-level Failure Precision (CFPr):
    P(task fails | column constraint fails)
    = (# units where column fires AND v=0) / (# units where column fires)

Constraint-level Failure Precision (FPr):
    P(task fails | this specific constraint fires)

For the demo we approximate these over a mini-batch of training units
(each unit carries a v_binary label and a per-column constraint outcome).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ColumnOutcome:
    """Per (unit, column) evaluation result."""
    column: str
    # True if ANY constraint on this column fired on the eval CSV
    column_fires: bool
    # Binary task label: 0 = task fails, 1 = task succeeds
    v_binary: int
    # Per-constraint fire outcomes {constraint_id: fires_bool}
    constraint_fires: dict[str, bool]


def compute_cfpr(outcomes: list[ColumnOutcome]) -> float:
    """Column-level failure precision over a collection of outcomes.

    CFPr = P(v=0 | column_fires) = TP / (TP + FP)

    If no columns fire in the batch, returns 0.0 (degenerate case).
    """
    fires = [o for o in outcomes if o.column_fires]
    if not fires:
        return 0.0
    true_positives = sum(1 for o in fires if o.v_binary == 0)
    return true_positives / len(fires)


def compute_fpr(outcomes: list[ColumnOutcome]) -> dict[str, float]:
    """Constraint-level failure precision: {constraint_id: FPr}.

    FPr(c) = P(v=0 | constraint c fires) for each constraint.
    Constraints that never fire get FPr = 0.0.
    """
    fires_by_constraint: dict[str, list[int]] = {}
    for o in outcomes:
        for cid, fires in o.constraint_fires.items():
            if fires:
                fires_by_constraint.setdefault(cid, []).append(o.v_binary)

    result: dict[str, float] = {}
    for cid, v_labels in fires_by_constraint.items():
        result[cid] = sum(1 for v in v_labels if v == 0) / len(v_labels)

    return result


def select_low_fpr(fpr: dict[str, float], n_fb: int) -> list[str]:
    """Return up to n_fb constraint IDs with the lowest FPr (most likely false alarms)."""
    ranked = sorted(fpr.items(), key=lambda kv: kv[1])  # ascending FPr
    return [cid for cid, _ in ranked[:n_fb]]


def unit_score(column_outcomes: list[ColumnOutcome]) -> float:
    """Aggregate quality score for one training unit.

    For corrupted units (v=0): detection rate = fraction of columns that fire.
    For clean units (v=1): precision rate = fraction of columns that do NOT fire.

    Returns a float in [0, 1], higher = better.
    """
    if not column_outcomes:
        return 0.0
    v = column_outcomes[0].v_binary
    if v == 0:
        # Detection: want constraints to fire on corrupted data
        return sum(1.0 for o in column_outcomes if o.column_fires) / len(column_outcomes)
    else:
        # Precision: want constraints NOT to fire on clean data
        return sum(1.0 for o in column_outcomes if not o.column_fires) / len(column_outcomes)

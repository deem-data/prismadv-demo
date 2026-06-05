"""GEPA prompt optimization module for PrismaDV.

Optimizes the three LLM module prompts (Column Access Detection, Assumption
Extraction, Constraint Generation) using EIDBench binary task outcomes as
training signal.

Usage::

    from prismadv.optimization import run_gepa, EIDBenchLoader

    loader = EIDBenchLoader()
    units = loader.load_training_units("IPL_win_prediction", max_units=40)
    result = run_gepa(lm=my_lm, training_units=units, n_rounds=2, budget=6)
    print(result.after_instructions)
"""

from prismadv.optimization.adapter import (
    ALL_COMPONENTS,
    COMPONENT_COLUMN_ACCESS,
    COMPONENT_ASSUMPTION_EXTRACTION,
    COMPONENT_CONSTRAINT_GENERATION,
    PrismaDVAdapter,
    _extract_instructions,
)
from prismadv.optimization.config import (
    clear_active_instructions,
    get_active_instructions,
    has_active_instructions,
    set_active_instructions,
)
from prismadv.optimization.engine import run_gepa
from prismadv.optimization.result import OptimizationResult
from prismadv.optimization.training import EIDBenchLoader, TrainingUnit

__all__ = [
    "get_active_instructions",
    "set_active_instructions",
    "clear_active_instructions",
    "has_active_instructions",
    "run_gepa",
    "EIDBenchLoader",
    "TrainingUnit",
    "OptimizationResult",
    "PrismaDVAdapter",
    "_extract_instructions",
    "ALL_COMPONENTS",
    "COMPONENT_COLUMN_ACCESS",
    "COMPONENT_ASSUMPTION_EXTRACTION",
    "COMPONENT_CONSTRAINT_GENERATION",
]

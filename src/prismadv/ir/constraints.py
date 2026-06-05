"""Internal representation for generated constraints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from prismadv.ir.deequ import DeequConstraintSpec
from prismadv.ir.gx import GXExpectationSpec


class ConstraintIR(BaseModel):
    """Internal representation of a generated data quality constraint.

    A constraint is the executable validation rule (in Deequ and/or GX format)
    that was generated from one or more AssumptionIR instances.

    Supports many-to-many: multiple assumptions can contribute to one constraint,
    and one assumption can generate multiple constraints.
    """

    model_config = ConfigDict(extra="forbid")

    # Identity
    id: str
    assumption_ids: list[str] = Field(
        default_factory=list, description="Links to AssumptionIR(s) that generated this constraint"
    )

    # Column information
    column: str  # Primary column this constraint applies to
    columns: list[str] = Field(default_factory=list)  # All columns (for multi-column constraints)
    column_type: str  # "textual", "numerical", "categorical"

    # Constraint classification
    type: str  # "completeness", "range", "enum", etc.
    # Note: Using str to avoid circular dependency with API schemas

    # Generated validation code (using existing IR types)
    code_deequ: DeequConstraintSpec | None = None
    code_gx: GXExpectationSpec | None = None

    # Raw LLM-generated code strings (fallback when parsing fails)
    raw_deequ_code: str | None = None
    raw_gx_code: str | None = None

    # Data context (from profiling)
    data_stats: dict[str, Any] = Field(default_factory=dict)

    # Extensibility
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Display
    label: str | None = None  # Human-readable label for UI
    enabled: bool = True  # Whether this constraint is active

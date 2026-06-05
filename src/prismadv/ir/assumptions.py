from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from prismadv.ir.source import SourceSpan


class AssumptionIR(BaseModel):
    """Internal representation of a data quality assumption extracted from code.

    An assumption represents an implicit constraint inferred from how the code
    uses the data (e.g., filtering, null checks, value ranges).
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str  # Human-readable description of the assumption
    sources: list[SourceSpan] = Field(default_factory=list)  # Where in code this came from

    # NEW: Column tracking for provenance
    columns: list[str] = Field(default_factory=list)  # Which columns are involved

    # NEW: Constraint type hint (helps map assumption → constraint)
    constraint_type: str | None = None  # e.g., "completeness", "range", "enum"
    # Note: Using str instead of ConstraintType enum to avoid circular dependency with API schemas

    # NEW: Extensible metadata for future use
    metadata: dict[str, Any] = Field(default_factory=dict)


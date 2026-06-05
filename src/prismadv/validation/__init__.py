from __future__ import annotations

from typing import TYPE_CHECKING

from prismadv.validation.base import BaseValidator
from prismadv.validation.errors import MissingDependencyError
from prismadv.validation.models import (
    ConstraintCode,
    ValidationConfig,
    ValidationConstraint,
    ValidationReport,
    ValidationResultItem,
    ValidationSeverity,
    ValidationStatus,
    ValidatorBackend,
)
from prismadv.validation.registry import get_validator

if TYPE_CHECKING:
    from prismadv.validation.deequ_validator import DeequValidator
    from prismadv.validation.gx_validator import GreatExpectationsValidator

__all__ = [
    "BaseValidator",
    "ConstraintCode",
    "ValidationConfig",
    "ValidationConstraint",
    "DeequValidator",
    "GreatExpectationsValidator",
    "ValidationReport",
    "ValidationResultItem",
    "ValidationSeverity",
    "ValidationStatus",
    "ValidatorBackend",
    "get_validator",
]


def __getattr__(name: str):
    if name == "DeequValidator":
        try:
            from prismadv.validation.deequ_validator import DeequValidator as cls
        except Exception as e:  # pragma: no cover
            raise MissingDependencyError(
                "Deequ validator dependencies are missing. Install with `uv sync --extra deequ`."
            ) from e
        return cls
    if name == "GreatExpectationsValidator":
        try:
            from prismadv.validation.gx_validator import GreatExpectationsValidator as cls
        except Exception as e:  # pragma: no cover
            raise MissingDependencyError(
                "Great Expectations validator dependencies are missing. Install with `uv sync --extra gx`."
            ) from e
        return cls
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


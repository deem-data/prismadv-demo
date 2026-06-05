from __future__ import annotations

from prismadv.validation.errors import MissingDependencyError
from prismadv.validation.models import ValidatorBackend


def get_validator(backend: ValidatorBackend):
    if backend == ValidatorBackend.DEEQU:
        try:
            from prismadv.validation.deequ_validator import DeequValidator
        except Exception as e:  # pragma: no cover
            raise MissingDependencyError(
                "Deequ validator dependencies are missing. Install with `uv sync --extra deequ`."
            ) from e
        return DeequValidator()
    if backend == ValidatorBackend.GREAT_EXPECTATIONS:
        try:
            from prismadv.validation.gx_validator import GreatExpectationsValidator
        except Exception as e:  # pragma: no cover
            raise MissingDependencyError(
                "Great Expectations validator dependencies are missing. Install with `uv sync --extra gx`."
            ) from e
        return GreatExpectationsValidator()
    raise ValueError(f"Unknown validator backend: {backend}")

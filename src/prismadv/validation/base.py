from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

from prismadv.validation.models import ValidationConfig, ValidationConstraint, ValidationReport, ValidatorBackend


class BaseValidator(ABC):
    backend: ValidatorBackend

    @abstractmethod
    def validate_csv(
        self,
        path: str | Path,
        *,
        dataset_id: str,
        constraints: Sequence[ValidationConstraint],
        cfg: ValidationConfig | None = None,
    ) -> ValidationReport:
        raise NotImplementedError


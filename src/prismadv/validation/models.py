from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ValidatorBackend(StrEnum):
    DEEQU = "deequ"
    GREAT_EXPECTATIONS = "great_expectations"


class ValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_details: bool = True
    include_traceback: bool = False
    max_traceback_chars: int = Field(default=10_000, ge=0, le=1_000_000)


class ConstraintCode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deequ: str | None = None
    great_expectations: str | None = None


class ValidationConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    column: str | None = None
    columns: list[str] | None = None
    severity: ValidationSeverity = ValidationSeverity.ERROR
    enabled: bool = True
    code: ConstraintCode
    label: str | None = None

    @model_validator(mode="after")
    def _check_column_selector(self):
        if self.column is None and not self.columns:
            raise ValueError("Either `column` or `columns` must be set.")
        if self.column is not None and self.columns:
            raise ValueError("Only one of `column` or `columns` can be set.")
        return self


class ValidationResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    constraint_id: str
    backend: ValidatorBackend
    status: ValidationStatus
    severity: ValidationSeverity

    column: str | None = None
    columns: list[str] | None = None
    code: str | None = None

    message: str = ""
    details: dict[str, Any] | None = None
    error: str | None = None
    traceback: str | None = None

    started_at: datetime
    finished_at: datetime
    duration_ms: int = Field(ge=0)


class ValidationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    passed: int
    failed: int
    errored: int
    skipped: int

    passed_error: int
    failed_error: int
    passed_warning: int
    failed_warning: int

    @classmethod
    def from_items(cls, items: Iterable[ValidationResultItem]) -> "ValidationSummary":
        total = passed = failed = errored = skipped = 0
        passed_error = failed_error = passed_warning = failed_warning = 0

        for item in items:
            total += 1
            if item.status == ValidationStatus.PASSED:
                passed += 1
                if item.severity == ValidationSeverity.ERROR:
                    passed_error += 1
                elif item.severity == ValidationSeverity.WARNING:
                    passed_warning += 1
            elif item.status == ValidationStatus.FAILED:
                failed += 1
                if item.severity == ValidationSeverity.ERROR:
                    failed_error += 1
                elif item.severity == ValidationSeverity.WARNING:
                    failed_warning += 1
            elif item.status == ValidationStatus.ERROR:
                errored += 1
            elif item.status == ValidationStatus.SKIPPED:
                skipped += 1

        return cls(
            total=total,
            passed=passed,
            failed=failed,
            errored=errored,
            skipped=skipped,
            passed_error=passed_error,
            failed_error=failed_error,
            passed_warning=passed_warning,
            failed_warning=failed_warning,
        )


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str
    backend: ValidatorBackend
    started_at: datetime
    finished_at: datetime
    duration_ms: int = Field(ge=0)

    items: list[ValidationResultItem]
    summary: ValidationSummary

    @classmethod
    def from_items(
        cls,
        *,
        dataset_id: str,
        backend: ValidatorBackend,
        started_at: datetime,
        finished_at: datetime,
        items: list[ValidationResultItem],
    ) -> "ValidationReport":
        duration_ms = int(max((finished_at - started_at).total_seconds() * 1000, 0))
        return cls(
            dataset_id=dataset_id,
            backend=backend,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            items=items,
            summary=ValidationSummary.from_items(items),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True)

    def save_to_yaml(self, path: str | Path) -> None:
        Path(path).write_text(self.to_yaml(), encoding="utf-8")

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ValidationReport":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)


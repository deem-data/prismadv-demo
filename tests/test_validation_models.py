from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from prismadv.validation.models import (
    ConstraintCode,
    ValidationConstraint,
    ValidationReport,
    ValidationResultItem,
    ValidationSeverity,
    ValidationStatus,
    ValidatorBackend,
)


def test_validation_constraint_requires_column_selector():
    with pytest.raises(ValueError):
        ValidationConstraint(
            id="c1",
            code=ConstraintCode(deequ='isComplete("a")'),
        )

    with pytest.raises(ValueError):
        ValidationConstraint(
            id="c1",
            column="a",
            columns=["b"],
            code=ConstraintCode(deequ='isComplete("a")'),
        )

    c = ValidationConstraint(
        id="c1",
        column="a",
        severity=ValidationSeverity.WARNING,
        code=ConstraintCode(deequ='isComplete("a")'),
    )
    assert c.column == "a"
    assert c.columns is None


def test_validation_report_summary_and_yaml_roundtrip(tmp_path):
    started_at = datetime(2026, 1, 28, tzinfo=timezone.utc)
    finished_at = started_at + timedelta(milliseconds=1234)

    items = [
        ValidationResultItem(
            constraint_id="c_ok",
            backend=ValidatorBackend.DEEQU,
            status=ValidationStatus.PASSED,
            severity=ValidationSeverity.ERROR,
            column="id",
            code='isComplete("id")',
            started_at=started_at,
            finished_at=started_at,
            duration_ms=0,
        ),
        ValidationResultItem(
            constraint_id="c_fail_warn",
            backend=ValidatorBackend.DEEQU,
            status=ValidationStatus.FAILED,
            severity=ValidationSeverity.WARNING,
            column="age",
            code='hasMin("age", 0)',
            message="Failure",
            started_at=started_at,
            finished_at=started_at,
            duration_ms=0,
        ),
        ValidationResultItem(
            constraint_id="c_skip",
            backend=ValidatorBackend.DEEQU,
            status=ValidationStatus.SKIPPED,
            severity=ValidationSeverity.ERROR,
            column="name",
            code='isComplete("name")',
            started_at=started_at,
            finished_at=started_at,
            duration_ms=0,
        ),
        ValidationResultItem(
            constraint_id="c_error",
            backend=ValidatorBackend.DEEQU,
            status=ValidationStatus.ERROR,
            severity=ValidationSeverity.ERROR,
            column="x",
            code="not valid",
            error="boom",
            started_at=started_at,
            finished_at=started_at,
            duration_ms=0,
        ),
    ]

    report = ValidationReport.from_items(
        dataset_id="ds_1",
        backend=ValidatorBackend.DEEQU,
        started_at=started_at,
        finished_at=finished_at,
        items=items,
    )

    assert report.duration_ms == 1234
    assert report.summary.total == 4
    assert report.summary.passed == 1
    assert report.summary.failed == 1
    assert report.summary.skipped == 1
    assert report.summary.errored == 1
    assert report.summary.passed_error == 1
    assert report.summary.failed_warning == 1

    path = tmp_path / "validation.yaml"
    report.save_to_yaml(path)
    loaded = ValidationReport.from_yaml(path)
    assert loaded.summary == report.summary
    assert loaded.items[0].constraint_id == "c_ok"


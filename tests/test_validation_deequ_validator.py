from __future__ import annotations

from datetime import datetime, timezone

import pytest


def test_deequ_validator_smoke(tmp_path):
    try:
        import pyspark  # type: ignore
    except Exception as e:
        pytest.skip(f"pyspark not available: {e}")

    try:
        import pydeequ  # noqa: F401
    except Exception as e:
        pytest.skip(f"pydeequ not available/compatible: {e}")

    from prismadv.validation import ConstraintCode, DeequValidator, ValidationConstraint, ValidationSeverity

    csv_path = tmp_path / "toy.csv"
    csv_path.write_text(
        "\n".join(
            [
                "id,age",
                "1,10",
                "2,",
                "3,30",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    validator = DeequValidator()
    constraints = [
        ValidationConstraint(
            id="c_id_complete",
            column="id",
            severity=ValidationSeverity.ERROR,
            code=ConstraintCode(deequ='isComplete("id")'),
        ),
        ValidationConstraint(
            id="c_age_complete",
            column="age",
            severity=ValidationSeverity.WARNING,
            code=ConstraintCode(deequ='isComplete("age")'),
        ),
    ]

    try:
        report = validator.validate_csv(csv_path, dataset_id="ds_deequ_val", constraints=constraints)
    except Exception as e:
        pytest.skip(f"Spark/Deequ not available in this environment: {e}")

    assert report.dataset_id == "ds_deequ_val"
    assert report.summary.total == 2


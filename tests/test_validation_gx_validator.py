from __future__ import annotations

import pytest


def test_gx_validator_profiles_dataset(tmp_path):
    pytest.importorskip("great_expectations")

    from prismadv.validation import ConstraintCode, GreatExpectationsValidator, ValidationConstraint, ValidationSeverity

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

    validator = GreatExpectationsValidator()
    constraints = [
        ValidationConstraint(
            id="c_id_complete",
            column="id",
            severity=ValidationSeverity.ERROR,
            code=ConstraintCode(great_expectations='validator.expect_column_values_to_not_be_null(column="id")'),
        ),
        ValidationConstraint(
            id="c_age_complete",
            column="age",
            severity=ValidationSeverity.WARNING,
            code=ConstraintCode(great_expectations='ExpectColumnValuesToNotBeNull(column="age")'),
        ),
    ]

    report = validator.validate_csv(csv_path, dataset_id="ds_gx_val", constraints=constraints)

    assert report.dataset_id == "ds_gx_val"
    assert report.summary.total == 2
    assert report.summary.passed >= 1
    assert report.summary.failed >= 1

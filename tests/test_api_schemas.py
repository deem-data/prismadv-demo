from datetime import datetime, timezone

from prismadv.api.v1.schemas import CodeFile, CodeLanguage, ConstraintCode


def test_code_file_serializes_camel_case():
    cf = CodeFile(
        id="uuid",
        name="task.py",
        language=CodeLanguage.PYTHON,
        size=1,
        content="print('hi')",
        uploaded_at=datetime(2026, 1, 28, 10, 30, tzinfo=timezone.utc),
    )
    data = cf.model_dump(by_alias=True)
    assert "uploadedAt" in data
    assert "uploaded_at" not in data


def test_constraint_code_serializes_expected_keys():
    code = ConstraintCode(great_expectations="gx()", deequ="deequ()")
    data = code.model_dump(by_alias=True)
    assert set(data.keys()) == {"greatExpectations", "deequ"}


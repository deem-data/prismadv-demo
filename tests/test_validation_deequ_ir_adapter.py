from __future__ import annotations

from prismadv.ir.deequ import parse_deequ_constraint
from prismadv.validation.deequ_validator import _apply_deequ_constraint, _deequ_lambda_assertion_to_callable


class DummyConstrainableDataTypes:
    String = object()
    Numeric = object()


class DummyCheck:
    def __init__(self):
        self.calls: list[tuple] = []

    def hasMean(self, column, assertion, hint=None):  # noqa: N802
        self.calls.append(("hasMean", column, assertion, hint))
        return self

    def hasDataType(self, column, datatype, assertion=None, hint=None):  # noqa: N802
        self.calls.append(("hasDataType", column, datatype, assertion, hint))
        return self

    def satisfies(self, columnCondition, constraintName, assertion=None, hint=None):  # noqa: N802
        self.calls.append(("satisfies", columnCondition, constraintName, assertion, hint))
        return self


def test_deequ_lambda_assertion_to_callable():
    spec = parse_deequ_constraint(".isNonNegative('x', lambda x: x >= 0.95)")
    fn = _deequ_lambda_assertion_to_callable(spec.args[1])
    assert fn(0.96) is True
    assert fn(0.94) is False


def test_deequ_apply_callspec_converts_lambda_assertion():
    spec = parse_deequ_constraint(".hasMean('gpa', lambda x: x >= 2.0 and x <= 3.5)")
    check = DummyCheck()
    _apply_deequ_constraint(check, spec, ConstrainableDataTypes=DummyConstrainableDataTypes)

    name, column, assertion, hint = check.calls[0]
    assert name == "hasMean"
    assert column == "gpa"
    assert hint is None
    assert callable(assertion)
    assert assertion(2.5) is True
    assert assertion(1.9) is False


def test_deequ_apply_callspec_converts_enum_value():
    spec = parse_deequ_constraint(".hasDataType('student_id', ConstrainableDataTypes.String)")
    check = DummyCheck()
    _apply_deequ_constraint(check, spec, ConstrainableDataTypes=DummyConstrainableDataTypes)

    name, column, datatype, assertion, hint = check.calls[0]
    assert name == "hasDataType"
    assert column == "student_id"
    assert datatype is DummyConstrainableDataTypes.String
    assert assertion is None
    assert hint is None


def test_deequ_apply_satisfies_spec_converts_lambda_assertion():
    spec = parse_deequ_constraint("satisfies('`a` IS NOT NULL', 'nn', lambda x: x >= 0.95)")
    check = DummyCheck()
    _apply_deequ_constraint(check, spec, ConstrainableDataTypes=DummyConstrainableDataTypes)

    name, column_condition, constraint_name, assertion, hint = check.calls[0]
    assert name == "satisfies"
    assert column_condition == "`a` IS NOT NULL"
    assert constraint_name == "nn"
    assert hint is None
    assert callable(assertion)
    assert assertion(0.96) is True
    assert assertion(0.94) is False

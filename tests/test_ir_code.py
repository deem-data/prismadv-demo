from __future__ import annotations

import pytest

from prismadv.ir.deequ import (
    DeequCallSpec,
    DeequSatisfiesSpec,
    DeequLambdaAssertionSpec,
    DeequEnumValueSpec,
    parse_deequ_constraint,
)
from prismadv.ir.gx import GXExpectationSpec, parse_gx_expectation


def test_parse_deequ_simple_method_call():
    spec = parse_deequ_constraint('.isComplete("id")')
    assert isinstance(spec, DeequCallSpec)
    assert spec.method == "isComplete"
    assert spec.args == ["id"]
    assert spec.kwargs == {}
    assert spec.to_string().startswith("isComplete(")


def test_parse_deequ_satisfies_with_comparison_lambda():
    spec = parse_deequ_constraint('satisfies("`a` IS NOT NULL", "nn", lambda x: x >= 0.95)')
    assert isinstance(spec, DeequSatisfiesSpec)
    assert spec.column_condition == "`a` IS NOT NULL"
    assert spec.constraint_name == "nn"
    assert spec.assertion is not None
    assert isinstance(spec.assertion, DeequLambdaAssertionSpec)
    assert spec.assertion.clauses[0].op == ">="
    assert spec.assertion.clauses[0].value == pytest.approx(0.95)
    assert "lambda x: x >=" in spec.to_string()


def test_parse_deequ_call_with_range_lambda_assertion():
    spec = parse_deequ_constraint(".hasMean('gpa', lambda x: x >= 2.0 and x <= 3.5)")
    assert isinstance(spec, DeequCallSpec)
    assert spec.method == "hasMean"
    assert spec.args[0] == "gpa"
    assert isinstance(spec.args[1], DeequLambdaAssertionSpec)
    assert spec.args[1].combiner == "and"
    assert [c.op for c in spec.args[1].clauses] == [">=", "<="]


def test_parse_deequ_call_with_constrainable_datatype():
    spec = parse_deequ_constraint(".hasDataType('student_id', ConstrainableDataTypes.String)")
    assert isinstance(spec, DeequCallSpec)
    assert spec.method == "hasDataType"
    assert spec.args[0] == "student_id"
    assert isinstance(spec.args[1], DeequEnumValueSpec)
    assert spec.args[1].to_string() == "ConstrainableDataTypes.String"
    assert "ConstrainableDataTypes.String" in spec.to_string()


def test_parse_deequ_validates_missing_required_params():
    with pytest.raises(ValueError):
        parse_deequ_constraint(".hasCompleteness('credits_attempted')")


def test_parse_gx_expectation_accepts_class_and_method_styles():
    a = parse_gx_expectation('ExpectColumnValuesToNotBeNull(column="name")')
    b = parse_gx_expectation('expect_column_values_to_not_be_null(column="name")')
    c = parse_gx_expectation('validator.expect_column_values_to_not_be_null(column="name")')

    for spec in (a, b, c):
        assert isinstance(spec, GXExpectationSpec)
        assert spec.type == "expect_column_values_to_not_be_null"
        assert spec.kwargs["column"] == "name"
        assert spec.to_class_name() == "ExpectColumnValuesToNotBeNull"
        assert spec.to_string().startswith("ExpectColumnValuesToNotBeNull(")


def test_parse_gx_rejects_positional_args():
    with pytest.raises(ValueError):
        parse_gx_expectation("ExpectColumnValuesToNotBeNull('a')")


def test_parse_gx_validates_kwargs_against_packaged_grammar():
    with pytest.raises(ValueError):
        parse_gx_expectation('ExpectColumnValuesToNotBeNull(column="a", not_a_real_kw=1)')

    ok = parse_gx_expectation('ExpectColumnValuesToNotBeNull(column="a", mostly=0.5)')
    assert ok.kwargs["mostly"] == pytest.approx(0.5)

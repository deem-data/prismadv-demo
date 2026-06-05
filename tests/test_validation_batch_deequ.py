"""Tests for the batched Deequ validation module used by the error benchmark."""

from __future__ import annotations

import pytest

from prismadv.validation.batch_deequ import _normalise_deequ_code


# ---------------------------------------------------------------------------
# _normalise_deequ_code — pure string transformation, no Spark needed
# ---------------------------------------------------------------------------


class TestNormaliseDequCode:
    """Test the Deequ code normalisation that preprocesses LLM output."""

    def test_passthrough_simple(self):
        assert _normalise_deequ_code("isComplete('Age')") == "isComplete('Age')"

    def test_passthrough_with_assertion(self):
        code = "isNonNegative('TotalWorkingYears', lambda x: x == 1.0)"
        assert _normalise_deequ_code(code) == code

    # --- Array() → [] conversion ---

    def test_array_string_values(self):
        code = ".isContainedIn('AgeGroup', Array('18-25', '26-35', '36-45'))"
        result = _normalise_deequ_code(code)
        assert "Array" not in result
        assert "['18-25', '26-35', '36-45']" in result

    def test_array_double_quoted(self):
        code = '.isContainedIn("OverTime", Array("Yes", "No"))'
        result = _normalise_deequ_code(code)
        assert "Array" not in result
        assert '["Yes", "No"]' in result

    def test_array_with_assertion(self):
        code = ".isContainedIn('SalarySlab', Array('Upto 5k', '5k-10k'), lambda x: x == 1.0)"
        result = _normalise_deequ_code(code)
        assert "Array" not in result
        assert "['Upto 5k', '5k-10k']" in result
        assert "lambda x: x == 1.0" in result

    def test_array_numeric_values(self):
        """Array(1.0, 2.0, 3.0, 4.0) should become ['1', '2', '3', '4'] for isContainedIn."""
        code = ".isContainedIn('EnvironmentSatisfaction', Array(1.0, 2.0, 3.0, 4.0))"
        result = _normalise_deequ_code(code)
        assert "Array" not in result
        # After normalisation, these should be in a list — the exact float→string
        # conversion is handled at the parse level, but Array must be gone
        assert "[" in result and "]" in result

    # --- Hint stripping ---

    def test_strip_hint_string(self):
        code = 'isContainedIn("X", ["a", "b"], lambda x: x >= 0.93, "It should be above 0.93!")'
        result = _normalise_deequ_code(code)
        assert "It should be above" not in result
        assert result.endswith(")")

    def test_strip_hint_preserves_assertion(self):
        code = 'isContainedIn("X", ["a"], lambda x: x >= 0.91, "hint text")'
        result = _normalise_deequ_code(code)
        assert "lambda x: x >= 0.91" in result
        assert "hint text" not in result

    def test_no_hint_no_change(self):
        code = "isContainedIn('X', ['a', 'b'], lambda x: x >= 0.95)"
        assert _normalise_deequ_code(code) == code

    # --- Combined ---

    def test_array_plus_hint(self):
        code = '.isContainedIn("X", Array("a", "b"), lambda x: x >= 0.9, "my hint")'
        result = _normalise_deequ_code(code)
        assert "Array" not in result
        assert "my hint" not in result
        assert '["a", "b"]' in result
        assert "lambda x: x >= 0.9" in result


# ---------------------------------------------------------------------------
# Parsing: ensure normalised codes actually parse via the Deequ IR parser
# ---------------------------------------------------------------------------


class TestNormalisedCodeParses:
    """After normalisation, the code should parse with parse_deequ_constraint."""

    REAL_PRISMADV_CODES = [
        "hasDataType('Age', ConstrainableDataTypes.Numeric, lambda x: x == 1.0)",
        "isGreaterThanOrEqualTo('Age', 'TotalWorkingYears', lambda x: x == 1.0)",
        "satisfies('`Age` - `TotalWorkingYears` >= 15', 'career_start_age_min_15', lambda x: x == 1.0)",
        "isNonNegative('TotalWorkingYears', lambda x: x == 1.0)",
        ".isContainedIn('AgeGroup', Array('18-25', '26-35', '36-45', '46-55', '55+'))",
        "isComplete('AgeGroup')",
        ".isContainedIn('Attrition', Array('Yes', 'No'))",
        "isContainedIn('Department', ['Sales', 'Research & Development', 'Human Resources'])",
        "isUnique('EmployeeNumber')",
        "isComplete('EnvironmentSatisfaction')",
        ".isContainedIn('EnvironmentSatisfaction', Array(1.0, 2.0, 3.0, 4.0))",
        "isComplete('JobRole')",
        "hasDataType('JobSatisfaction', ConstrainableDataTypes.Numeric)",
        "isComplete('MonthlyIncome')",
        "hasDataType('MonthlyIncome', ConstrainableDataTypes.Numeric)",
        "isPositive('MonthlyIncome')",
        ".isContainedIn('SalarySlab', Array('Upto 5k', '5k-10k', '10k-15k', '15k+'), lambda x: x == 1.0)",
        '.isContainedIn("OverTime", Array("Yes", "No"))',
        "isComplete('PerformanceRating')",
        ".isContainedIn('PerformanceRating', Array(1.0, 2.0, 3.0, 4.0))",
        ".isContainedIn('SalarySlab', Array('Upto 5k', '5k-10k', '10k-15k', '15k+'))",
        "satisfies(\"SalarySlab = 'Upto 5k' => (MonthlyIncome > 0 AND MonthlyIncome <= 5000)\", 'monthly_income_upto_5k_range', lambda x: x == 1.0)",
        "isLessThanOrEqualTo('YearsAtCompany', 'TotalWorkingYears', lambda x: x == 1.0)",
        "isLessThanOrEqualTo('YearsWithCurrManager', 'YearsAtCompany')",
        "hasDataType('YearsSinceLastPromotion', ConstrainableDataTypes.Integral)",
        "isNonNegative('YearsSinceLastPromotion')",
        "hasDataType('YearsWithCurrManager', ConstrainableDataTypes.Numeric, lambda x: x == 1.0)",
        "isGreaterThanOrEqualTo('YearsAtCompany', 'YearsWithCurrManager')",
    ]

    REAL_DEEQU_CODES = [
        "isComplete('Age')",
        "isNonNegative('Age')",
        "hasMin('Age', lambda x: x >= 18)",
        "hasMax('Age', lambda x: x <= 61)",
        "isContainedIn('Department', ['Sales', 'Research & Development', 'Human Resources'])",
        "isUnique('EmployeeNumber')",
        "hasSize(lambda x: x >= 1470)",
    ]

    # Codes we expect to NOT parse (wrong API usage)
    KNOWN_BAD_CODES = [
        "isContainedIn('JobSatisfaction', 1.0, 4.0)",  # wrong: not a list
        "isContainedIn('WorkLifeBalance', 1.0, 4.0)",  # wrong: not a list
    ]

    @pytest.mark.parametrize("code", REAL_PRISMADV_CODES, ids=lambda c: c[:50])
    def test_prismadv_code_parses(self, code: str):
        from prismadv.ir.deequ import parse_deequ_constraint
        normalised = _normalise_deequ_code(code)
        spec = parse_deequ_constraint(normalised)
        assert spec is not None

    @pytest.mark.parametrize("code", REAL_DEEQU_CODES, ids=lambda c: c[:50])
    def test_deequ_suggestion_parses(self, code: str):
        from prismadv.ir.deequ import parse_deequ_constraint
        normalised = _normalise_deequ_code(code)
        spec = parse_deequ_constraint(normalised)
        assert spec is not None

    @pytest.mark.parametrize("code", KNOWN_BAD_CODES, ids=lambda c: c[:50])
    def test_known_bad_code_handled(self, code: str):
        """Known bad codes should either parse or raise — not crash."""
        from prismadv.ir.deequ import parse_deequ_constraint
        normalised = _normalise_deequ_code(code)
        try:
            parse_deequ_constraint(normalised)
        except (ValueError, TypeError):
            pass  # expected — these are legitimately broken


# ---------------------------------------------------------------------------
# validate_constraints_batch — needs Spark
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def spark_session():
    """Create a Spark session for Deequ tests, skip if unavailable."""
    try:
        import pyspark  # type: ignore
        import os
        os.environ.setdefault("SPARK_VERSION", ".".join(str(pyspark.__version__).split(".")[:2]))
        import pydeequ  # noqa: F401
        from pyspark.sql import SparkSession  # type: ignore
    except Exception as e:
        pytest.skip(f"Spark/PyDeequ not available: {e}")

    spark = (
        SparkSession.builder.appName("test-batch-deequ")
        .master("local[1]")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.jars.packages", pydeequ.deequ_maven_coord)
        .config("spark.jars.excludes", pydeequ.f2j_maven_coord)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    yield spark


@pytest.fixture
def toy_spark_df(spark_session, tmp_path):
    """A small Spark DataFrame for testing."""
    csv = tmp_path / "toy.csv"
    csv.write_text("name,age,dept\nAlice,30,Sales\nBob,,HR\nCharlie,25,Sales\n")
    return spark_session.read.option("header", "true").option("inferSchema", "true").csv(str(csv))


class TestValidateConstraintsBatch:
    def test_empty_input(self, spark_session, toy_spark_df):
        from prismadv.validation.batch_deequ import validate_constraints_batch
        result = validate_constraints_batch(toy_spark_df, [], spark_session)
        assert result == {}

    def test_passing_constraint(self, spark_session, toy_spark_df):
        from prismadv.validation.batch_deequ import validate_constraints_batch
        # "name" is complete — should PASS (False = no violation)
        result = validate_constraints_batch(
            toy_spark_df,
            [("c1", "isComplete('name')")],
            spark_session,
        )
        assert result["c1"] is False

    def test_failing_constraint(self, spark_session, toy_spark_df):
        from prismadv.validation.batch_deequ import validate_constraints_batch
        # "age" has a null — should FAIL (True = violation detected)
        result = validate_constraints_batch(
            toy_spark_df,
            [("c1", "isComplete('age')")],
            spark_session,
        )
        assert result["c1"] is True

    def test_unparseable_returns_none(self, spark_session, toy_spark_df):
        from prismadv.validation.batch_deequ import validate_constraints_batch
        result = validate_constraints_batch(
            toy_spark_df,
            [("bad", "totallyBogusMethod('x')")],
            spark_session,
        )
        # Should be None (error), not False (passed)
        assert result["bad"] is None

    def test_empty_code_returns_none(self, spark_session, toy_spark_df):
        from prismadv.validation.batch_deequ import validate_constraints_batch
        result = validate_constraints_batch(
            toy_spark_df,
            [("empty", "")],
            spark_session,
        )
        assert result["empty"] is None

    def test_mixed_pass_fail_error(self, spark_session, toy_spark_df):
        from prismadv.validation.batch_deequ import validate_constraints_batch
        result = validate_constraints_batch(
            toy_spark_df,
            [
                ("pass", "isComplete('name')"),
                ("fail", "isComplete('age')"),
                ("err", "bogusMethod('x')"),
            ],
            spark_session,
        )
        assert result["pass"] is False
        assert result["fail"] is True
        assert result["err"] is None

    def test_array_normalisation_works(self, spark_session, toy_spark_df):
        from prismadv.validation.batch_deequ import validate_constraints_batch
        # Uses Array() syntax — should be normalised and work
        result = validate_constraints_batch(
            toy_spark_df,
            [("c1", ".isContainedIn('dept', Array('Sales', 'HR'))")],
            spark_session,
        )
        # All dept values are in the set → should pass
        assert result["c1"] is False

    def test_contained_in_violation(self, spark_session, toy_spark_df):
        from prismadv.validation.batch_deequ import validate_constraints_batch
        # "Sales" not in allowed set → should fail
        result = validate_constraints_batch(
            toy_spark_df,
            [("c1", "isContainedIn('dept', ['HR', 'Eng'])")],
            spark_session,
        )
        assert result["c1"] is True

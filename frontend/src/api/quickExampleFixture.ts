/**
 * Auto-generated fixture from real pipeline run.
 * EIDBench: hr_analytics / general_task_1.py
 */
import type { GenerationResult } from "@/types";

export const QUICK_EXAMPLE_DATASET = "hr_analytics";
export const QUICK_EXAMPLE_SCRIPT = "general_task_1.py";

export const quickExampleResult: GenerationResult = {
  "constraints": [
    {
      "id": "constraint-6eca18a3",
      "column": "Age",
      "type": "format",
      "columnType": "textual",
      "label": "Age (format)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_in_type_list(column='Age', type_list=['int', 'float'])",
        "deequ": "hasDataType('Age', ConstrainableDataTypes.Numeric, lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "The 'Age' column is expected to contain numeric values, as it is used in arithmetic operations like subtraction to calculate 'career_start_age'.",
        "sourceCodeLines": [
          82
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-5f82a6b8",
      "dataStats": {}
    },
    {
      "id": "constraint-dc4d03d6",
      "column": "Age",
      "type": "relationship",
      "columnType": "textual",
      "label": "Age (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_pair_values_a_to_be_greater_than_b(column_A='Age', column_B='TotalWorkingYears', or_equal=True, mostly=1.0)",
        "deequ": "isGreaterThanOrEqualTo('Age', 'TotalWorkingYears', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "The 'Age' column is assumed to be greater than or equal to 'TotalWorkingYears' to ensure that the calculated 'career_start_age' (Age - TotalWorkingYears) is a non-negative and logically sound value, representing a person's age when they started their career.",
        "sourceCodeLines": [
          82
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-6c17dea0",
      "dataStats": {}
    },
    {
      "id": "constraint-1ff1b2f9",
      "column": "TotalWorkingYears",
      "type": "relationship",
      "columnType": "textual",
      "label": "TotalWorkingYears (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_pair_values_a_to_be_greater_than_b(column_A='Age', column_B='TotalWorkingYears', or_equal=True, mostly=1.0)",
        "deequ": "isGreaterThanOrEqualTo('Age', 'TotalWorkingYears', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "The 'Age' column is assumed to be greater than or equal to 'TotalWorkingYears' to ensure that the calculated 'career_start_age' (Age - TotalWorkingYears) is a non-negative and logically sound value, representing a person's age when they started their career.",
        "sourceCodeLines": [
          82
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-6c17dea0",
      "dataStats": {}
    },
    {
      "id": "constraint-902f8fa2",
      "column": "Age",
      "type": "range",
      "columnType": "textual",
      "label": "Age (range)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_pair_values_a_to_be_greater_than_b(column_A='Age', column_B='TotalWorkingYears', or_equal=True)",
        "deequ": "satisfies('`Age` - `TotalWorkingYears` >= 15', 'career_start_age_min_15', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "The derived 'career_start_age' (Age - TotalWorkingYears) is implicitly expected to be at least 15. Although the code clips `(career_start_age - 15)` to a lower bound of 0, this baseline subtraction suggests an implicit understanding of 15 as a minimum reasonable age for starting a career.",
        "sourceCodeLines": [
          82,
          88
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-22591095",
      "dataStats": {}
    },
    {
      "id": "constraint-987f5680",
      "column": "TotalWorkingYears",
      "type": "range",
      "columnType": "textual",
      "label": "TotalWorkingYears (range)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_between(column='TotalWorkingYears', min_value=0)",
        "deequ": "isNonNegative('TotalWorkingYears', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "The derived 'career_start_age' (Age - TotalWorkingYears) is implicitly expected to be at least 15. Although the code clips `(career_start_age - 15)` to a lower bound of 0, this baseline subtraction suggests an implicit understanding of 15 as a minimum reasonable age for starting a career.",
        "sourceCodeLines": [
          82,
          88
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-22591095",
      "dataStats": {}
    },
    {
      "id": "constraint-e2fc4f41",
      "column": "AgeGroup",
      "type": "enum",
      "columnType": "textual",
      "label": "AgeGroup (enum)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_in_set(column='AgeGroup', value_set=['18-25', '26-35', '36-45', '46-55', '55+'])",
        "deequ": ".isContainedIn('AgeGroup', Array('18-25', '26-35', '36-45', '46-55', '55+'))"
      },
      "assumption": {
        "text": "The 'AgeGroup' column is expected to contain values that are present in the predefined set of allowed age groups. Values not in `{\"18-25\", \"26-35\", \"36-45\", \"46-55\", \"55+\"}` will not be mapped correctly and will result in NaN, which will propagate to the `risk_score`.",
        "sourceCodeLines": [
          64,
          71,
          132,
          133,
          134,
          135,
          136,
          137,
          138,
          139
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-83ca81b2",
      "dataStats": {}
    },
    {
      "id": "constraint-1f6bbc57",
      "column": "AgeGroup",
      "type": "completeness",
      "columnType": "textual",
      "label": "AgeGroup (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_not_be_null(column='AgeGroup')",
        "deequ": "isComplete('AgeGroup')"
      },
      "assumption": {
        "text": "The 'AgeGroup' column is assumed to be complete and not contain any null or missing values. If null values are present, the `.map()` operation (line 139) will produce NaN, which will propagate through `age_w` to the `risk_score` calculation, potentially resulting in NaN risk scores for those rows.",
        "sourceCodeLines": [
          139,
          166
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-0d2bca48",
      "dataStats": {}
    },
    {
      "id": "constraint-f5517f3e",
      "column": "Attrition",
      "type": "enum",
      "columnType": "textual",
      "label": "Attrition (enum)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_in_set(column='Attrition', value_set=['Yes', 'No'])",
        "deequ": ".isContainedIn('Attrition', Array('Yes', 'No'))"
      },
      "assumption": {
        "text": "The 'Attrition' column is expected to contain 'Yes' for positive attrition cases. Any other value in this column is implicitly treated as indicating no attrition (e.g., 'No', or other string values would map to 0).",
        "sourceCodeLines": [
          103
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-2e93e36e",
      "dataStats": {}
    },
    {
      "id": "constraint-81a61207",
      "column": "Attrition",
      "type": "completeness",
      "columnType": "textual",
      "label": "Attrition (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_in_set(column='Attrition', value_set=['Yes', 'No', None])",
        "deequ": ".isContainedIn('Attrition', Array('Yes', 'No'))"
      },
      "assumption": {
        "text": "The code implicitly assumes that `NaN` (missing) values in the 'Attrition' column are acceptable and should be treated as indicating no attrition. If `Attrition` is `NaN`, it is mapped to 0 (equivalent to 'No') for all subsequent calculations.",
        "sourceCodeLines": [
          103
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-22b1b7e1",
      "dataStats": {}
    },
    {
      "id": "constraint-b18ecb47",
      "column": "Department",
      "type": "enum",
      "columnType": "textual",
      "label": "Department (enum)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_in_set(column='Department', value_set=['Sales', 'Research & Development', 'Human Resources'])",
        "deequ": "isContainedIn('Department', ['Sales', 'Research & Development', 'Human Resources'])"
      },
      "assumption": {
        "text": "The 'Department' column is assumed to contain values exclusively from a predefined set: 'Sales', 'Research & Development', and 'Human Resources'. This is explicitly stated in the `dept_allowed` set and is reinforced by the `map` operation which assigns specific weights only to these departments.",
        "sourceCodeLines": [
          50,
          59,
          142,
          143,
          144,
          145,
          146
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-5ee2ee04",
      "dataStats": {}
    },
    {
      "id": "constraint-c39b0f73",
      "column": "Department",
      "type": "completeness",
      "columnType": "textual",
      "label": "Department (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_not_be_null(column='Department')",
        "deequ": "isComplete('Department')"
      },
      "assumption": {
        "text": "The 'Department' column is assumed to be complete, meaning it should not contain any null or missing values. Operations like equality checks and mapping are performed directly on the column without any explicit handling (e.g., `fillna`, `dropna`) for missing data. If nulls were present, they would lead to unexpected behavior or propagate `NaN` values into subsequent calculations like `dept_weight` and `linear_score`.",
        "sourceCodeLines": [
          59,
          142,
          143,
          144,
          145,
          146
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-3ed8219b",
      "dataStats": {}
    },
    {
      "id": "constraint-fd345361",
      "column": "EmployeeNumber",
      "type": "uniqueness",
      "columnType": "textual",
      "label": "EmployeeNumber (uniqueness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_unique(column='EmployeeNumber')",
        "deequ": "isUnique('EmployeeNumber')"
      },
      "assumption": {
        "text": "The `EmployeeNumber` column is expected to contain unique values, as it is included alongside `EmpID` in the output dataframe `risk_out`, implying it acts as an identifier for individual employees.",
        "sourceCodeLines": [
          170,
          171
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-cccdafab",
      "dataStats": {}
    },
    {
      "id": "constraint-a508a485",
      "column": "EnvironmentSatisfaction",
      "type": "completeness",
      "columnType": "textual",
      "label": "EnvironmentSatisfaction (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_not_be_null(column='EnvironmentSatisfaction')",
        "deequ": "isComplete('EnvironmentSatisfaction')"
      },
      "assumption": {
        "text": "The 'EnvironmentSatisfaction' column is expected to contain non-null numeric values. The calculation of `sat_mean` using `.mean(axis=1)` implies that missing values would either lead to NaNs propagating or be implicitly ignored by pandas' default behavior, which might not be the desired outcome if all values are expected to be present.",
        "sourceCodeLines": [
          117,
          118
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-7fc0d8da",
      "dataStats": {}
    },
    {
      "id": "constraint-161ff4ee",
      "column": "EnvironmentSatisfaction",
      "type": "range",
      "columnType": "textual",
      "label": "EnvironmentSatisfaction (range)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_between(column='EnvironmentSatisfaction', min_value=1, max_value=4)",
        "deequ": ".isContainedIn('EnvironmentSatisfaction', Array(1.0, 2.0, 3.0, 4.0))"
      },
      "assumption": {
        "text": "The 'EnvironmentSatisfaction' column is expected to contain numeric values, specifically integers, within the range of 1 to 4, inclusive. This is inferred from the formula `1.0 - (sat_mean - 1.0) / 3.0`, where `sat_mean` is the average of satisfaction columns. This specific normalization formula is designed to map input values from a 1-4 scale to a 0-1 dissatisfaction score. Values outside this range would produce `dissat` scores outside 0-1, which are then clipped, implying an underlying expectation for the source values.",
        "sourceCodeLines": [
          117,
          118,
          119,
          121
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-1747c2a1",
      "dataStats": {}
    },
    {
      "id": "constraint-035ad0b9",
      "column": "JobRole",
      "type": "completeness",
      "columnType": "textual",
      "label": "JobRole (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_to_exist(column='JobRole')",
        "deequ": "isComplete('JobRole')"
      },
      "assumption": {
        "text": "The code accesses the 'JobRole' column to include it in the 'attrition_risk_scores.csv' output. This implicitly assumes that the 'JobRole' column exists in the input DataFrame.",
        "sourceCodeLines": [
          170,
          171
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-7642690e",
      "dataStats": {}
    },
    {
      "id": "constraint-2856d65e",
      "column": "JobSatisfaction",
      "type": "format",
      "columnType": "textual",
      "label": "JobSatisfaction (format)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_in_type_list(column='JobSatisfaction', type_list=['int', 'float'])",
        "deequ": "hasDataType('JobSatisfaction', ConstrainableDataTypes.Numeric)"
      },
      "assumption": {
        "text": "The 'JobSatisfaction' column is implicitly assumed to contain numerical values that can be averaged and used in arithmetic calculations.",
        "sourceCodeLines": [
          117,
          118,
          119
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-aa65f974",
      "dataStats": {}
    },
    {
      "id": "constraint-e4c25999",
      "column": "JobSatisfaction",
      "type": "range",
      "columnType": "textual",
      "label": "JobSatisfaction (range)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_between(column='JobSatisfaction', min_value=1, max_value=4)",
        "deequ": "isContainedIn('JobSatisfaction', 1.0, 4.0)"
      },
      "assumption": {
        "text": "The 'JobSatisfaction' column is implicitly assumed to contain values within the range of 1 to 4. This is inferred from the normalization formula `(sat_mean - 1.0) / 3.0` which is typically used to scale values from a [1, 4] range to a [0, 1] range. Values outside this range would lead to 'dissat' being outside [0, 1] before explicit clipping.",
        "sourceCodeLines": [
          117,
          118,
          119
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-789201bb",
      "dataStats": {}
    },
    {
      "id": "constraint-24db5bbd",
      "column": "JobSatisfaction",
      "type": "completeness",
      "columnType": "textual",
      "label": "JobSatisfaction (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_not_be_null(column='JobSatisfaction')",
        "deequ": "isComplete('JobSatisfaction')"
      },
      "assumption": {
        "text": "The 'JobSatisfaction' column is assumed to be complete (non-null) for all records where an 'attrition_risk_score' is expected. Although `mean()` handles NaNs by default by skipping them, if 'JobSatisfaction' (or other satisfaction columns in a row) were entirely null, `sat_mean` would become NaN, propagating NaNs through 'dissat' to the final `risk_score` in the output.",
        "sourceCodeLines": [
          117,
          118,
          119
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-4a430678",
      "dataStats": {}
    },
    {
      "id": "constraint-a213a99a",
      "column": "MonthlyIncome",
      "type": "completeness",
      "columnType": "textual",
      "label": "MonthlyIncome (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_not_be_null(column='MonthlyIncome')",
        "deequ": "isComplete('MonthlyIncome')"
      },
      "assumption": {
        "text": "The `MonthlyIncome` column is expected to contain numerical values and not have null/missing entries. This is implied by its use in direct numerical comparisons (`>`, `<=`) and aggregate calculations (`median`, `min`, `max`). The presence of non-numeric data would lead to errors, while null values could propagate through calculations (e.g., `row_ok` would evaluate to False or NaN) or result in unexpected behavior in aggregations (e.g., `median` ignoring NaNs, but if a group is all NaNs, returning NaN, which would then affect `progression_logs`).",
        "sourceCodeLines": [
          29,
          32,
          33,
          34,
          35,
          41,
          185,
          186,
          187
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-068e7022",
      "dataStats": {}
    },
    {
      "id": "constraint-e635f4f8",
      "column": "MonthlyIncome",
      "type": "completeness",
      "columnType": "textual",
      "label": "MonthlyIncome (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_of_type(column='MonthlyIncome', type_='float')",
        "deequ": "hasDataType('MonthlyIncome', ConstrainableDataTypes.Numeric)"
      },
      "assumption": {
        "text": "The `MonthlyIncome` column is expected to contain numerical values and not have null/missing entries. This is implied by its use in direct numerical comparisons (`>`, `<=`) and aggregate calculations (`median`, `min`, `max`). The presence of non-numeric data would lead to errors, while null values could propagate through calculations (e.g., `row_ok` would evaluate to False or NaN) or result in unexpected behavior in aggregations (e.g., `median` ignoring NaNs, but if a group is all NaNs, returning NaN, which would then affect `progression_logs`).",
        "sourceCodeLines": [
          29,
          32,
          33,
          34,
          35,
          41,
          185,
          186,
          187
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-068e7022",
      "dataStats": {}
    },
    {
      "id": "constraint-855e308e",
      "column": "MonthlyIncome",
      "type": "range",
      "columnType": "textual",
      "label": "MonthlyIncome (range)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_between(column='MonthlyIncome', min_value=0, strict_min=True)",
        "deequ": "isPositive('MonthlyIncome')"
      },
      "assumption": {
        "text": "Values in the `MonthlyIncome` column are expected to be strictly positive (greater than zero). This is explicitly enforced for the 'Upto 5k' salary slab and is generally implied for all slabs, as income is typically a positive quantity.",
        "sourceCodeLines": [
          32
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-74003ac4",
      "dataStats": {}
    },
    {
      "id": "constraint-cce37835",
      "column": "SalarySlab",
      "type": "statistical",
      "columnType": "textual",
      "label": "SalarySlab (statistical)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_distinct_values_to_equal_set(column='SalarySlab', value_set=['Upto 5k', '5k-10k', '10k-15k', '15k+'])",
        "deequ": ".isContainedIn('SalarySlab', Array('Upto 5k', '5k-10k', '10k-15k', '15k+'), lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "The median `MonthlyIncome` values, when grouped by `SalarySlab` and ordered according to the `allowed_slabs` categories, are expected to show a positive and generally increasing progression. The calculation of `progression_logs` as the natural logarithm of the ratio of successive median incomes implies an expectation that median income increases with each higher salary slab.",
        "sourceCodeLines": [
          41,
          42,
          46
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-66729341",
      "dataStats": {}
    },
    {
      "id": "constraint-47914be6",
      "column": "MonthlyIncome",
      "type": "statistical",
      "columnType": "textual",
      "label": "MonthlyIncome (statistical)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_between(column='MonthlyIncome', min_value=1, strict_min=True, mostly=1.0)",
        "deequ": "isPositive('MonthlyIncome', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "The median `MonthlyIncome` values, when grouped by `SalarySlab` and ordered according to the `allowed_slabs` categories, are expected to show a positive and generally increasing progression. The calculation of `progression_logs` as the natural logarithm of the ratio of successive median incomes implies an expectation that median income increases with each higher salary slab.",
        "sourceCodeLines": [
          41,
          42,
          46
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-66729341",
      "dataStats": {}
    },
    {
      "id": "constraint-a13a8857",
      "column": "OverTime",
      "type": "enum",
      "columnType": "textual",
      "label": "OverTime (enum)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_in_set(column='OverTime', value_set=['Yes', 'No'])",
        "deequ": ".isContainedIn(\"OverTime\", Array(\"Yes\", \"No\"))"
      },
      "assumption": {
        "text": "The `OverTime` column is expected to contain only the categorical values \"Yes\" or \"No\". Any other value, including nulls (NaN), would implicitly be treated as \"No\" for the purpose of calculations and categorizations within the script.",
        "sourceCodeLines": [
          104,
          109,
          110,
          113,
          159,
          170,
          202,
          203
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-6a3e0e00",
      "dataStats": {}
    },
    {
      "id": "constraint-1021d1bd",
      "column": "PercentSalaryHike",
      "type": "completeness",
      "columnType": "textual",
      "label": "PercentSalaryHike (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_not_be_null(column='PercentSalaryHike')",
        "deequ": "isComplete('PercentSalaryHike')"
      },
      "assumption": {
        "text": "The 'PercentSalaryHike' column is assumed to contain no missing (null) values. The code directly performs arithmetic operations (subtraction and division) on the column without any explicit null handling (e.g., `fillna()`, `dropna()`). If nulls were present, these operations would result in `NaN`s, which would propagate to `comp_change_norm` and potentially lead to errors or unexpected behavior in downstream calculations.",
        "sourceCodeLines": [
          97
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-c33036f8",
      "dataStats": {}
    },
    {
      "id": "constraint-f82ed2ea",
      "column": "PercentSalaryHike",
      "type": "format",
      "columnType": "textual",
      "label": "PercentSalaryHike (format)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_of_type(column='PercentSalaryHike', type_='float')",
        "deequ": "hasDataType('PercentSalaryHike', ConstrainableDataTypes.Numeric)"
      },
      "assumption": {
        "text": "The 'PercentSalaryHike' column is assumed to be of a numerical data type (e.g., integer or float). The code performs arithmetic operations (subtraction from a scalar, division by a scalar) on the column, which would raise a TypeError if the column contained non-numeric values (e.g., strings, booleans).",
        "sourceCodeLines": [
          97
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-7f8675f7",
      "dataStats": {}
    },
    {
      "id": "constraint-90eaf62b",
      "column": "PercentSalaryHike",
      "type": "range",
      "columnType": "textual",
      "label": "PercentSalaryHike (range)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_between(column='PercentSalaryHike', min_value=0, max_value=25, strict_max=True, mostly=1.0)",
        "deequ": "isNonNegative('PercentSalaryHike')"
      },
      "assumption": {
        "text": "The 'PercentSalaryHike' column is expected to represent a non-negative percentage increase, likely between 0 and less than 25. The term 'Hike' semantically implies a non-negative value. The calculation `(25 - df[\"PercentSalaryHike\"]) / 14.0` followed by clipping `np.clip(comp_change_norm, 0.0, 2.0)` implies that values of 25 or higher for `PercentSalaryHike` result in `comp_change_norm` being 0.0, and values lower than approximately -3 result in `comp_change_norm` being 2.0. This suggests that for `comp_change_norm` to reflect meaningful variation, `PercentSalaryHike` is expected to be primarily within the range of 0 to 25 (exclusive of 25 for non-zero `comp_change_norm`).",
        "sourceCodeLines": [
          97
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-196570f9",
      "dataStats": {}
    },
    {
      "id": "constraint-aea4bb4d",
      "column": "PerformanceRating",
      "type": "completeness",
      "columnType": "textual",
      "label": "PerformanceRating (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_not_be_null(column='PerformanceRating')",
        "deequ": "isComplete('PerformanceRating')"
      },
      "assumption": {
        "text": "The code assumes that the `PerformanceRating` column does not contain missing (null) values, as it directly accesses and compares values without explicit null-checking or handling. If nulls were present, they would implicitly be treated as \"not 4\".",
        "sourceCodeLines": [
          96
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-8af3d172",
      "dataStats": {}
    },
    {
      "id": "constraint-af0d4fa7",
      "column": "PerformanceRating",
      "type": "enum",
      "columnType": "textual",
      "label": "PerformanceRating (enum)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_not_be_null(column='PerformanceRating')",
        "deequ": "isComplete('PerformanceRating')"
      },
      "assumption": {
        "text": "The code explicitly checks if `PerformanceRating` is equal to `4`. This implies that `PerformanceRating` is expected to be a categorical or enumerated value, with `4` being one of the valid and specifically recognized states. Any other value (including other valid ratings, or unexpected data) is grouped as \"not 4\".",
        "sourceCodeLines": [
          96
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-0e356a3f",
      "dataStats": {}
    },
    {
      "id": "constraint-1a80ff4d",
      "column": "PerformanceRating",
      "type": "enum",
      "columnType": "textual",
      "label": "PerformanceRating (enum)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_in_set(column='PerformanceRating', value_set=[1, 2, 3, 4])",
        "deequ": ".isContainedIn('PerformanceRating', Array(1.0, 2.0, 3.0, 4.0))"
      },
      "assumption": {
        "text": "The code explicitly checks if `PerformanceRating` is equal to `4`. This implies that `PerformanceRating` is expected to be a categorical or enumerated value, with `4` being one of the valid and specifically recognized states. Any other value (including other valid ratings, or unexpected data) is grouped as \"not 4\".",
        "sourceCodeLines": [
          96
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-0e356a3f",
      "dataStats": {}
    },
    {
      "id": "constraint-8e45b0a2",
      "column": "SalarySlab",
      "type": "completeness",
      "columnType": "textual",
      "label": "SalarySlab (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_not_be_null(column='SalarySlab')",
        "deequ": "isComplete('SalarySlab')"
      },
      "assumption": {
        "text": "The `SalarySlab` column is implicitly assumed to not contain any null or missing values. The code directly accesses and uses the column for filtering, categorical conversion, and grouping operations without explicit null handling, indicating an expectation for its presence in all rows for consistent processing.",
        "sourceCodeLines": [
          30,
          32,
          33,
          34,
          35,
          40,
          41,
          182
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-a87b0cef",
      "dataStats": {}
    },
    {
      "id": "constraint-304ce5d0",
      "column": "SalarySlab",
      "type": "enum",
      "columnType": "textual",
      "label": "SalarySlab (enum)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_in_set(column='SalarySlab', value_set=['Upto 5k', '5k-10k', '10k-15k', '15k+'])",
        "deequ": ".isContainedIn('SalarySlab', Array('Upto 5k', '5k-10k', '10k-15k', '15k+'))"
      },
      "assumption": {
        "text": "The `SalarySlab` column is expected to contain only a specific, ordered set of categorical values: \"Upto 5k\", \"5k-10k\", \"10k-15k\", \"15k+\". The code explicitly defines these allowed categories and converts the column to an ordered categorical type, asserting its enum and ordinal nature.",
        "sourceCodeLines": [
          25,
          32,
          33,
          34,
          35,
          40,
          41,
          182
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-cc52c5a4",
      "dataStats": {}
    },
    {
      "id": "constraint-e8b00bc3",
      "column": "SalarySlab",
      "type": "relationship",
      "columnType": "textual",
      "label": "SalarySlab (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_in_set(column='SalarySlab', value_set=['Upto 5k', '5k-10k', '10k-15k', '15k+'], mostly=1.0)",
        "deequ": ".isContainedIn('SalarySlab', Array('Upto 5k', '5k-10k', '10k-15k', '15k+'), lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "There is a strict relationship between the `SalarySlab` column and the `MonthlyIncome` column, where each `SalarySlab` value corresponds to a specific range for `MonthlyIncome`. Specifically:\n- If `SalarySlab` is \"Upto 5k\", `MonthlyIncome` must be greater than 0 and less than or equal to 5000.\n- If `SalarySlab` is \"5k-10k\", `MonthlyIncome` must be greater than 5000 and less than or equal to 10000.\n- If `SalarySlab` is \"10k-15k\", `MonthlyIncome` must be greater than 10000 and less than or equal to 15000.\n- If `SalarySlab` is \"15k+\", `MonthlyIncome` must be greater than 15000.",
        "sourceCodeLines": [
          32,
          33,
          34,
          35
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-898b4780",
      "dataStats": {}
    },
    {
      "id": "constraint-35fa7e8a",
      "column": "MonthlyIncome",
      "type": "relationship",
      "columnType": "textual",
      "label": "MonthlyIncome (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_between(column='MonthlyIncome', min_value=0.0, max_value=5000.0, strict_min=True, mostly=1.0, row_condition=\"SalarySlab == 'Upto 5k'\")",
        "deequ": "satisfies(\"SalarySlab = 'Upto 5k' => (MonthlyIncome > 0 AND MonthlyIncome <= 5000)\", 'monthly_income_upto_5k_range', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "There is a strict relationship between the `SalarySlab` column and the `MonthlyIncome` column, where each `SalarySlab` value corresponds to a specific range for `MonthlyIncome`. Specifically:\n- If `SalarySlab` is \"Upto 5k\", `MonthlyIncome` must be greater than 0 and less than or equal to 5000.\n- If `SalarySlab` is \"5k-10k\", `MonthlyIncome` must be greater than 5000 and less than or equal to 10000.\n- If `SalarySlab` is \"10k-15k\", `MonthlyIncome` must be greater than 10000 and less than or equal to 15000.\n- If `SalarySlab` is \"15k+\", `MonthlyIncome` must be greater than 15000.",
        "sourceCodeLines": [
          32,
          33,
          34,
          35
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-898b4780",
      "dataStats": {}
    },
    {
      "id": "constraint-4e3e34db",
      "column": "MonthlyIncome",
      "type": "relationship",
      "columnType": "textual",
      "label": "MonthlyIncome (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_between(column='MonthlyIncome', min_value=5000.0, max_value=10000.0, strict_min=True, mostly=1.0, row_condition=\"SalarySlab == '5k-10k'\")",
        "deequ": "satisfies(\"SalarySlab = '5k-10k' => (MonthlyIncome > 5000 AND MonthlyIncome <= 10000)\", 'monthly_income_5k_10k_range', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "There is a strict relationship between the `SalarySlab` column and the `MonthlyIncome` column, where each `SalarySlab` value corresponds to a specific range for `MonthlyIncome`. Specifically:\n- If `SalarySlab` is \"Upto 5k\", `MonthlyIncome` must be greater than 0 and less than or equal to 5000.\n- If `SalarySlab` is \"5k-10k\", `MonthlyIncome` must be greater than 5000 and less than or equal to 10000.\n- If `SalarySlab` is \"10k-15k\", `MonthlyIncome` must be greater than 10000 and less than or equal to 15000.\n- If `SalarySlab` is \"15k+\", `MonthlyIncome` must be greater than 15000.",
        "sourceCodeLines": [
          32,
          33,
          34,
          35
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-898b4780",
      "dataStats": {}
    },
    {
      "id": "constraint-d9f98846",
      "column": "MonthlyIncome",
      "type": "relationship",
      "columnType": "textual",
      "label": "MonthlyIncome (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_between(column='MonthlyIncome', min_value=10000.0, max_value=15000.0, strict_min=True, mostly=1.0, row_condition=\"SalarySlab == '10k-15k'\")",
        "deequ": "satisfies(\"SalarySlab = '10k-15k' => (MonthlyIncome > 10000 AND MonthlyIncome <= 15000)\", 'monthly_income_10k_15k_range', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "There is a strict relationship between the `SalarySlab` column and the `MonthlyIncome` column, where each `SalarySlab` value corresponds to a specific range for `MonthlyIncome`. Specifically:\n- If `SalarySlab` is \"Upto 5k\", `MonthlyIncome` must be greater than 0 and less than or equal to 5000.\n- If `SalarySlab` is \"5k-10k\", `MonthlyIncome` must be greater than 5000 and less than or equal to 10000.\n- If `SalarySlab` is \"10k-15k\", `MonthlyIncome` must be greater than 10000 and less than or equal to 15000.\n- If `SalarySlab` is \"15k+\", `MonthlyIncome` must be greater than 15000.",
        "sourceCodeLines": [
          32,
          33,
          34,
          35
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-898b4780",
      "dataStats": {}
    },
    {
      "id": "constraint-aed396fc",
      "column": "MonthlyIncome",
      "type": "relationship",
      "columnType": "textual",
      "label": "MonthlyIncome (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_between(column='MonthlyIncome', min_value=15000.0, max_value=None, strict_min=True, mostly=1.0, row_condition=\"SalarySlab == '15k+'\")",
        "deequ": "satisfies(\"SalarySlab = '15k+' => (MonthlyIncome > 15000)\", 'monthly_income_15k_plus_range', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "There is a strict relationship between the `SalarySlab` column and the `MonthlyIncome` column, where each `SalarySlab` value corresponds to a specific range for `MonthlyIncome`. Specifically:\n- If `SalarySlab` is \"Upto 5k\", `MonthlyIncome` must be greater than 0 and less than or equal to 5000.\n- If `SalarySlab` is \"5k-10k\", `MonthlyIncome` must be greater than 5000 and less than or equal to 10000.\n- If `SalarySlab` is \"10k-15k\", `MonthlyIncome` must be greater than 10000 and less than or equal to 15000.\n- If `SalarySlab` is \"15k+\", `MonthlyIncome` must be greater than 15000.",
        "sourceCodeLines": [
          32,
          33,
          34,
          35
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-898b4780",
      "dataStats": {}
    },
    {
      "id": "constraint-ad8c4ddc",
      "column": "TotalWorkingYears",
      "type": "relationship",
      "columnType": "textual",
      "label": "TotalWorkingYears (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_pair_values_a_to_be_greater_than_b(column_A='TotalWorkingYears', column_B='YearsAtCompany', or_equal=True, mostly=1.0)",
        "deequ": "isGreaterThanOrEqualTo('TotalWorkingYears', 'YearsAtCompany', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "The `external_experience` calculation assumes that an employee's `TotalWorkingYears` are greater than or equal to the `YearsAtCompany`. If `TotalWorkingYears` were less than `YearsAtCompany`, it would imply working at the current company longer than total career, which is illogical. The result of this subtraction is clipped to `lower=0`, effectively validating that the difference should not be negative.",
        "sourceCodeLines": [
          81
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-c787b1f8",
      "dataStats": {}
    },
    {
      "id": "constraint-32997b21",
      "column": "YearsAtCompany",
      "type": "relationship",
      "columnType": "textual",
      "label": "YearsAtCompany (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_pair_values_a_to_be_greater_than_b(column_A='TotalWorkingYears', column_B='YearsAtCompany', or_equal=True, mostly=1.0)",
        "deequ": "isGreaterThanOrEqualTo('TotalWorkingYears', 'YearsAtCompany', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "The `external_experience` calculation assumes that an employee's `TotalWorkingYears` are greater than or equal to the `YearsAtCompany`. If `TotalWorkingYears` were less than `YearsAtCompany`, it would imply working at the current company longer than total career, which is illogical. The result of this subtraction is clipped to `lower=0`, effectively validating that the difference should not be negative.",
        "sourceCodeLines": [
          81
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-c787b1f8",
      "dataStats": {}
    },
    {
      "id": "constraint-bbabdd8f",
      "column": "Age",
      "type": "relationship",
      "columnType": "textual",
      "label": "Age (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_pair_values_a_to_be_greater_than_b(column_A='Age', column_B='TotalWorkingYears', mostly=1.0)",
        "deequ": "satisfies('`Age` - `TotalWorkingYears` >= 15', 'career_start_age_at_least_15', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "The `career_start_age` calculation (`Age - TotalWorkingYears`) implicitly assumes that `Age` is sufficiently greater than `TotalWorkingYears` to yield a positive and realistic 'career start age'. Furthermore, the `career_start_signal` calculation in line 88 (`(career_start_age - 15).clip(lower=0)`) explicitly implies that the calculated `career_start_age` (i.e., `Age - TotalWorkingYears`) should be at least 15, representing a plausible minimum age for starting a career.",
        "sourceCodeLines": [
          82,
          88,
          161
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-6454c9db",
      "dataStats": {}
    },
    {
      "id": "constraint-5ae07326",
      "column": "TotalWorkingYears",
      "type": "relationship",
      "columnType": "textual",
      "label": "TotalWorkingYears (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_pair_values_a_to_be_greater_than_b(column_A='Age', column_B='TotalWorkingYears', mostly=1.0)",
        "deequ": "satisfies('`Age` - `TotalWorkingYears` >= 15', 'career_start_age_at_least_15', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "The `career_start_age` calculation (`Age - TotalWorkingYears`) implicitly assumes that `Age` is sufficiently greater than `TotalWorkingYears` to yield a positive and realistic 'career start age'. Furthermore, the `career_start_signal` calculation in line 88 (`(career_start_age - 15).clip(lower=0)`) explicitly implies that the calculated `career_start_age` (i.e., `Age - TotalWorkingYears`) should be at least 15, representing a plausible minimum age for starting a career.",
        "sourceCodeLines": [
          82,
          88,
          161
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-6454c9db",
      "dataStats": {}
    },
    {
      "id": "constraint-7c7c41a4",
      "column": "TotalWorkingYears",
      "type": "completeness",
      "columnType": "textual",
      "label": "TotalWorkingYears (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_not_be_null(column='TotalWorkingYears')",
        "deequ": "isComplete('TotalWorkingYears')"
      },
      "assumption": {
        "text": "The code performs arithmetic operations (subtraction) on the `TotalWorkingYears` column in lines 81 and 82 without explicit handling for null or missing values. This implicitly assumes that the `TotalWorkingYears` column is complete and does not contain any nulls. Null values would propagate as `NaN` through calculations like `external_experience` (line 81) and `career_start_age` (line 82), potentially affecting subsequent operations such as `np.sqrt` (line 87) and conditional `max()` checks (lines 160, 161).",
        "sourceCodeLines": [
          81,
          82,
          87,
          160,
          161
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-c9d4f4a3",
      "dataStats": {}
    },
    {
      "id": "constraint-47bc5dba",
      "column": "WorkLifeBalance",
      "type": "range",
      "columnType": "textual",
      "label": "WorkLifeBalance (range)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_between(column='WorkLifeBalance', min_value=1, max_value=4)",
        "deequ": "isContainedIn('WorkLifeBalance', 1.0, 4.0)"
      },
      "assumption": {
        "text": "The `WorkLifeBalance` column is implicitly assumed to contain numerical values within a range of 1 to 4. This is strongly inferred by the calculation of `dissat`, where `sat_mean` (an average including `WorkLifeBalance`) is normalized using the formula `(sat_mean - 1.0) / 3.0`. This formula effectively scales values from a 1-4 range to a 0-1 range. Values outside this expected range would result in `dissat` values falling outside of 0-1 before the final clipping on line 121, indicating that the normalization is designed for a 1-4 scale.",
        "sourceCodeLines": [
          117,
          118,
          119,
          121
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-d86463f2",
      "dataStats": {}
    },
    {
      "id": "constraint-f1a3962e",
      "column": "WorkLifeBalance",
      "type": "completeness",
      "columnType": "textual",
      "label": "WorkLifeBalance (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_not_be_null(column='WorkLifeBalance')",
        "deequ": "isComplete('WorkLifeBalance')"
      },
      "assumption": {
        "text": "The `WorkLifeBalance` column is implicitly assumed to be complete (non-null) for consistent calculation of the `sat_mean`. While `pandas.DataFrame.mean(axis=1)` handles null values by excluding them, the subsequent calculation of `dissat` (on line 119) is intended to represent a composite satisfaction score based on all three `satisfaction_cols`. If `WorkLifeBalance` is null for a given row, `sat_mean` would be an average of fewer than three components, thus altering the intended interpretation and comparability of the composite dissatisfaction score.",
        "sourceCodeLines": [
          117,
          118,
          119
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-248d29d0",
      "dataStats": {}
    },
    {
      "id": "constraint-a9b33bd8",
      "column": "YearsAtCompany",
      "type": "completeness",
      "columnType": "textual",
      "label": "YearsAtCompany (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_not_be_null(column='YearsAtCompany')",
        "deequ": "isComplete('YearsAtCompany')"
      },
      "assumption": {
        "text": "The 'YearsAtCompany' column is assumed to contain no null or missing values, as it is directly used in arithmetic operations and comparisons without explicit null handling for NaNs specifically within the column itself before these operations.",
        "sourceCodeLines": [
          81,
          83,
          124
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-4f25b6ff",
      "dataStats": {}
    },
    {
      "id": "constraint-40d32813",
      "column": "YearsAtCompany",
      "type": "range",
      "columnType": "textual",
      "label": "YearsAtCompany (range)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_between(column='YearsAtCompany', min_value=0)",
        "deequ": "isNonNegative('YearsAtCompany')"
      },
      "assumption": {
        "text": "The 'YearsAtCompany' column is assumed to contain non-negative numeric values. This is evident from checks like `df[\"YearsAtCompany\"] > 0` (which would be illogical for negative years) and its use in calculations like `TotalWorkingYears - YearsAtCompany` which is subsequently clipped at 0, implying that negative values for years at company are not expected or are treated as an error/edge case.",
        "sourceCodeLines": [
          81,
          83,
          124
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-c095b624",
      "dataStats": {}
    },
    {
      "id": "constraint-bc961088",
      "column": "YearsAtCompany",
      "type": "relationship",
      "columnType": "textual",
      "label": "YearsAtCompany (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_pair_values_a_to_be_greater_than_b(column_A='TotalWorkingYears', column_B='YearsAtCompany', or_equal=True)",
        "deequ": "isLessThanOrEqualTo('YearsAtCompany', 'TotalWorkingYears', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "The 'YearsAtCompany' column is implicitly assumed to be less than or equal to 'TotalWorkingYears'. This is inferred from the calculation `(df[\"TotalWorkingYears\"] - df[\"YearsAtCompany\"]).clip(lower=0)`, which suggests that `YearsAtCompany` should logically not exceed `TotalWorkingYears`. Any scenario where `YearsAtCompany` is greater than `TotalWorkingYears` results in a value of 0 for `external_experience`, indicating this is an unexpected or invalid state.",
        "sourceCodeLines": [
          81
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-05290575",
      "dataStats": {}
    },
    {
      "id": "constraint-9fff019c",
      "column": "YearsWithCurrManager",
      "type": "relationship",
      "columnType": "textual",
      "label": "YearsWithCurrManager (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_pair_values_a_to_be_greater_than_b(column_A='YearsAtCompany', column_B='YearsWithCurrManager', or_equal=True)",
        "deequ": "isLessThanOrEqualTo('YearsWithCurrManager', 'YearsAtCompany')"
      },
      "assumption": {
        "text": "The 'YearsWithCurrManager' column is implicitly assumed to be less than or equal to 'YearsAtCompany'. The `manager_ratio` is calculated using `df[\"YearsWithCurrManager\"] / df[\"YearsAtCompany\"]`, which logically implies that an employee cannot have spent more years with their current manager than their total tenure at the company.",
        "sourceCodeLines": [
          83
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-ec287b44",
      "dataStats": {}
    },
    {
      "id": "constraint-2b3a8831",
      "column": "YearsAtCompany",
      "type": "relationship",
      "columnType": "textual",
      "label": "YearsAtCompany (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_pair_values_a_to_be_greater_than_b(column_A='YearsAtCompany', column_B='YearsSinceLastPromotion', or_equal=True)",
        "deequ": "isLessThanOrEqualTo('YearsSinceLastPromotion', 'YearsAtCompany')"
      },
      "assumption": {
        "text": "The 'YearsSinceLastPromotion' column is implicitly assumed to be less than or equal to 'YearsAtCompany'. The `no_promo_signal` is calculated as a ratio `df[\"YearsSinceLastPromotion\"] / df[\"YearsAtCompany\"]`, which semantically implies that the duration since the last promotion should not exceed the total years spent at the company.",
        "sourceCodeLines": [
          125
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-da32aa0a",
      "dataStats": {}
    },
    {
      "id": "constraint-2fe2d5d7",
      "column": "YearsSinceLastPromotion",
      "type": "relationship",
      "columnType": "textual",
      "label": "YearsSinceLastPromotion (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_pair_values_a_to_be_greater_than_b(column_A='YearsAtCompany', column_B='YearsSinceLastPromotion', or_equal=True)",
        "deequ": "isLessThanOrEqualTo('YearsSinceLastPromotion', 'YearsAtCompany')"
      },
      "assumption": {
        "text": "The 'YearsSinceLastPromotion' column is implicitly assumed to be less than or equal to 'YearsAtCompany'. The `no_promo_signal` is calculated as a ratio `df[\"YearsSinceLastPromotion\"] / df[\"YearsAtCompany\"]`, which semantically implies that the duration since the last promotion should not exceed the total years spent at the company.",
        "sourceCodeLines": [
          125
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-da32aa0a",
      "dataStats": {}
    },
    {
      "id": "constraint-66046bfb",
      "column": "YearsSinceLastPromotion",
      "type": "range",
      "columnType": "textual",
      "label": "YearsSinceLastPromotion (range)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_of_type(column='YearsSinceLastPromotion', type_='float')",
        "deequ": "hasDataType('YearsSinceLastPromotion', ConstrainableDataTypes.Integral)"
      },
      "assumption": {
        "text": "The 'YearsSinceLastPromotion' column is assumed to be a numeric data type, representing a duration. It is also implicitly assumed to contain non-negative values, as negative values would typically be illogical for a duration and the derived 'no_promo_signal' (which uses this column in its calculation) is clipped at a lower bound of 0.0.",
        "sourceCodeLines": [
          125,
          127
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-277755c1",
      "dataStats": {}
    },
    {
      "id": "constraint-724a5e07",
      "column": "YearsSinceLastPromotion",
      "type": "range",
      "columnType": "textual",
      "label": "YearsSinceLastPromotion (range)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_between(column='YearsSinceLastPromotion', min_value=0)",
        "deequ": "isNonNegative('YearsSinceLastPromotion')"
      },
      "assumption": {
        "text": "The 'YearsSinceLastPromotion' column is assumed to be a numeric data type, representing a duration. It is also implicitly assumed to contain non-negative values, as negative values would typically be illogical for a duration and the derived 'no_promo_signal' (which uses this column in its calculation) is clipped at a lower bound of 0.0.",
        "sourceCodeLines": [
          125,
          127
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-277755c1",
      "dataStats": {}
    },
    {
      "id": "constraint-9257fb6f",
      "column": "YearsSinceLastPromotion",
      "type": "completeness",
      "columnType": "textual",
      "label": "YearsSinceLastPromotion (completeness)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_not_be_null(column='YearsSinceLastPromotion')",
        "deequ": "isComplete('YearsSinceLastPromotion')"
      },
      "assumption": {
        "text": "The 'YearsSinceLastPromotion' column is assumed to be complete, meaning it should not contain any missing or null values, as it is directly accessed and used in calculations (like division) without explicit null handling.",
        "sourceCodeLines": [
          125
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-95397ca6",
      "dataStats": {}
    },
    {
      "id": "constraint-5adb8210",
      "column": "YearsSinceLastPromotion",
      "type": "relationship",
      "columnType": "textual",
      "label": "YearsSinceLastPromotion (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_pair_values_a_to_be_greater_than_b(column_A='YearsAtCompany', column_B='YearsSinceLastPromotion', or_equal=True, mostly=1.0)",
        "deequ": "satisfies('`YearsSinceLastPromotion` <= `YearsAtCompany`', 'years_since_last_promotion_le_years_at_company', lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "It is implicitly assumed that 'YearsSinceLastPromotion' should not exceed 'YearsAtCompany' (for records where 'YearsAtCompany' is greater than 0). The code calculates a ratio of 'YearsSinceLastPromotion' to 'YearsAtCompany' and then clips this ratio to a maximum of 1.0. This implies that if 'YearsSinceLastPromotion' is greater than 'YearsAtCompany', it's considered an upper bound or an anomaly, and its effective value in the 'no_promo_signal' is capped at 1.0.",
        "sourceCodeLines": [
          124,
          125,
          127
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-d1748782",
      "dataStats": {}
    },
    {
      "id": "constraint-6944215c",
      "column": "YearsWithCurrManager",
      "type": "format",
      "columnType": "textual",
      "label": "YearsWithCurrManager (format)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_of_type(column='YearsWithCurrManager', type_='float')",
        "deequ": "hasDataType('YearsWithCurrManager', ConstrainableDataTypes.Numeric, lambda x: x == 1.0)"
      },
      "assumption": {
        "text": "The 'YearsWithCurrManager' column is expected to contain numerical values, as it undergoes arithmetic operations (division) and null value imputation with a numerical constant (0).",
        "sourceCodeLines": [
          83
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-b2d94777",
      "dataStats": {}
    },
    {
      "id": "constraint-e7030566",
      "column": "YearsWithCurrManager",
      "type": "range",
      "columnType": "textual",
      "label": "YearsWithCurrManager (range)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_values_to_be_between(column='YearsWithCurrManager', min_value=0)",
        "deequ": "isNonNegative('YearsWithCurrManager')"
      },
      "assumption": {
        "text": "The 'YearsWithCurrManager' column is expected to contain non-negative values. While nulls are explicitly filled with 0, any non-null negative values would result in a negative `manager_ratio` which is then implicitly treated as 0 due to the `np.clip` operation on line 84.",
        "sourceCodeLines": [
          83,
          84
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-ae702fbb",
      "dataStats": {}
    },
    {
      "id": "constraint-65848a4b",
      "column": "YearsAtCompany",
      "type": "relationship",
      "columnType": "textual",
      "label": "YearsAtCompany (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_pair_values_a_to_be_greater_than_b(column_A='YearsAtCompany', column_B='YearsWithCurrManager', or_equal=True)",
        "deequ": "isGreaterThanOrEqualTo('YearsAtCompany', 'YearsWithCurrManager')"
      },
      "assumption": {
        "text": "The 'YearsWithCurrManager' column is implicitly assumed to be less than or equal to the 'YearsAtCompany' column for the same employee. This is inferred from the `manager_ratio` calculation (`YearsWithCurrManager / YearsAtCompany`) being clipped to a maximum of 1.0. If 'YearsWithCurrManager' were to exceed 'YearsAtCompany', the ratio would be greater than 1, but the code explicitly caps it at 1.0.",
        "sourceCodeLines": [
          83,
          84
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-5590617c",
      "dataStats": {}
    },
    {
      "id": "constraint-7de2d1ff",
      "column": "YearsWithCurrManager",
      "type": "relationship",
      "columnType": "textual",
      "label": "YearsWithCurrManager (relationship)",
      "enabled": true,
      "code": {
        "greatExpectations": "expect_column_pair_values_a_to_be_greater_than_b(column_A='YearsAtCompany', column_B='YearsWithCurrManager', or_equal=True)",
        "deequ": "isGreaterThanOrEqualTo('YearsAtCompany', 'YearsWithCurrManager')"
      },
      "assumption": {
        "text": "The 'YearsWithCurrManager' column is implicitly assumed to be less than or equal to the 'YearsAtCompany' column for the same employee. This is inferred from the `manager_ratio` calculation (`YearsWithCurrManager / YearsAtCompany`) being clipped to a maximum of 1.0. If 'YearsWithCurrManager' were to exceed 'YearsAtCompany', the ratio would be greater than 1, but the code explicitly caps it at 1.0.",
        "sourceCodeLines": [
          83,
          84
        ],
        "sourceFile": "general_task_1.py"
      },
      "assumptionId": "assumption-5590617c",
      "dataStats": {}
    }
  ],
  "assumptions": [
    {
      "id": "assumption-5f82a6b8",
      "text": "The 'Age' column is expected to contain numeric values, as it is used in arithmetic operations like subtraction to calculate 'career_start_age'.",
      "column": "Age",
      "columns": [
        "Age"
      ],
      "sourceCodeLines": [
        82
      ],
      "constraintIds": [
        "constraint-6eca18a3"
      ]
    },
    {
      "id": "assumption-6c17dea0",
      "text": "The 'Age' column is assumed to be greater than or equal to 'TotalWorkingYears' to ensure that the calculated 'career_start_age' (Age - TotalWorkingYears) is a non-negative and logically sound value, representing a person's age when they started their career.",
      "column": "Age",
      "columns": [
        "Age",
        "TotalWorkingYears"
      ],
      "sourceCodeLines": [
        82
      ],
      "constraintIds": [
        "constraint-dc4d03d6",
        "constraint-1ff1b2f9"
      ]
    },
    {
      "id": "assumption-22591095",
      "text": "The derived 'career_start_age' (Age - TotalWorkingYears) is implicitly expected to be at least 15. Although the code clips `(career_start_age - 15)` to a lower bound of 0, this baseline subtraction suggests an implicit understanding of 15 as a minimum reasonable age for starting a career.",
      "column": "Age",
      "columns": [
        "Age",
        "TotalWorkingYears"
      ],
      "sourceCodeLines": [
        82,
        88
      ],
      "constraintIds": [
        "constraint-902f8fa2",
        "constraint-987f5680"
      ]
    },
    {
      "id": "assumption-83ca81b2",
      "text": "The 'AgeGroup' column is expected to contain values that are present in the predefined set of allowed age groups. Values not in `{\"18-25\", \"26-35\", \"36-45\", \"46-55\", \"55+\"}` will not be mapped correctly and will result in NaN, which will propagate to the `risk_score`.",
      "column": "AgeGroup",
      "columns": [
        "AgeGroup"
      ],
      "sourceCodeLines": [
        64,
        71,
        132,
        133,
        134,
        135,
        136,
        137,
        138,
        139
      ],
      "constraintIds": [
        "constraint-e2fc4f41"
      ]
    },
    {
      "id": "assumption-0d2bca48",
      "text": "The 'AgeGroup' column is assumed to be complete and not contain any null or missing values. If null values are present, the `.map()` operation (line 139) will produce NaN, which will propagate through `age_w` to the `risk_score` calculation, potentially resulting in NaN risk scores for those rows.",
      "column": "AgeGroup",
      "columns": [
        "AgeGroup"
      ],
      "sourceCodeLines": [
        139,
        166
      ],
      "constraintIds": [
        "constraint-1f6bbc57"
      ]
    },
    {
      "id": "assumption-2e93e36e",
      "text": "The 'Attrition' column is expected to contain 'Yes' for positive attrition cases. Any other value in this column is implicitly treated as indicating no attrition (e.g., 'No', or other string values would map to 0).",
      "column": "Attrition",
      "columns": [
        "Attrition"
      ],
      "sourceCodeLines": [
        103
      ],
      "constraintIds": [
        "constraint-f5517f3e"
      ]
    },
    {
      "id": "assumption-22b1b7e1",
      "text": "The code implicitly assumes that `NaN` (missing) values in the 'Attrition' column are acceptable and should be treated as indicating no attrition. If `Attrition` is `NaN`, it is mapped to 0 (equivalent to 'No') for all subsequent calculations.",
      "column": "Attrition",
      "columns": [
        "Attrition"
      ],
      "sourceCodeLines": [
        103
      ],
      "constraintIds": [
        "constraint-81a61207"
      ]
    },
    {
      "id": "assumption-5ee2ee04",
      "text": "The 'Department' column is assumed to contain values exclusively from a predefined set: 'Sales', 'Research & Development', and 'Human Resources'. This is explicitly stated in the `dept_allowed` set and is reinforced by the `map` operation which assigns specific weights only to these departments.",
      "column": "Department",
      "columns": [
        "Department"
      ],
      "sourceCodeLines": [
        50,
        59,
        142,
        143,
        144,
        145,
        146
      ],
      "constraintIds": [
        "constraint-b18ecb47"
      ]
    },
    {
      "id": "assumption-3ed8219b",
      "text": "The 'Department' column is assumed to be complete, meaning it should not contain any null or missing values. Operations like equality checks and mapping are performed directly on the column without any explicit handling (e.g., `fillna`, `dropna`) for missing data. If nulls were present, they would lead to unexpected behavior or propagate `NaN` values into subsequent calculations like `dept_weight` and `linear_score`.",
      "column": "Department",
      "columns": [
        "Department"
      ],
      "sourceCodeLines": [
        59,
        142,
        143,
        144,
        145,
        146
      ],
      "constraintIds": [
        "constraint-c39b0f73"
      ]
    },
    {
      "id": "assumption-cccdafab",
      "text": "The `EmployeeNumber` column is expected to contain unique values, as it is included alongside `EmpID` in the output dataframe `risk_out`, implying it acts as an identifier for individual employees.",
      "column": "EmployeeNumber",
      "columns": [
        "EmployeeNumber"
      ],
      "sourceCodeLines": [
        170,
        171
      ],
      "constraintIds": [
        "constraint-fd345361"
      ]
    },
    {
      "id": "assumption-7fc0d8da",
      "text": "The 'EnvironmentSatisfaction' column is expected to contain non-null numeric values. The calculation of `sat_mean` using `.mean(axis=1)` implies that missing values would either lead to NaNs propagating or be implicitly ignored by pandas' default behavior, which might not be the desired outcome if all values are expected to be present.",
      "column": "EnvironmentSatisfaction",
      "columns": [
        "EnvironmentSatisfaction"
      ],
      "sourceCodeLines": [
        117,
        118
      ],
      "constraintIds": [
        "constraint-a508a485"
      ]
    },
    {
      "id": "assumption-1747c2a1",
      "text": "The 'EnvironmentSatisfaction' column is expected to contain numeric values, specifically integers, within the range of 1 to 4, inclusive. This is inferred from the formula `1.0 - (sat_mean - 1.0) / 3.0`, where `sat_mean` is the average of satisfaction columns. This specific normalization formula is designed to map input values from a 1-4 scale to a 0-1 dissatisfaction score. Values outside this range would produce `dissat` scores outside 0-1, which are then clipped, implying an underlying expectation for the source values.",
      "column": "EnvironmentSatisfaction",
      "columns": [
        "EnvironmentSatisfaction"
      ],
      "sourceCodeLines": [
        117,
        118,
        119,
        121
      ],
      "constraintIds": [
        "constraint-161ff4ee"
      ]
    },
    {
      "id": "assumption-7642690e",
      "text": "The code accesses the 'JobRole' column to include it in the 'attrition_risk_scores.csv' output. This implicitly assumes that the 'JobRole' column exists in the input DataFrame.",
      "column": "JobRole",
      "columns": [
        "JobRole"
      ],
      "sourceCodeLines": [
        170,
        171
      ],
      "constraintIds": [
        "constraint-035ad0b9"
      ]
    },
    {
      "id": "assumption-aa65f974",
      "text": "The 'JobSatisfaction' column is implicitly assumed to contain numerical values that can be averaged and used in arithmetic calculations.",
      "column": "JobSatisfaction",
      "columns": [
        "JobSatisfaction"
      ],
      "sourceCodeLines": [
        117,
        118,
        119
      ],
      "constraintIds": [
        "constraint-2856d65e"
      ]
    },
    {
      "id": "assumption-789201bb",
      "text": "The 'JobSatisfaction' column is implicitly assumed to contain values within the range of 1 to 4. This is inferred from the normalization formula `(sat_mean - 1.0) / 3.0` which is typically used to scale values from a [1, 4] range to a [0, 1] range. Values outside this range would lead to 'dissat' being outside [0, 1] before explicit clipping.",
      "column": "JobSatisfaction",
      "columns": [
        "JobSatisfaction"
      ],
      "sourceCodeLines": [
        117,
        118,
        119
      ],
      "constraintIds": [
        "constraint-e4c25999"
      ]
    },
    {
      "id": "assumption-4a430678",
      "text": "The 'JobSatisfaction' column is assumed to be complete (non-null) for all records where an 'attrition_risk_score' is expected. Although `mean()` handles NaNs by default by skipping them, if 'JobSatisfaction' (or other satisfaction columns in a row) were entirely null, `sat_mean` would become NaN, propagating NaNs through 'dissat' to the final `risk_score` in the output.",
      "column": "JobSatisfaction",
      "columns": [
        "JobSatisfaction"
      ],
      "sourceCodeLines": [
        117,
        118,
        119
      ],
      "constraintIds": [
        "constraint-24db5bbd"
      ]
    },
    {
      "id": "assumption-068e7022",
      "text": "The `MonthlyIncome` column is expected to contain numerical values and not have null/missing entries. This is implied by its use in direct numerical comparisons (`>`, `<=`) and aggregate calculations (`median`, `min`, `max`). The presence of non-numeric data would lead to errors, while null values could propagate through calculations (e.g., `row_ok` would evaluate to False or NaN) or result in unexpected behavior in aggregations (e.g., `median` ignoring NaNs, but if a group is all NaNs, returning NaN, which would then affect `progression_logs`).",
      "column": "MonthlyIncome",
      "columns": [
        "MonthlyIncome"
      ],
      "sourceCodeLines": [
        29,
        32,
        33,
        34,
        35,
        41,
        185,
        186,
        187
      ],
      "constraintIds": [
        "constraint-a213a99a",
        "constraint-e635f4f8"
      ]
    },
    {
      "id": "assumption-74003ac4",
      "text": "Values in the `MonthlyIncome` column are expected to be strictly positive (greater than zero). This is explicitly enforced for the 'Upto 5k' salary slab and is generally implied for all slabs, as income is typically a positive quantity.",
      "column": "MonthlyIncome",
      "columns": [
        "MonthlyIncome"
      ],
      "sourceCodeLines": [
        32
      ],
      "constraintIds": [
        "constraint-855e308e"
      ]
    },
    {
      "id": "assumption-7aec03e4",
      "text": "Each record's `MonthlyIncome` is expected to align with its `SalarySlab` category. Specifically, for 'Upto 5k', `MonthlyIncome` should be in (0, 5000]; for '5k-10k', it should be in (5000, 10000]; for '10k-15k', it should be in (10000, 15000]; and for '15k+', it should be > 15000. This consistency is used to create a `salary_ok` flag.",
      "column": "MonthlyIncome",
      "columns": [
        "MonthlyIncome",
        "SalarySlab"
      ],
      "sourceCodeLines": [
        32,
        33,
        34,
        35
      ],
      "constraintIds": []
    },
    {
      "id": "assumption-66729341",
      "text": "The median `MonthlyIncome` values, when grouped by `SalarySlab` and ordered according to the `allowed_slabs` categories, are expected to show a positive and generally increasing progression. The calculation of `progression_logs` as the natural logarithm of the ratio of successive median incomes implies an expectation that median income increases with each higher salary slab.",
      "column": "MonthlyIncome",
      "columns": [
        "MonthlyIncome",
        "SalarySlab"
      ],
      "sourceCodeLines": [
        41,
        42,
        46
      ],
      "constraintIds": [
        "constraint-cce37835",
        "constraint-47914be6"
      ]
    },
    {
      "id": "assumption-6a3e0e00",
      "text": "The `OverTime` column is expected to contain only the categorical values \"Yes\" or \"No\". Any other value, including nulls (NaN), would implicitly be treated as \"No\" for the purpose of calculations and categorizations within the script.",
      "column": "OverTime",
      "columns": [
        "OverTime"
      ],
      "sourceCodeLines": [
        104,
        109,
        110,
        113,
        159,
        170,
        202,
        203
      ],
      "constraintIds": [
        "constraint-a13a8857"
      ]
    },
    {
      "id": "assumption-c33036f8",
      "text": "The 'PercentSalaryHike' column is assumed to contain no missing (null) values. The code directly performs arithmetic operations (subtraction and division) on the column without any explicit null handling (e.g., `fillna()`, `dropna()`). If nulls were present, these operations would result in `NaN`s, which would propagate to `comp_change_norm` and potentially lead to errors or unexpected behavior in downstream calculations.",
      "column": "PercentSalaryHike",
      "columns": [
        "PercentSalaryHike"
      ],
      "sourceCodeLines": [
        97
      ],
      "constraintIds": [
        "constraint-1021d1bd"
      ]
    },
    {
      "id": "assumption-7f8675f7",
      "text": "The 'PercentSalaryHike' column is assumed to be of a numerical data type (e.g., integer or float). The code performs arithmetic operations (subtraction from a scalar, division by a scalar) on the column, which would raise a TypeError if the column contained non-numeric values (e.g., strings, booleans).",
      "column": "PercentSalaryHike",
      "columns": [
        "PercentSalaryHike"
      ],
      "sourceCodeLines": [
        97
      ],
      "constraintIds": [
        "constraint-f82ed2ea"
      ]
    },
    {
      "id": "assumption-196570f9",
      "text": "The 'PercentSalaryHike' column is expected to represent a non-negative percentage increase, likely between 0 and less than 25. The term 'Hike' semantically implies a non-negative value. The calculation `(25 - df[\"PercentSalaryHike\"]) / 14.0` followed by clipping `np.clip(comp_change_norm, 0.0, 2.0)` implies that values of 25 or higher for `PercentSalaryHike` result in `comp_change_norm` being 0.0, and values lower than approximately -3 result in `comp_change_norm` being 2.0. This suggests that for `comp_change_norm` to reflect meaningful variation, `PercentSalaryHike` is expected to be primarily within the range of 0 to 25 (exclusive of 25 for non-zero `comp_change_norm`).",
      "column": "PercentSalaryHike",
      "columns": [
        "PercentSalaryHike"
      ],
      "sourceCodeLines": [
        97
      ],
      "constraintIds": [
        "constraint-90eaf62b"
      ]
    },
    {
      "id": "assumption-8af3d172",
      "text": "The code assumes that the `PerformanceRating` column does not contain missing (null) values, as it directly accesses and compares values without explicit null-checking or handling. If nulls were present, they would implicitly be treated as \"not 4\".",
      "column": "PerformanceRating",
      "columns": [
        "PerformanceRating"
      ],
      "sourceCodeLines": [
        96
      ],
      "constraintIds": [
        "constraint-aea4bb4d"
      ]
    },
    {
      "id": "assumption-0e356a3f",
      "text": "The code explicitly checks if `PerformanceRating` is equal to `4`. This implies that `PerformanceRating` is expected to be a categorical or enumerated value, with `4` being one of the valid and specifically recognized states. Any other value (including other valid ratings, or unexpected data) is grouped as \"not 4\".",
      "column": "PerformanceRating",
      "columns": [
        "PerformanceRating"
      ],
      "sourceCodeLines": [
        96
      ],
      "constraintIds": [
        "constraint-af0d4fa7",
        "constraint-1a80ff4d"
      ]
    },
    {
      "id": "assumption-a87b0cef",
      "text": "The `SalarySlab` column is implicitly assumed to not contain any null or missing values. The code directly accesses and uses the column for filtering, categorical conversion, and grouping operations without explicit null handling, indicating an expectation for its presence in all rows for consistent processing.",
      "column": "SalarySlab",
      "columns": [
        "SalarySlab"
      ],
      "sourceCodeLines": [
        30,
        32,
        33,
        34,
        35,
        40,
        41,
        182
      ],
      "constraintIds": [
        "constraint-8e45b0a2"
      ]
    },
    {
      "id": "assumption-cc52c5a4",
      "text": "The `SalarySlab` column is expected to contain only a specific, ordered set of categorical values: \"Upto 5k\", \"5k-10k\", \"10k-15k\", \"15k+\". The code explicitly defines these allowed categories and converts the column to an ordered categorical type, asserting its enum and ordinal nature.",
      "column": "SalarySlab",
      "columns": [
        "SalarySlab"
      ],
      "sourceCodeLines": [
        25,
        32,
        33,
        34,
        35,
        40,
        41,
        182
      ],
      "constraintIds": [
        "constraint-304ce5d0"
      ]
    },
    {
      "id": "assumption-898b4780",
      "text": "There is a strict relationship between the `SalarySlab` column and the `MonthlyIncome` column, where each `SalarySlab` value corresponds to a specific range for `MonthlyIncome`. Specifically:\n- If `SalarySlab` is \"Upto 5k\", `MonthlyIncome` must be greater than 0 and less than or equal to 5000.\n- If `SalarySlab` is \"5k-10k\", `MonthlyIncome` must be greater than 5000 and less than or equal to 10000.\n- If `SalarySlab` is \"10k-15k\", `MonthlyIncome` must be greater than 10000 and less than or equal to 15000.\n- If `SalarySlab` is \"15k+\", `MonthlyIncome` must be greater than 15000.",
      "column": "SalarySlab",
      "columns": [
        "SalarySlab",
        "MonthlyIncome"
      ],
      "sourceCodeLines": [
        32,
        33,
        34,
        35
      ],
      "constraintIds": [
        "constraint-e8b00bc3",
        "constraint-35fa7e8a",
        "constraint-4e3e34db",
        "constraint-d9f98846",
        "constraint-aed396fc"
      ]
    },
    {
      "id": "assumption-c787b1f8",
      "text": "The `external_experience` calculation assumes that an employee's `TotalWorkingYears` are greater than or equal to the `YearsAtCompany`. If `TotalWorkingYears` were less than `YearsAtCompany`, it would imply working at the current company longer than total career, which is illogical. The result of this subtraction is clipped to `lower=0`, effectively validating that the difference should not be negative.",
      "column": "TotalWorkingYears",
      "columns": [
        "TotalWorkingYears",
        "YearsAtCompany"
      ],
      "sourceCodeLines": [
        81
      ],
      "constraintIds": [
        "constraint-ad8c4ddc",
        "constraint-32997b21"
      ]
    },
    {
      "id": "assumption-6454c9db",
      "text": "The `career_start_age` calculation (`Age - TotalWorkingYears`) implicitly assumes that `Age` is sufficiently greater than `TotalWorkingYears` to yield a positive and realistic 'career start age'. Furthermore, the `career_start_signal` calculation in line 88 (`(career_start_age - 15).clip(lower=0)`) explicitly implies that the calculated `career_start_age` (i.e., `Age - TotalWorkingYears`) should be at least 15, representing a plausible minimum age for starting a career.",
      "column": "TotalWorkingYears",
      "columns": [
        "TotalWorkingYears",
        "Age"
      ],
      "sourceCodeLines": [
        82,
        88,
        161
      ],
      "constraintIds": [
        "constraint-bbabdd8f",
        "constraint-5ae07326"
      ]
    },
    {
      "id": "assumption-c9d4f4a3",
      "text": "The code performs arithmetic operations (subtraction) on the `TotalWorkingYears` column in lines 81 and 82 without explicit handling for null or missing values. This implicitly assumes that the `TotalWorkingYears` column is complete and does not contain any nulls. Null values would propagate as `NaN` through calculations like `external_experience` (line 81) and `career_start_age` (line 82), potentially affecting subsequent operations such as `np.sqrt` (line 87) and conditional `max()` checks (lines 160, 161).",
      "column": "TotalWorkingYears",
      "columns": [
        "TotalWorkingYears"
      ],
      "sourceCodeLines": [
        81,
        82,
        87,
        160,
        161
      ],
      "constraintIds": [
        "constraint-7c7c41a4"
      ]
    },
    {
      "id": "assumption-d86463f2",
      "text": "The `WorkLifeBalance` column is implicitly assumed to contain numerical values within a range of 1 to 4. This is strongly inferred by the calculation of `dissat`, where `sat_mean` (an average including `WorkLifeBalance`) is normalized using the formula `(sat_mean - 1.0) / 3.0`. This formula effectively scales values from a 1-4 range to a 0-1 range. Values outside this expected range would result in `dissat` values falling outside of 0-1 before the final clipping on line 121, indicating that the normalization is designed for a 1-4 scale.",
      "column": "WorkLifeBalance",
      "columns": [
        "WorkLifeBalance"
      ],
      "sourceCodeLines": [
        117,
        118,
        119,
        121
      ],
      "constraintIds": [
        "constraint-47bc5dba"
      ]
    },
    {
      "id": "assumption-248d29d0",
      "text": "The `WorkLifeBalance` column is implicitly assumed to be complete (non-null) for consistent calculation of the `sat_mean`. While `pandas.DataFrame.mean(axis=1)` handles null values by excluding them, the subsequent calculation of `dissat` (on line 119) is intended to represent a composite satisfaction score based on all three `satisfaction_cols`. If `WorkLifeBalance` is null for a given row, `sat_mean` would be an average of fewer than three components, thus altering the intended interpretation and comparability of the composite dissatisfaction score.",
      "column": "WorkLifeBalance",
      "columns": [
        "WorkLifeBalance"
      ],
      "sourceCodeLines": [
        117,
        118,
        119
      ],
      "constraintIds": [
        "constraint-f1a3962e"
      ]
    },
    {
      "id": "assumption-4f25b6ff",
      "text": "The 'YearsAtCompany' column is assumed to contain no null or missing values, as it is directly used in arithmetic operations and comparisons without explicit null handling for NaNs specifically within the column itself before these operations.",
      "column": "YearsAtCompany",
      "columns": [
        "YearsAtCompany"
      ],
      "sourceCodeLines": [
        81,
        83,
        124
      ],
      "constraintIds": [
        "constraint-a9b33bd8"
      ]
    },
    {
      "id": "assumption-c095b624",
      "text": "The 'YearsAtCompany' column is assumed to contain non-negative numeric values. This is evident from checks like `df[\"YearsAtCompany\"] > 0` (which would be illogical for negative years) and its use in calculations like `TotalWorkingYears - YearsAtCompany` which is subsequently clipped at 0, implying that negative values for years at company are not expected or are treated as an error/edge case.",
      "column": "YearsAtCompany",
      "columns": [
        "YearsAtCompany"
      ],
      "sourceCodeLines": [
        81,
        83,
        124
      ],
      "constraintIds": [
        "constraint-40d32813"
      ]
    },
    {
      "id": "assumption-05290575",
      "text": "The 'YearsAtCompany' column is implicitly assumed to be less than or equal to 'TotalWorkingYears'. This is inferred from the calculation `(df[\"TotalWorkingYears\"] - df[\"YearsAtCompany\"]).clip(lower=0)`, which suggests that `YearsAtCompany` should logically not exceed `TotalWorkingYears`. Any scenario where `YearsAtCompany` is greater than `TotalWorkingYears` results in a value of 0 for `external_experience`, indicating this is an unexpected or invalid state.",
      "column": "YearsAtCompany",
      "columns": [
        "YearsAtCompany",
        "TotalWorkingYears"
      ],
      "sourceCodeLines": [
        81
      ],
      "constraintIds": [
        "constraint-bc961088"
      ]
    },
    {
      "id": "assumption-ec287b44",
      "text": "The 'YearsWithCurrManager' column is implicitly assumed to be less than or equal to 'YearsAtCompany'. The `manager_ratio` is calculated using `df[\"YearsWithCurrManager\"] / df[\"YearsAtCompany\"]`, which logically implies that an employee cannot have spent more years with their current manager than their total tenure at the company.",
      "column": "YearsAtCompany",
      "columns": [
        "YearsAtCompany",
        "YearsWithCurrManager"
      ],
      "sourceCodeLines": [
        83
      ],
      "constraintIds": [
        "constraint-9fff019c"
      ]
    },
    {
      "id": "assumption-da32aa0a",
      "text": "The 'YearsSinceLastPromotion' column is implicitly assumed to be less than or equal to 'YearsAtCompany'. The `no_promo_signal` is calculated as a ratio `df[\"YearsSinceLastPromotion\"] / df[\"YearsAtCompany\"]`, which semantically implies that the duration since the last promotion should not exceed the total years spent at the company.",
      "column": "YearsAtCompany",
      "columns": [
        "YearsAtCompany",
        "YearsSinceLastPromotion"
      ],
      "sourceCodeLines": [
        125
      ],
      "constraintIds": [
        "constraint-2b3a8831",
        "constraint-2fe2d5d7"
      ]
    },
    {
      "id": "assumption-277755c1",
      "text": "The 'YearsSinceLastPromotion' column is assumed to be a numeric data type, representing a duration. It is also implicitly assumed to contain non-negative values, as negative values would typically be illogical for a duration and the derived 'no_promo_signal' (which uses this column in its calculation) is clipped at a lower bound of 0.0.",
      "column": "YearsSinceLastPromotion",
      "columns": [
        "YearsSinceLastPromotion"
      ],
      "sourceCodeLines": [
        125,
        127
      ],
      "constraintIds": [
        "constraint-66046bfb",
        "constraint-724a5e07"
      ]
    },
    {
      "id": "assumption-95397ca6",
      "text": "The 'YearsSinceLastPromotion' column is assumed to be complete, meaning it should not contain any missing or null values, as it is directly accessed and used in calculations (like division) without explicit null handling.",
      "column": "YearsSinceLastPromotion",
      "columns": [
        "YearsSinceLastPromotion"
      ],
      "sourceCodeLines": [
        125
      ],
      "constraintIds": [
        "constraint-9257fb6f"
      ]
    },
    {
      "id": "assumption-d1748782",
      "text": "It is implicitly assumed that 'YearsSinceLastPromotion' should not exceed 'YearsAtCompany' (for records where 'YearsAtCompany' is greater than 0). The code calculates a ratio of 'YearsSinceLastPromotion' to 'YearsAtCompany' and then clips this ratio to a maximum of 1.0. This implies that if 'YearsSinceLastPromotion' is greater than 'YearsAtCompany', it's considered an upper bound or an anomaly, and its effective value in the 'no_promo_signal' is capped at 1.0.",
      "column": "YearsSinceLastPromotion",
      "columns": [
        "YearsSinceLastPromotion",
        "YearsAtCompany"
      ],
      "sourceCodeLines": [
        124,
        125,
        127
      ],
      "constraintIds": [
        "constraint-5adb8210"
      ]
    },
    {
      "id": "assumption-b2d94777",
      "text": "The 'YearsWithCurrManager' column is expected to contain numerical values, as it undergoes arithmetic operations (division) and null value imputation with a numerical constant (0).",
      "column": "YearsWithCurrManager",
      "columns": [
        "YearsWithCurrManager"
      ],
      "sourceCodeLines": [
        83
      ],
      "constraintIds": [
        "constraint-6944215c"
      ]
    },
    {
      "id": "assumption-ae702fbb",
      "text": "The 'YearsWithCurrManager' column is expected to contain non-negative values. While nulls are explicitly filled with 0, any non-null negative values would result in a negative `manager_ratio` which is then implicitly treated as 0 due to the `np.clip` operation on line 84.",
      "column": "YearsWithCurrManager",
      "columns": [
        "YearsWithCurrManager"
      ],
      "sourceCodeLines": [
        83,
        84
      ],
      "constraintIds": [
        "constraint-e7030566"
      ]
    },
    {
      "id": "assumption-5590617c",
      "text": "The 'YearsWithCurrManager' column is implicitly assumed to be less than or equal to the 'YearsAtCompany' column for the same employee. This is inferred from the `manager_ratio` calculation (`YearsWithCurrManager / YearsAtCompany`) being clipped to a maximum of 1.0. If 'YearsWithCurrManager' were to exceed 'YearsAtCompany', the ratio would be greater than 1, but the code explicitly caps it at 1.0.",
      "column": "YearsWithCurrManager",
      "columns": [
        "YearsWithCurrManager",
        "YearsAtCompany"
      ],
      "sourceCodeLines": [
        83,
        84
      ],
      "constraintIds": [
        "constraint-65848a4b",
        "constraint-7de2d1ff"
      ]
    }
  ],
  "flowGraph": {
    "nodes": [
      {
        "id": "code-main",
        "type": "code",
        "label": "general_task_1.py",
        "columnType": null,
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 0.0,
          "y": 850.0
        }
      },
      {
        "id": "data-Age",
        "type": "data",
        "label": "Age",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 0.0
        }
      },
      {
        "id": "data-AgeGroup",
        "type": "data",
        "label": "AgeGroup",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 100.0
        }
      },
      {
        "id": "data-Attrition",
        "type": "data",
        "label": "Attrition",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 200.0
        }
      },
      {
        "id": "data-Department",
        "type": "data",
        "label": "Department",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 300.0
        }
      },
      {
        "id": "data-EmployeeNumber",
        "type": "data",
        "label": "EmployeeNumber",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 400.0
        }
      },
      {
        "id": "data-EnvironmentSatisfaction",
        "type": "data",
        "label": "EnvironmentSatisfaction",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 500.0
        }
      },
      {
        "id": "data-JobRole",
        "type": "data",
        "label": "JobRole",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 600.0
        }
      },
      {
        "id": "data-JobSatisfaction",
        "type": "data",
        "label": "JobSatisfaction",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 700.0
        }
      },
      {
        "id": "data-MonthlyIncome",
        "type": "data",
        "label": "MonthlyIncome",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 800.0
        }
      },
      {
        "id": "data-OverTime",
        "type": "data",
        "label": "OverTime",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 900.0
        }
      },
      {
        "id": "data-PercentSalaryHike",
        "type": "data",
        "label": "PercentSalaryHike",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 1000.0
        }
      },
      {
        "id": "data-PerformanceRating",
        "type": "data",
        "label": "PerformanceRating",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 1100.0
        }
      },
      {
        "id": "data-SalarySlab",
        "type": "data",
        "label": "SalarySlab",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 1200.0
        }
      },
      {
        "id": "data-TotalWorkingYears",
        "type": "data",
        "label": "TotalWorkingYears",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 1300.0
        }
      },
      {
        "id": "data-WorkLifeBalance",
        "type": "data",
        "label": "WorkLifeBalance",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 1400.0
        }
      },
      {
        "id": "data-YearsAtCompany",
        "type": "data",
        "label": "YearsAtCompany",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 1500.0
        }
      },
      {
        "id": "data-YearsSinceLastPromotion",
        "type": "data",
        "label": "YearsSinceLastPromotion",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 1600.0
        }
      },
      {
        "id": "data-YearsWithCurrManager",
        "type": "data",
        "label": "YearsWithCurrManager",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": null,
        "position": {
          "x": 200.0,
          "y": 1700.0
        }
      },
      {
        "id": "assumption-assumption-5f82a6b8",
        "type": "assumption",
        "label": "The 'Age' column is expected t...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-5f82a6b8",
        "position": {
          "x": 400.0,
          "y": 0.0
        }
      },
      {
        "id": "assumption-assumption-6c17dea0",
        "type": "assumption",
        "label": "The 'Age' column is assumed to...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-6c17dea0",
        "position": {
          "x": 400.0,
          "y": 100.0
        }
      },
      {
        "id": "assumption-assumption-22591095",
        "type": "assumption",
        "label": "The derived 'career_start_age'...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-22591095",
        "position": {
          "x": 400.0,
          "y": 200.0
        }
      },
      {
        "id": "assumption-assumption-83ca81b2",
        "type": "assumption",
        "label": "The 'AgeGroup' column is expec...",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": "assumption-83ca81b2",
        "position": {
          "x": 400.0,
          "y": 300.0
        }
      },
      {
        "id": "assumption-assumption-0d2bca48",
        "type": "assumption",
        "label": "The 'AgeGroup' column is assum...",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": "assumption-0d2bca48",
        "position": {
          "x": 400.0,
          "y": 400.0
        }
      },
      {
        "id": "assumption-assumption-2e93e36e",
        "type": "assumption",
        "label": "The 'Attrition' column is expe...",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": "assumption-2e93e36e",
        "position": {
          "x": 400.0,
          "y": 500.0
        }
      },
      {
        "id": "assumption-assumption-22b1b7e1",
        "type": "assumption",
        "label": "The code implicitly assumes th...",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": "assumption-22b1b7e1",
        "position": {
          "x": 400.0,
          "y": 600.0
        }
      },
      {
        "id": "assumption-assumption-5ee2ee04",
        "type": "assumption",
        "label": "The 'Department' column is ass...",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": "assumption-5ee2ee04",
        "position": {
          "x": 400.0,
          "y": 700.0
        }
      },
      {
        "id": "assumption-assumption-3ed8219b",
        "type": "assumption",
        "label": "The 'Department' column is ass...",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": "assumption-3ed8219b",
        "position": {
          "x": 400.0,
          "y": 800.0
        }
      },
      {
        "id": "assumption-assumption-cccdafab",
        "type": "assumption",
        "label": "The `EmployeeNumber` column is...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-cccdafab",
        "position": {
          "x": 400.0,
          "y": 900.0
        }
      },
      {
        "id": "assumption-assumption-7fc0d8da",
        "type": "assumption",
        "label": "The 'EnvironmentSatisfaction' ...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-7fc0d8da",
        "position": {
          "x": 400.0,
          "y": 1000.0
        }
      },
      {
        "id": "assumption-assumption-1747c2a1",
        "type": "assumption",
        "label": "The 'EnvironmentSatisfaction' ...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-1747c2a1",
        "position": {
          "x": 400.0,
          "y": 1100.0
        }
      },
      {
        "id": "assumption-assumption-7642690e",
        "type": "assumption",
        "label": "The code accesses the 'JobRole...",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": "assumption-7642690e",
        "position": {
          "x": 400.0,
          "y": 1200.0
        }
      },
      {
        "id": "assumption-assumption-aa65f974",
        "type": "assumption",
        "label": "The 'JobSatisfaction' column i...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-aa65f974",
        "position": {
          "x": 400.0,
          "y": 1300.0
        }
      },
      {
        "id": "assumption-assumption-789201bb",
        "type": "assumption",
        "label": "The 'JobSatisfaction' column i...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-789201bb",
        "position": {
          "x": 400.0,
          "y": 1400.0
        }
      },
      {
        "id": "assumption-assumption-4a430678",
        "type": "assumption",
        "label": "The 'JobSatisfaction' column i...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-4a430678",
        "position": {
          "x": 400.0,
          "y": 1500.0
        }
      },
      {
        "id": "assumption-assumption-068e7022",
        "type": "assumption",
        "label": "The `MonthlyIncome` column is ...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-068e7022",
        "position": {
          "x": 400.0,
          "y": 1600.0
        }
      },
      {
        "id": "assumption-assumption-74003ac4",
        "type": "assumption",
        "label": "Values in the `MonthlyIncome` ...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-74003ac4",
        "position": {
          "x": 400.0,
          "y": 1700.0
        }
      },
      {
        "id": "assumption-assumption-7aec03e4",
        "type": "assumption",
        "label": "Each record's `MonthlyIncome` ...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-7aec03e4",
        "position": {
          "x": 400.0,
          "y": 1800.0
        }
      },
      {
        "id": "assumption-assumption-66729341",
        "type": "assumption",
        "label": "The median `MonthlyIncome` val...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-66729341",
        "position": {
          "x": 400.0,
          "y": 1900.0
        }
      },
      {
        "id": "assumption-assumption-6a3e0e00",
        "type": "assumption",
        "label": "The `OverTime` column is expec...",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": "assumption-6a3e0e00",
        "position": {
          "x": 400.0,
          "y": 2000.0
        }
      },
      {
        "id": "assumption-assumption-c33036f8",
        "type": "assumption",
        "label": "The 'PercentSalaryHike' column...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-c33036f8",
        "position": {
          "x": 400.0,
          "y": 2100.0
        }
      },
      {
        "id": "assumption-assumption-7f8675f7",
        "type": "assumption",
        "label": "The 'PercentSalaryHike' column...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-7f8675f7",
        "position": {
          "x": 400.0,
          "y": 2200.0
        }
      },
      {
        "id": "assumption-assumption-196570f9",
        "type": "assumption",
        "label": "The 'PercentSalaryHike' column...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-196570f9",
        "position": {
          "x": 400.0,
          "y": 2300.0
        }
      },
      {
        "id": "assumption-assumption-8af3d172",
        "type": "assumption",
        "label": "The code assumes that the `Per...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-8af3d172",
        "position": {
          "x": 400.0,
          "y": 2400.0
        }
      },
      {
        "id": "assumption-assumption-0e356a3f",
        "type": "assumption",
        "label": "The code explicitly checks if ...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-0e356a3f",
        "position": {
          "x": 400.0,
          "y": 2500.0
        }
      },
      {
        "id": "assumption-assumption-a87b0cef",
        "type": "assumption",
        "label": "The `SalarySlab` column is imp...",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": "assumption-a87b0cef",
        "position": {
          "x": 400.0,
          "y": 2600.0
        }
      },
      {
        "id": "assumption-assumption-cc52c5a4",
        "type": "assumption",
        "label": "The `SalarySlab` column is exp...",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": "assumption-cc52c5a4",
        "position": {
          "x": 400.0,
          "y": 2700.0
        }
      },
      {
        "id": "assumption-assumption-898b4780",
        "type": "assumption",
        "label": "There is a strict relationship...",
        "columnType": "categorical",
        "constraintId": null,
        "assumptionId": "assumption-898b4780",
        "position": {
          "x": 400.0,
          "y": 2800.0
        }
      },
      {
        "id": "assumption-assumption-c787b1f8",
        "type": "assumption",
        "label": "The `external_experience` calc...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-c787b1f8",
        "position": {
          "x": 400.0,
          "y": 2900.0
        }
      },
      {
        "id": "assumption-assumption-6454c9db",
        "type": "assumption",
        "label": "The `career_start_age` calcula...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-6454c9db",
        "position": {
          "x": 400.0,
          "y": 3000.0
        }
      },
      {
        "id": "assumption-assumption-c9d4f4a3",
        "type": "assumption",
        "label": "The code performs arithmetic o...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-c9d4f4a3",
        "position": {
          "x": 400.0,
          "y": 3100.0
        }
      },
      {
        "id": "assumption-assumption-d86463f2",
        "type": "assumption",
        "label": "The `WorkLifeBalance` column i...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-d86463f2",
        "position": {
          "x": 400.0,
          "y": 3200.0
        }
      },
      {
        "id": "assumption-assumption-248d29d0",
        "type": "assumption",
        "label": "The `WorkLifeBalance` column i...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-248d29d0",
        "position": {
          "x": 400.0,
          "y": 3300.0
        }
      },
      {
        "id": "assumption-assumption-4f25b6ff",
        "type": "assumption",
        "label": "The 'YearsAtCompany' column is...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-4f25b6ff",
        "position": {
          "x": 400.0,
          "y": 3400.0
        }
      },
      {
        "id": "assumption-assumption-c095b624",
        "type": "assumption",
        "label": "The 'YearsAtCompany' column is...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-c095b624",
        "position": {
          "x": 400.0,
          "y": 3500.0
        }
      },
      {
        "id": "assumption-assumption-05290575",
        "type": "assumption",
        "label": "The 'YearsAtCompany' column is...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-05290575",
        "position": {
          "x": 400.0,
          "y": 3600.0
        }
      },
      {
        "id": "assumption-assumption-ec287b44",
        "type": "assumption",
        "label": "The 'YearsWithCurrManager' col...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-ec287b44",
        "position": {
          "x": 400.0,
          "y": 3700.0
        }
      },
      {
        "id": "assumption-assumption-da32aa0a",
        "type": "assumption",
        "label": "The 'YearsSinceLastPromotion' ...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-da32aa0a",
        "position": {
          "x": 400.0,
          "y": 3800.0
        }
      },
      {
        "id": "assumption-assumption-277755c1",
        "type": "assumption",
        "label": "The 'YearsSinceLastPromotion' ...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-277755c1",
        "position": {
          "x": 400.0,
          "y": 3900.0
        }
      },
      {
        "id": "assumption-assumption-95397ca6",
        "type": "assumption",
        "label": "The 'YearsSinceLastPromotion' ...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-95397ca6",
        "position": {
          "x": 400.0,
          "y": 4000.0
        }
      },
      {
        "id": "assumption-assumption-d1748782",
        "type": "assumption",
        "label": "It is implicitly assumed that ...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-d1748782",
        "position": {
          "x": 400.0,
          "y": 4100.0
        }
      },
      {
        "id": "assumption-assumption-b2d94777",
        "type": "assumption",
        "label": "The 'YearsWithCurrManager' col...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-b2d94777",
        "position": {
          "x": 400.0,
          "y": 4200.0
        }
      },
      {
        "id": "assumption-assumption-ae702fbb",
        "type": "assumption",
        "label": "The 'YearsWithCurrManager' col...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-ae702fbb",
        "position": {
          "x": 400.0,
          "y": 4300.0
        }
      },
      {
        "id": "assumption-assumption-5590617c",
        "type": "assumption",
        "label": "The 'YearsWithCurrManager' col...",
        "columnType": "numerical",
        "constraintId": null,
        "assumptionId": "assumption-5590617c",
        "position": {
          "x": 400.0,
          "y": 4400.0
        }
      },
      {
        "id": "constraint-constraint-6eca18a3",
        "type": "constraint",
        "label": "Age (format)",
        "columnType": null,
        "constraintId": "constraint-6eca18a3",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 0.0
        }
      },
      {
        "id": "constraint-constraint-dc4d03d6",
        "type": "constraint",
        "label": "Age (relationship)",
        "columnType": null,
        "constraintId": "constraint-dc4d03d6",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 100.0
        }
      },
      {
        "id": "constraint-constraint-1ff1b2f9",
        "type": "constraint",
        "label": "TotalWorkingYears (relationship)",
        "columnType": null,
        "constraintId": "constraint-1ff1b2f9",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 200.0
        }
      },
      {
        "id": "constraint-constraint-902f8fa2",
        "type": "constraint",
        "label": "Age (range)",
        "columnType": null,
        "constraintId": "constraint-902f8fa2",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 300.0
        }
      },
      {
        "id": "constraint-constraint-987f5680",
        "type": "constraint",
        "label": "TotalWorkingYears (range)",
        "columnType": null,
        "constraintId": "constraint-987f5680",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 400.0
        }
      },
      {
        "id": "constraint-constraint-e2fc4f41",
        "type": "constraint",
        "label": "AgeGroup (enum)",
        "columnType": null,
        "constraintId": "constraint-e2fc4f41",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 500.0
        }
      },
      {
        "id": "constraint-constraint-1f6bbc57",
        "type": "constraint",
        "label": "AgeGroup (completeness)",
        "columnType": null,
        "constraintId": "constraint-1f6bbc57",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 600.0
        }
      },
      {
        "id": "constraint-constraint-f5517f3e",
        "type": "constraint",
        "label": "Attrition (enum)",
        "columnType": null,
        "constraintId": "constraint-f5517f3e",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 700.0
        }
      },
      {
        "id": "constraint-constraint-81a61207",
        "type": "constraint",
        "label": "Attrition (completeness)",
        "columnType": null,
        "constraintId": "constraint-81a61207",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 800.0
        }
      },
      {
        "id": "constraint-constraint-b18ecb47",
        "type": "constraint",
        "label": "Department (enum)",
        "columnType": null,
        "constraintId": "constraint-b18ecb47",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 900.0
        }
      },
      {
        "id": "constraint-constraint-c39b0f73",
        "type": "constraint",
        "label": "Department (completeness)",
        "columnType": null,
        "constraintId": "constraint-c39b0f73",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 1000.0
        }
      },
      {
        "id": "constraint-constraint-fd345361",
        "type": "constraint",
        "label": "EmployeeNumber (uniqueness)",
        "columnType": null,
        "constraintId": "constraint-fd345361",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 1100.0
        }
      },
      {
        "id": "constraint-constraint-a508a485",
        "type": "constraint",
        "label": "EnvironmentSatisfaction (completeness)",
        "columnType": null,
        "constraintId": "constraint-a508a485",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 1200.0
        }
      },
      {
        "id": "constraint-constraint-161ff4ee",
        "type": "constraint",
        "label": "EnvironmentSatisfaction (range)",
        "columnType": null,
        "constraintId": "constraint-161ff4ee",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 1300.0
        }
      },
      {
        "id": "constraint-constraint-035ad0b9",
        "type": "constraint",
        "label": "JobRole (completeness)",
        "columnType": null,
        "constraintId": "constraint-035ad0b9",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 1400.0
        }
      },
      {
        "id": "constraint-constraint-2856d65e",
        "type": "constraint",
        "label": "JobSatisfaction (format)",
        "columnType": null,
        "constraintId": "constraint-2856d65e",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 1500.0
        }
      },
      {
        "id": "constraint-constraint-e4c25999",
        "type": "constraint",
        "label": "JobSatisfaction (range)",
        "columnType": null,
        "constraintId": "constraint-e4c25999",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 1600.0
        }
      },
      {
        "id": "constraint-constraint-24db5bbd",
        "type": "constraint",
        "label": "JobSatisfaction (completeness)",
        "columnType": null,
        "constraintId": "constraint-24db5bbd",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 1700.0
        }
      },
      {
        "id": "constraint-constraint-a213a99a",
        "type": "constraint",
        "label": "MonthlyIncome (completeness)",
        "columnType": null,
        "constraintId": "constraint-a213a99a",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 1800.0
        }
      },
      {
        "id": "constraint-constraint-e635f4f8",
        "type": "constraint",
        "label": "MonthlyIncome (completeness)",
        "columnType": null,
        "constraintId": "constraint-e635f4f8",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 1900.0
        }
      },
      {
        "id": "constraint-constraint-855e308e",
        "type": "constraint",
        "label": "MonthlyIncome (range)",
        "columnType": null,
        "constraintId": "constraint-855e308e",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 2000.0
        }
      },
      {
        "id": "constraint-constraint-cce37835",
        "type": "constraint",
        "label": "SalarySlab (statistical)",
        "columnType": null,
        "constraintId": "constraint-cce37835",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 2100.0
        }
      },
      {
        "id": "constraint-constraint-47914be6",
        "type": "constraint",
        "label": "MonthlyIncome (statistical)",
        "columnType": null,
        "constraintId": "constraint-47914be6",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 2200.0
        }
      },
      {
        "id": "constraint-constraint-a13a8857",
        "type": "constraint",
        "label": "OverTime (enum)",
        "columnType": null,
        "constraintId": "constraint-a13a8857",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 2300.0
        }
      },
      {
        "id": "constraint-constraint-1021d1bd",
        "type": "constraint",
        "label": "PercentSalaryHike (completeness)",
        "columnType": null,
        "constraintId": "constraint-1021d1bd",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 2400.0
        }
      },
      {
        "id": "constraint-constraint-f82ed2ea",
        "type": "constraint",
        "label": "PercentSalaryHike (format)",
        "columnType": null,
        "constraintId": "constraint-f82ed2ea",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 2500.0
        }
      },
      {
        "id": "constraint-constraint-90eaf62b",
        "type": "constraint",
        "label": "PercentSalaryHike (range)",
        "columnType": null,
        "constraintId": "constraint-90eaf62b",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 2600.0
        }
      },
      {
        "id": "constraint-constraint-aea4bb4d",
        "type": "constraint",
        "label": "PerformanceRating (completeness)",
        "columnType": null,
        "constraintId": "constraint-aea4bb4d",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 2700.0
        }
      },
      {
        "id": "constraint-constraint-af0d4fa7",
        "type": "constraint",
        "label": "PerformanceRating (enum)",
        "columnType": null,
        "constraintId": "constraint-af0d4fa7",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 2800.0
        }
      },
      {
        "id": "constraint-constraint-1a80ff4d",
        "type": "constraint",
        "label": "PerformanceRating (enum)",
        "columnType": null,
        "constraintId": "constraint-1a80ff4d",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 2900.0
        }
      },
      {
        "id": "constraint-constraint-8e45b0a2",
        "type": "constraint",
        "label": "SalarySlab (completeness)",
        "columnType": null,
        "constraintId": "constraint-8e45b0a2",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 3000.0
        }
      },
      {
        "id": "constraint-constraint-304ce5d0",
        "type": "constraint",
        "label": "SalarySlab (enum)",
        "columnType": null,
        "constraintId": "constraint-304ce5d0",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 3100.0
        }
      },
      {
        "id": "constraint-constraint-e8b00bc3",
        "type": "constraint",
        "label": "SalarySlab (relationship)",
        "columnType": null,
        "constraintId": "constraint-e8b00bc3",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 3200.0
        }
      },
      {
        "id": "constraint-constraint-35fa7e8a",
        "type": "constraint",
        "label": "MonthlyIncome (relationship)",
        "columnType": null,
        "constraintId": "constraint-35fa7e8a",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 3300.0
        }
      },
      {
        "id": "constraint-constraint-4e3e34db",
        "type": "constraint",
        "label": "MonthlyIncome (relationship)",
        "columnType": null,
        "constraintId": "constraint-4e3e34db",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 3400.0
        }
      },
      {
        "id": "constraint-constraint-d9f98846",
        "type": "constraint",
        "label": "MonthlyIncome (relationship)",
        "columnType": null,
        "constraintId": "constraint-d9f98846",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 3500.0
        }
      },
      {
        "id": "constraint-constraint-aed396fc",
        "type": "constraint",
        "label": "MonthlyIncome (relationship)",
        "columnType": null,
        "constraintId": "constraint-aed396fc",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 3600.0
        }
      },
      {
        "id": "constraint-constraint-ad8c4ddc",
        "type": "constraint",
        "label": "TotalWorkingYears (relationship)",
        "columnType": null,
        "constraintId": "constraint-ad8c4ddc",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 3700.0
        }
      },
      {
        "id": "constraint-constraint-32997b21",
        "type": "constraint",
        "label": "YearsAtCompany (relationship)",
        "columnType": null,
        "constraintId": "constraint-32997b21",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 3800.0
        }
      },
      {
        "id": "constraint-constraint-bbabdd8f",
        "type": "constraint",
        "label": "Age (relationship)",
        "columnType": null,
        "constraintId": "constraint-bbabdd8f",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 3900.0
        }
      },
      {
        "id": "constraint-constraint-5ae07326",
        "type": "constraint",
        "label": "TotalWorkingYears (relationship)",
        "columnType": null,
        "constraintId": "constraint-5ae07326",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 4000.0
        }
      },
      {
        "id": "constraint-constraint-7c7c41a4",
        "type": "constraint",
        "label": "TotalWorkingYears (completeness)",
        "columnType": null,
        "constraintId": "constraint-7c7c41a4",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 4100.0
        }
      },
      {
        "id": "constraint-constraint-47bc5dba",
        "type": "constraint",
        "label": "WorkLifeBalance (range)",
        "columnType": null,
        "constraintId": "constraint-47bc5dba",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 4200.0
        }
      },
      {
        "id": "constraint-constraint-f1a3962e",
        "type": "constraint",
        "label": "WorkLifeBalance (completeness)",
        "columnType": null,
        "constraintId": "constraint-f1a3962e",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 4300.0
        }
      },
      {
        "id": "constraint-constraint-a9b33bd8",
        "type": "constraint",
        "label": "YearsAtCompany (completeness)",
        "columnType": null,
        "constraintId": "constraint-a9b33bd8",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 4400.0
        }
      },
      {
        "id": "constraint-constraint-40d32813",
        "type": "constraint",
        "label": "YearsAtCompany (range)",
        "columnType": null,
        "constraintId": "constraint-40d32813",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 4500.0
        }
      },
      {
        "id": "constraint-constraint-bc961088",
        "type": "constraint",
        "label": "YearsAtCompany (relationship)",
        "columnType": null,
        "constraintId": "constraint-bc961088",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 4600.0
        }
      },
      {
        "id": "constraint-constraint-9fff019c",
        "type": "constraint",
        "label": "YearsWithCurrManager (relationship)",
        "columnType": null,
        "constraintId": "constraint-9fff019c",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 4700.0
        }
      },
      {
        "id": "constraint-constraint-2b3a8831",
        "type": "constraint",
        "label": "YearsAtCompany (relationship)",
        "columnType": null,
        "constraintId": "constraint-2b3a8831",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 4800.0
        }
      },
      {
        "id": "constraint-constraint-2fe2d5d7",
        "type": "constraint",
        "label": "YearsSinceLastPromotion (relationship)",
        "columnType": null,
        "constraintId": "constraint-2fe2d5d7",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 4900.0
        }
      },
      {
        "id": "constraint-constraint-66046bfb",
        "type": "constraint",
        "label": "YearsSinceLastPromotion (range)",
        "columnType": null,
        "constraintId": "constraint-66046bfb",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 5000.0
        }
      },
      {
        "id": "constraint-constraint-724a5e07",
        "type": "constraint",
        "label": "YearsSinceLastPromotion (range)",
        "columnType": null,
        "constraintId": "constraint-724a5e07",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 5100.0
        }
      },
      {
        "id": "constraint-constraint-9257fb6f",
        "type": "constraint",
        "label": "YearsSinceLastPromotion (completeness)",
        "columnType": null,
        "constraintId": "constraint-9257fb6f",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 5200.0
        }
      },
      {
        "id": "constraint-constraint-5adb8210",
        "type": "constraint",
        "label": "YearsSinceLastPromotion (relationship)",
        "columnType": null,
        "constraintId": "constraint-5adb8210",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 5300.0
        }
      },
      {
        "id": "constraint-constraint-6944215c",
        "type": "constraint",
        "label": "YearsWithCurrManager (format)",
        "columnType": null,
        "constraintId": "constraint-6944215c",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 5400.0
        }
      },
      {
        "id": "constraint-constraint-e7030566",
        "type": "constraint",
        "label": "YearsWithCurrManager (range)",
        "columnType": null,
        "constraintId": "constraint-e7030566",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 5500.0
        }
      },
      {
        "id": "constraint-constraint-65848a4b",
        "type": "constraint",
        "label": "YearsAtCompany (relationship)",
        "columnType": null,
        "constraintId": "constraint-65848a4b",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 5600.0
        }
      },
      {
        "id": "constraint-constraint-7de2d1ff",
        "type": "constraint",
        "label": "YearsWithCurrManager (relationship)",
        "columnType": null,
        "constraintId": "constraint-7de2d1ff",
        "assumptionId": null,
        "position": {
          "x": 600.0,
          "y": 5700.0
        }
      }
    ],
    "edges": [
      {
        "id": "e-code-data-Age",
        "source": "code-main",
        "target": "data-Age",
        "label": null
      },
      {
        "id": "e-code-data-AgeGroup",
        "source": "code-main",
        "target": "data-AgeGroup",
        "label": null
      },
      {
        "id": "e-code-data-Attrition",
        "source": "code-main",
        "target": "data-Attrition",
        "label": null
      },
      {
        "id": "e-code-data-Department",
        "source": "code-main",
        "target": "data-Department",
        "label": null
      },
      {
        "id": "e-code-data-EmployeeNumber",
        "source": "code-main",
        "target": "data-EmployeeNumber",
        "label": null
      },
      {
        "id": "e-code-data-EnvironmentSatisfaction",
        "source": "code-main",
        "target": "data-EnvironmentSatisfaction",
        "label": null
      },
      {
        "id": "e-code-data-JobRole",
        "source": "code-main",
        "target": "data-JobRole",
        "label": null
      },
      {
        "id": "e-code-data-JobSatisfaction",
        "source": "code-main",
        "target": "data-JobSatisfaction",
        "label": null
      },
      {
        "id": "e-code-data-MonthlyIncome",
        "source": "code-main",
        "target": "data-MonthlyIncome",
        "label": null
      },
      {
        "id": "e-code-data-OverTime",
        "source": "code-main",
        "target": "data-OverTime",
        "label": null
      },
      {
        "id": "e-code-data-PercentSalaryHike",
        "source": "code-main",
        "target": "data-PercentSalaryHike",
        "label": null
      },
      {
        "id": "e-code-data-PerformanceRating",
        "source": "code-main",
        "target": "data-PerformanceRating",
        "label": null
      },
      {
        "id": "e-code-data-SalarySlab",
        "source": "code-main",
        "target": "data-SalarySlab",
        "label": null
      },
      {
        "id": "e-code-data-TotalWorkingYears",
        "source": "code-main",
        "target": "data-TotalWorkingYears",
        "label": null
      },
      {
        "id": "e-code-data-WorkLifeBalance",
        "source": "code-main",
        "target": "data-WorkLifeBalance",
        "label": null
      },
      {
        "id": "e-code-data-YearsAtCompany",
        "source": "code-main",
        "target": "data-YearsAtCompany",
        "label": null
      },
      {
        "id": "e-code-data-YearsSinceLastPromotion",
        "source": "code-main",
        "target": "data-YearsSinceLastPromotion",
        "label": null
      },
      {
        "id": "e-code-data-YearsWithCurrManager",
        "source": "code-main",
        "target": "data-YearsWithCurrManager",
        "label": null
      },
      {
        "id": "e-data-Age-assumption-5f82a6b8",
        "source": "data-Age",
        "target": "assumption-assumption-5f82a6b8",
        "label": null
      },
      {
        "id": "e-data-Age-assumption-6c17dea0",
        "source": "data-Age",
        "target": "assumption-assumption-6c17dea0",
        "label": null
      },
      {
        "id": "e-data-TotalWorkingYears-assumption-6c17dea0",
        "source": "data-TotalWorkingYears",
        "target": "assumption-assumption-6c17dea0",
        "label": null
      },
      {
        "id": "e-data-Age-assumption-22591095",
        "source": "data-Age",
        "target": "assumption-assumption-22591095",
        "label": null
      },
      {
        "id": "e-data-TotalWorkingYears-assumption-22591095",
        "source": "data-TotalWorkingYears",
        "target": "assumption-assumption-22591095",
        "label": null
      },
      {
        "id": "e-data-AgeGroup-assumption-83ca81b2",
        "source": "data-AgeGroup",
        "target": "assumption-assumption-83ca81b2",
        "label": null
      },
      {
        "id": "e-data-AgeGroup-assumption-0d2bca48",
        "source": "data-AgeGroup",
        "target": "assumption-assumption-0d2bca48",
        "label": null
      },
      {
        "id": "e-data-Attrition-assumption-2e93e36e",
        "source": "data-Attrition",
        "target": "assumption-assumption-2e93e36e",
        "label": null
      },
      {
        "id": "e-data-Attrition-assumption-22b1b7e1",
        "source": "data-Attrition",
        "target": "assumption-assumption-22b1b7e1",
        "label": null
      },
      {
        "id": "e-data-Department-assumption-5ee2ee04",
        "source": "data-Department",
        "target": "assumption-assumption-5ee2ee04",
        "label": null
      },
      {
        "id": "e-data-Department-assumption-3ed8219b",
        "source": "data-Department",
        "target": "assumption-assumption-3ed8219b",
        "label": null
      },
      {
        "id": "e-data-EmployeeNumber-assumption-cccdafab",
        "source": "data-EmployeeNumber",
        "target": "assumption-assumption-cccdafab",
        "label": null
      },
      {
        "id": "e-data-EnvironmentSatisfaction-assumption-7fc0d8da",
        "source": "data-EnvironmentSatisfaction",
        "target": "assumption-assumption-7fc0d8da",
        "label": null
      },
      {
        "id": "e-data-EnvironmentSatisfaction-assumption-1747c2a1",
        "source": "data-EnvironmentSatisfaction",
        "target": "assumption-assumption-1747c2a1",
        "label": null
      },
      {
        "id": "e-data-JobRole-assumption-7642690e",
        "source": "data-JobRole",
        "target": "assumption-assumption-7642690e",
        "label": null
      },
      {
        "id": "e-data-JobSatisfaction-assumption-aa65f974",
        "source": "data-JobSatisfaction",
        "target": "assumption-assumption-aa65f974",
        "label": null
      },
      {
        "id": "e-data-JobSatisfaction-assumption-789201bb",
        "source": "data-JobSatisfaction",
        "target": "assumption-assumption-789201bb",
        "label": null
      },
      {
        "id": "e-data-JobSatisfaction-assumption-4a430678",
        "source": "data-JobSatisfaction",
        "target": "assumption-assumption-4a430678",
        "label": null
      },
      {
        "id": "e-data-MonthlyIncome-assumption-068e7022",
        "source": "data-MonthlyIncome",
        "target": "assumption-assumption-068e7022",
        "label": null
      },
      {
        "id": "e-data-MonthlyIncome-assumption-74003ac4",
        "source": "data-MonthlyIncome",
        "target": "assumption-assumption-74003ac4",
        "label": null
      },
      {
        "id": "e-data-MonthlyIncome-assumption-7aec03e4",
        "source": "data-MonthlyIncome",
        "target": "assumption-assumption-7aec03e4",
        "label": null
      },
      {
        "id": "e-data-SalarySlab-assumption-7aec03e4",
        "source": "data-SalarySlab",
        "target": "assumption-assumption-7aec03e4",
        "label": null
      },
      {
        "id": "e-data-MonthlyIncome-assumption-66729341",
        "source": "data-MonthlyIncome",
        "target": "assumption-assumption-66729341",
        "label": null
      },
      {
        "id": "e-data-SalarySlab-assumption-66729341",
        "source": "data-SalarySlab",
        "target": "assumption-assumption-66729341",
        "label": null
      },
      {
        "id": "e-data-OverTime-assumption-6a3e0e00",
        "source": "data-OverTime",
        "target": "assumption-assumption-6a3e0e00",
        "label": null
      },
      {
        "id": "e-data-PercentSalaryHike-assumption-c33036f8",
        "source": "data-PercentSalaryHike",
        "target": "assumption-assumption-c33036f8",
        "label": null
      },
      {
        "id": "e-data-PercentSalaryHike-assumption-7f8675f7",
        "source": "data-PercentSalaryHike",
        "target": "assumption-assumption-7f8675f7",
        "label": null
      },
      {
        "id": "e-data-PercentSalaryHike-assumption-196570f9",
        "source": "data-PercentSalaryHike",
        "target": "assumption-assumption-196570f9",
        "label": null
      },
      {
        "id": "e-data-PerformanceRating-assumption-8af3d172",
        "source": "data-PerformanceRating",
        "target": "assumption-assumption-8af3d172",
        "label": null
      },
      {
        "id": "e-data-PerformanceRating-assumption-0e356a3f",
        "source": "data-PerformanceRating",
        "target": "assumption-assumption-0e356a3f",
        "label": null
      },
      {
        "id": "e-data-SalarySlab-assumption-a87b0cef",
        "source": "data-SalarySlab",
        "target": "assumption-assumption-a87b0cef",
        "label": null
      },
      {
        "id": "e-data-SalarySlab-assumption-cc52c5a4",
        "source": "data-SalarySlab",
        "target": "assumption-assumption-cc52c5a4",
        "label": null
      },
      {
        "id": "e-data-SalarySlab-assumption-898b4780",
        "source": "data-SalarySlab",
        "target": "assumption-assumption-898b4780",
        "label": null
      },
      {
        "id": "e-data-MonthlyIncome-assumption-898b4780",
        "source": "data-MonthlyIncome",
        "target": "assumption-assumption-898b4780",
        "label": null
      },
      {
        "id": "e-data-TotalWorkingYears-assumption-c787b1f8",
        "source": "data-TotalWorkingYears",
        "target": "assumption-assumption-c787b1f8",
        "label": null
      },
      {
        "id": "e-data-YearsAtCompany-assumption-c787b1f8",
        "source": "data-YearsAtCompany",
        "target": "assumption-assumption-c787b1f8",
        "label": null
      },
      {
        "id": "e-data-TotalWorkingYears-assumption-6454c9db",
        "source": "data-TotalWorkingYears",
        "target": "assumption-assumption-6454c9db",
        "label": null
      },
      {
        "id": "e-data-Age-assumption-6454c9db",
        "source": "data-Age",
        "target": "assumption-assumption-6454c9db",
        "label": null
      },
      {
        "id": "e-data-TotalWorkingYears-assumption-c9d4f4a3",
        "source": "data-TotalWorkingYears",
        "target": "assumption-assumption-c9d4f4a3",
        "label": null
      },
      {
        "id": "e-data-WorkLifeBalance-assumption-d86463f2",
        "source": "data-WorkLifeBalance",
        "target": "assumption-assumption-d86463f2",
        "label": null
      },
      {
        "id": "e-data-WorkLifeBalance-assumption-248d29d0",
        "source": "data-WorkLifeBalance",
        "target": "assumption-assumption-248d29d0",
        "label": null
      },
      {
        "id": "e-data-YearsAtCompany-assumption-4f25b6ff",
        "source": "data-YearsAtCompany",
        "target": "assumption-assumption-4f25b6ff",
        "label": null
      },
      {
        "id": "e-data-YearsAtCompany-assumption-c095b624",
        "source": "data-YearsAtCompany",
        "target": "assumption-assumption-c095b624",
        "label": null
      },
      {
        "id": "e-data-YearsAtCompany-assumption-05290575",
        "source": "data-YearsAtCompany",
        "target": "assumption-assumption-05290575",
        "label": null
      },
      {
        "id": "e-data-TotalWorkingYears-assumption-05290575",
        "source": "data-TotalWorkingYears",
        "target": "assumption-assumption-05290575",
        "label": null
      },
      {
        "id": "e-data-YearsAtCompany-assumption-ec287b44",
        "source": "data-YearsAtCompany",
        "target": "assumption-assumption-ec287b44",
        "label": null
      },
      {
        "id": "e-data-YearsWithCurrManager-assumption-ec287b44",
        "source": "data-YearsWithCurrManager",
        "target": "assumption-assumption-ec287b44",
        "label": null
      },
      {
        "id": "e-data-YearsAtCompany-assumption-da32aa0a",
        "source": "data-YearsAtCompany",
        "target": "assumption-assumption-da32aa0a",
        "label": null
      },
      {
        "id": "e-data-YearsSinceLastPromotion-assumption-da32aa0a",
        "source": "data-YearsSinceLastPromotion",
        "target": "assumption-assumption-da32aa0a",
        "label": null
      },
      {
        "id": "e-data-YearsSinceLastPromotion-assumption-277755c1",
        "source": "data-YearsSinceLastPromotion",
        "target": "assumption-assumption-277755c1",
        "label": null
      },
      {
        "id": "e-data-YearsSinceLastPromotion-assumption-95397ca6",
        "source": "data-YearsSinceLastPromotion",
        "target": "assumption-assumption-95397ca6",
        "label": null
      },
      {
        "id": "e-data-YearsSinceLastPromotion-assumption-d1748782",
        "source": "data-YearsSinceLastPromotion",
        "target": "assumption-assumption-d1748782",
        "label": null
      },
      {
        "id": "e-data-YearsAtCompany-assumption-d1748782",
        "source": "data-YearsAtCompany",
        "target": "assumption-assumption-d1748782",
        "label": null
      },
      {
        "id": "e-data-YearsWithCurrManager-assumption-b2d94777",
        "source": "data-YearsWithCurrManager",
        "target": "assumption-assumption-b2d94777",
        "label": null
      },
      {
        "id": "e-data-YearsWithCurrManager-assumption-ae702fbb",
        "source": "data-YearsWithCurrManager",
        "target": "assumption-assumption-ae702fbb",
        "label": null
      },
      {
        "id": "e-data-YearsWithCurrManager-assumption-5590617c",
        "source": "data-YearsWithCurrManager",
        "target": "assumption-assumption-5590617c",
        "label": null
      },
      {
        "id": "e-data-YearsAtCompany-assumption-5590617c",
        "source": "data-YearsAtCompany",
        "target": "assumption-assumption-5590617c",
        "label": null
      },
      {
        "id": "e-assumption-assumption-5f82a6b8-constraint-6eca18a3",
        "source": "assumption-assumption-5f82a6b8",
        "target": "constraint-constraint-6eca18a3",
        "label": null
      },
      {
        "id": "e-assumption-assumption-6c17dea0-constraint-dc4d03d6",
        "source": "assumption-assumption-6c17dea0",
        "target": "constraint-constraint-dc4d03d6",
        "label": null
      },
      {
        "id": "e-assumption-assumption-6c17dea0-constraint-1ff1b2f9",
        "source": "assumption-assumption-6c17dea0",
        "target": "constraint-constraint-1ff1b2f9",
        "label": null
      },
      {
        "id": "e-assumption-assumption-22591095-constraint-902f8fa2",
        "source": "assumption-assumption-22591095",
        "target": "constraint-constraint-902f8fa2",
        "label": null
      },
      {
        "id": "e-assumption-assumption-22591095-constraint-987f5680",
        "source": "assumption-assumption-22591095",
        "target": "constraint-constraint-987f5680",
        "label": null
      },
      {
        "id": "e-assumption-assumption-83ca81b2-constraint-e2fc4f41",
        "source": "assumption-assumption-83ca81b2",
        "target": "constraint-constraint-e2fc4f41",
        "label": null
      },
      {
        "id": "e-assumption-assumption-0d2bca48-constraint-1f6bbc57",
        "source": "assumption-assumption-0d2bca48",
        "target": "constraint-constraint-1f6bbc57",
        "label": null
      },
      {
        "id": "e-assumption-assumption-2e93e36e-constraint-f5517f3e",
        "source": "assumption-assumption-2e93e36e",
        "target": "constraint-constraint-f5517f3e",
        "label": null
      },
      {
        "id": "e-assumption-assumption-22b1b7e1-constraint-81a61207",
        "source": "assumption-assumption-22b1b7e1",
        "target": "constraint-constraint-81a61207",
        "label": null
      },
      {
        "id": "e-assumption-assumption-5ee2ee04-constraint-b18ecb47",
        "source": "assumption-assumption-5ee2ee04",
        "target": "constraint-constraint-b18ecb47",
        "label": null
      },
      {
        "id": "e-assumption-assumption-3ed8219b-constraint-c39b0f73",
        "source": "assumption-assumption-3ed8219b",
        "target": "constraint-constraint-c39b0f73",
        "label": null
      },
      {
        "id": "e-assumption-assumption-cccdafab-constraint-fd345361",
        "source": "assumption-assumption-cccdafab",
        "target": "constraint-constraint-fd345361",
        "label": null
      },
      {
        "id": "e-assumption-assumption-7fc0d8da-constraint-a508a485",
        "source": "assumption-assumption-7fc0d8da",
        "target": "constraint-constraint-a508a485",
        "label": null
      },
      {
        "id": "e-assumption-assumption-1747c2a1-constraint-161ff4ee",
        "source": "assumption-assumption-1747c2a1",
        "target": "constraint-constraint-161ff4ee",
        "label": null
      },
      {
        "id": "e-assumption-assumption-7642690e-constraint-035ad0b9",
        "source": "assumption-assumption-7642690e",
        "target": "constraint-constraint-035ad0b9",
        "label": null
      },
      {
        "id": "e-assumption-assumption-aa65f974-constraint-2856d65e",
        "source": "assumption-assumption-aa65f974",
        "target": "constraint-constraint-2856d65e",
        "label": null
      },
      {
        "id": "e-assumption-assumption-789201bb-constraint-e4c25999",
        "source": "assumption-assumption-789201bb",
        "target": "constraint-constraint-e4c25999",
        "label": null
      },
      {
        "id": "e-assumption-assumption-4a430678-constraint-24db5bbd",
        "source": "assumption-assumption-4a430678",
        "target": "constraint-constraint-24db5bbd",
        "label": null
      },
      {
        "id": "e-assumption-assumption-068e7022-constraint-a213a99a",
        "source": "assumption-assumption-068e7022",
        "target": "constraint-constraint-a213a99a",
        "label": null
      },
      {
        "id": "e-assumption-assumption-068e7022-constraint-e635f4f8",
        "source": "assumption-assumption-068e7022",
        "target": "constraint-constraint-e635f4f8",
        "label": null
      },
      {
        "id": "e-assumption-assumption-74003ac4-constraint-855e308e",
        "source": "assumption-assumption-74003ac4",
        "target": "constraint-constraint-855e308e",
        "label": null
      },
      {
        "id": "e-assumption-assumption-66729341-constraint-cce37835",
        "source": "assumption-assumption-66729341",
        "target": "constraint-constraint-cce37835",
        "label": null
      },
      {
        "id": "e-assumption-assumption-66729341-constraint-47914be6",
        "source": "assumption-assumption-66729341",
        "target": "constraint-constraint-47914be6",
        "label": null
      },
      {
        "id": "e-assumption-assumption-6a3e0e00-constraint-a13a8857",
        "source": "assumption-assumption-6a3e0e00",
        "target": "constraint-constraint-a13a8857",
        "label": null
      },
      {
        "id": "e-assumption-assumption-c33036f8-constraint-1021d1bd",
        "source": "assumption-assumption-c33036f8",
        "target": "constraint-constraint-1021d1bd",
        "label": null
      },
      {
        "id": "e-assumption-assumption-7f8675f7-constraint-f82ed2ea",
        "source": "assumption-assumption-7f8675f7",
        "target": "constraint-constraint-f82ed2ea",
        "label": null
      },
      {
        "id": "e-assumption-assumption-196570f9-constraint-90eaf62b",
        "source": "assumption-assumption-196570f9",
        "target": "constraint-constraint-90eaf62b",
        "label": null
      },
      {
        "id": "e-assumption-assumption-8af3d172-constraint-aea4bb4d",
        "source": "assumption-assumption-8af3d172",
        "target": "constraint-constraint-aea4bb4d",
        "label": null
      },
      {
        "id": "e-assumption-assumption-0e356a3f-constraint-af0d4fa7",
        "source": "assumption-assumption-0e356a3f",
        "target": "constraint-constraint-af0d4fa7",
        "label": null
      },
      {
        "id": "e-assumption-assumption-0e356a3f-constraint-1a80ff4d",
        "source": "assumption-assumption-0e356a3f",
        "target": "constraint-constraint-1a80ff4d",
        "label": null
      },
      {
        "id": "e-assumption-assumption-a87b0cef-constraint-8e45b0a2",
        "source": "assumption-assumption-a87b0cef",
        "target": "constraint-constraint-8e45b0a2",
        "label": null
      },
      {
        "id": "e-assumption-assumption-cc52c5a4-constraint-304ce5d0",
        "source": "assumption-assumption-cc52c5a4",
        "target": "constraint-constraint-304ce5d0",
        "label": null
      },
      {
        "id": "e-assumption-assumption-898b4780-constraint-e8b00bc3",
        "source": "assumption-assumption-898b4780",
        "target": "constraint-constraint-e8b00bc3",
        "label": null
      },
      {
        "id": "e-assumption-assumption-898b4780-constraint-35fa7e8a",
        "source": "assumption-assumption-898b4780",
        "target": "constraint-constraint-35fa7e8a",
        "label": null
      },
      {
        "id": "e-assumption-assumption-898b4780-constraint-4e3e34db",
        "source": "assumption-assumption-898b4780",
        "target": "constraint-constraint-4e3e34db",
        "label": null
      },
      {
        "id": "e-assumption-assumption-898b4780-constraint-d9f98846",
        "source": "assumption-assumption-898b4780",
        "target": "constraint-constraint-d9f98846",
        "label": null
      },
      {
        "id": "e-assumption-assumption-898b4780-constraint-aed396fc",
        "source": "assumption-assumption-898b4780",
        "target": "constraint-constraint-aed396fc",
        "label": null
      },
      {
        "id": "e-assumption-assumption-c787b1f8-constraint-ad8c4ddc",
        "source": "assumption-assumption-c787b1f8",
        "target": "constraint-constraint-ad8c4ddc",
        "label": null
      },
      {
        "id": "e-assumption-assumption-c787b1f8-constraint-32997b21",
        "source": "assumption-assumption-c787b1f8",
        "target": "constraint-constraint-32997b21",
        "label": null
      },
      {
        "id": "e-assumption-assumption-6454c9db-constraint-bbabdd8f",
        "source": "assumption-assumption-6454c9db",
        "target": "constraint-constraint-bbabdd8f",
        "label": null
      },
      {
        "id": "e-assumption-assumption-6454c9db-constraint-5ae07326",
        "source": "assumption-assumption-6454c9db",
        "target": "constraint-constraint-5ae07326",
        "label": null
      },
      {
        "id": "e-assumption-assumption-c9d4f4a3-constraint-7c7c41a4",
        "source": "assumption-assumption-c9d4f4a3",
        "target": "constraint-constraint-7c7c41a4",
        "label": null
      },
      {
        "id": "e-assumption-assumption-d86463f2-constraint-47bc5dba",
        "source": "assumption-assumption-d86463f2",
        "target": "constraint-constraint-47bc5dba",
        "label": null
      },
      {
        "id": "e-assumption-assumption-248d29d0-constraint-f1a3962e",
        "source": "assumption-assumption-248d29d0",
        "target": "constraint-constraint-f1a3962e",
        "label": null
      },
      {
        "id": "e-assumption-assumption-4f25b6ff-constraint-a9b33bd8",
        "source": "assumption-assumption-4f25b6ff",
        "target": "constraint-constraint-a9b33bd8",
        "label": null
      },
      {
        "id": "e-assumption-assumption-c095b624-constraint-40d32813",
        "source": "assumption-assumption-c095b624",
        "target": "constraint-constraint-40d32813",
        "label": null
      },
      {
        "id": "e-assumption-assumption-05290575-constraint-bc961088",
        "source": "assumption-assumption-05290575",
        "target": "constraint-constraint-bc961088",
        "label": null
      },
      {
        "id": "e-assumption-assumption-ec287b44-constraint-9fff019c",
        "source": "assumption-assumption-ec287b44",
        "target": "constraint-constraint-9fff019c",
        "label": null
      },
      {
        "id": "e-assumption-assumption-da32aa0a-constraint-2b3a8831",
        "source": "assumption-assumption-da32aa0a",
        "target": "constraint-constraint-2b3a8831",
        "label": null
      },
      {
        "id": "e-assumption-assumption-da32aa0a-constraint-2fe2d5d7",
        "source": "assumption-assumption-da32aa0a",
        "target": "constraint-constraint-2fe2d5d7",
        "label": null
      },
      {
        "id": "e-assumption-assumption-277755c1-constraint-66046bfb",
        "source": "assumption-assumption-277755c1",
        "target": "constraint-constraint-66046bfb",
        "label": null
      },
      {
        "id": "e-assumption-assumption-277755c1-constraint-724a5e07",
        "source": "assumption-assumption-277755c1",
        "target": "constraint-constraint-724a5e07",
        "label": null
      },
      {
        "id": "e-assumption-assumption-95397ca6-constraint-9257fb6f",
        "source": "assumption-assumption-95397ca6",
        "target": "constraint-constraint-9257fb6f",
        "label": null
      },
      {
        "id": "e-assumption-assumption-d1748782-constraint-5adb8210",
        "source": "assumption-assumption-d1748782",
        "target": "constraint-constraint-5adb8210",
        "label": null
      },
      {
        "id": "e-assumption-assumption-b2d94777-constraint-6944215c",
        "source": "assumption-assumption-b2d94777",
        "target": "constraint-constraint-6944215c",
        "label": null
      },
      {
        "id": "e-assumption-assumption-ae702fbb-constraint-e7030566",
        "source": "assumption-assumption-ae702fbb",
        "target": "constraint-constraint-e7030566",
        "label": null
      },
      {
        "id": "e-assumption-assumption-5590617c-constraint-65848a4b",
        "source": "assumption-assumption-5590617c",
        "target": "constraint-constraint-65848a4b",
        "label": null
      },
      {
        "id": "e-assumption-assumption-5590617c-constraint-7de2d1ff",
        "source": "assumption-assumption-5590617c",
        "target": "constraint-constraint-7de2d1ff",
        "label": null
      }
    ]
  },
  "codeAnnotations": [
    {
      "lineNumber": 82,
      "type": "format",
      "columnType": "textual",
      "column": "Age",
      "constraintIds": [
        "constraint-6eca18a3"
      ],
      "highlight": true
    },
    {
      "lineNumber": 82,
      "type": "relationship",
      "columnType": "textual",
      "column": "Age",
      "constraintIds": [
        "constraint-dc4d03d6"
      ],
      "highlight": true
    },
    {
      "lineNumber": 82,
      "type": "relationship",
      "columnType": "textual",
      "column": "TotalWorkingYears",
      "constraintIds": [
        "constraint-1ff1b2f9"
      ],
      "highlight": true
    },
    {
      "lineNumber": 82,
      "type": "range",
      "columnType": "textual",
      "column": "Age",
      "constraintIds": [
        "constraint-902f8fa2"
      ],
      "highlight": true
    },
    {
      "lineNumber": 88,
      "type": "range",
      "columnType": "textual",
      "column": "Age",
      "constraintIds": [
        "constraint-902f8fa2"
      ],
      "highlight": true
    },
    {
      "lineNumber": 82,
      "type": "range",
      "columnType": "textual",
      "column": "TotalWorkingYears",
      "constraintIds": [
        "constraint-987f5680"
      ],
      "highlight": true
    },
    {
      "lineNumber": 88,
      "type": "range",
      "columnType": "textual",
      "column": "TotalWorkingYears",
      "constraintIds": [
        "constraint-987f5680"
      ],
      "highlight": true
    },
    {
      "lineNumber": 64,
      "type": "enum",
      "columnType": "textual",
      "column": "AgeGroup",
      "constraintIds": [
        "constraint-e2fc4f41"
      ],
      "highlight": true
    },
    {
      "lineNumber": 71,
      "type": "enum",
      "columnType": "textual",
      "column": "AgeGroup",
      "constraintIds": [
        "constraint-e2fc4f41"
      ],
      "highlight": true
    },
    {
      "lineNumber": 132,
      "type": "enum",
      "columnType": "textual",
      "column": "AgeGroup",
      "constraintIds": [
        "constraint-e2fc4f41"
      ],
      "highlight": true
    },
    {
      "lineNumber": 133,
      "type": "enum",
      "columnType": "textual",
      "column": "AgeGroup",
      "constraintIds": [
        "constraint-e2fc4f41"
      ],
      "highlight": true
    },
    {
      "lineNumber": 134,
      "type": "enum",
      "columnType": "textual",
      "column": "AgeGroup",
      "constraintIds": [
        "constraint-e2fc4f41"
      ],
      "highlight": true
    },
    {
      "lineNumber": 135,
      "type": "enum",
      "columnType": "textual",
      "column": "AgeGroup",
      "constraintIds": [
        "constraint-e2fc4f41"
      ],
      "highlight": true
    },
    {
      "lineNumber": 136,
      "type": "enum",
      "columnType": "textual",
      "column": "AgeGroup",
      "constraintIds": [
        "constraint-e2fc4f41"
      ],
      "highlight": true
    },
    {
      "lineNumber": 137,
      "type": "enum",
      "columnType": "textual",
      "column": "AgeGroup",
      "constraintIds": [
        "constraint-e2fc4f41"
      ],
      "highlight": true
    },
    {
      "lineNumber": 138,
      "type": "enum",
      "columnType": "textual",
      "column": "AgeGroup",
      "constraintIds": [
        "constraint-e2fc4f41"
      ],
      "highlight": true
    },
    {
      "lineNumber": 139,
      "type": "enum",
      "columnType": "textual",
      "column": "AgeGroup",
      "constraintIds": [
        "constraint-e2fc4f41"
      ],
      "highlight": true
    },
    {
      "lineNumber": 139,
      "type": "completeness",
      "columnType": "textual",
      "column": "AgeGroup",
      "constraintIds": [
        "constraint-1f6bbc57"
      ],
      "highlight": true
    },
    {
      "lineNumber": 166,
      "type": "completeness",
      "columnType": "textual",
      "column": "AgeGroup",
      "constraintIds": [
        "constraint-1f6bbc57"
      ],
      "highlight": true
    },
    {
      "lineNumber": 103,
      "type": "enum",
      "columnType": "textual",
      "column": "Attrition",
      "constraintIds": [
        "constraint-f5517f3e"
      ],
      "highlight": true
    },
    {
      "lineNumber": 103,
      "type": "completeness",
      "columnType": "textual",
      "column": "Attrition",
      "constraintIds": [
        "constraint-81a61207"
      ],
      "highlight": true
    },
    {
      "lineNumber": 50,
      "type": "enum",
      "columnType": "textual",
      "column": "Department",
      "constraintIds": [
        "constraint-b18ecb47"
      ],
      "highlight": true
    },
    {
      "lineNumber": 59,
      "type": "enum",
      "columnType": "textual",
      "column": "Department",
      "constraintIds": [
        "constraint-b18ecb47"
      ],
      "highlight": true
    },
    {
      "lineNumber": 142,
      "type": "enum",
      "columnType": "textual",
      "column": "Department",
      "constraintIds": [
        "constraint-b18ecb47"
      ],
      "highlight": true
    },
    {
      "lineNumber": 143,
      "type": "enum",
      "columnType": "textual",
      "column": "Department",
      "constraintIds": [
        "constraint-b18ecb47"
      ],
      "highlight": true
    },
    {
      "lineNumber": 144,
      "type": "enum",
      "columnType": "textual",
      "column": "Department",
      "constraintIds": [
        "constraint-b18ecb47"
      ],
      "highlight": true
    },
    {
      "lineNumber": 145,
      "type": "enum",
      "columnType": "textual",
      "column": "Department",
      "constraintIds": [
        "constraint-b18ecb47"
      ],
      "highlight": true
    },
    {
      "lineNumber": 146,
      "type": "enum",
      "columnType": "textual",
      "column": "Department",
      "constraintIds": [
        "constraint-b18ecb47"
      ],
      "highlight": true
    },
    {
      "lineNumber": 59,
      "type": "completeness",
      "columnType": "textual",
      "column": "Department",
      "constraintIds": [
        "constraint-c39b0f73"
      ],
      "highlight": true
    },
    {
      "lineNumber": 142,
      "type": "completeness",
      "columnType": "textual",
      "column": "Department",
      "constraintIds": [
        "constraint-c39b0f73"
      ],
      "highlight": true
    },
    {
      "lineNumber": 143,
      "type": "completeness",
      "columnType": "textual",
      "column": "Department",
      "constraintIds": [
        "constraint-c39b0f73"
      ],
      "highlight": true
    },
    {
      "lineNumber": 144,
      "type": "completeness",
      "columnType": "textual",
      "column": "Department",
      "constraintIds": [
        "constraint-c39b0f73"
      ],
      "highlight": true
    },
    {
      "lineNumber": 145,
      "type": "completeness",
      "columnType": "textual",
      "column": "Department",
      "constraintIds": [
        "constraint-c39b0f73"
      ],
      "highlight": true
    },
    {
      "lineNumber": 146,
      "type": "completeness",
      "columnType": "textual",
      "column": "Department",
      "constraintIds": [
        "constraint-c39b0f73"
      ],
      "highlight": true
    },
    {
      "lineNumber": 170,
      "type": "uniqueness",
      "columnType": "textual",
      "column": "EmployeeNumber",
      "constraintIds": [
        "constraint-fd345361"
      ],
      "highlight": true
    },
    {
      "lineNumber": 171,
      "type": "uniqueness",
      "columnType": "textual",
      "column": "EmployeeNumber",
      "constraintIds": [
        "constraint-fd345361"
      ],
      "highlight": true
    },
    {
      "lineNumber": 117,
      "type": "completeness",
      "columnType": "textual",
      "column": "EnvironmentSatisfaction",
      "constraintIds": [
        "constraint-a508a485"
      ],
      "highlight": true
    },
    {
      "lineNumber": 118,
      "type": "completeness",
      "columnType": "textual",
      "column": "EnvironmentSatisfaction",
      "constraintIds": [
        "constraint-a508a485"
      ],
      "highlight": true
    },
    {
      "lineNumber": 117,
      "type": "range",
      "columnType": "textual",
      "column": "EnvironmentSatisfaction",
      "constraintIds": [
        "constraint-161ff4ee"
      ],
      "highlight": true
    },
    {
      "lineNumber": 118,
      "type": "range",
      "columnType": "textual",
      "column": "EnvironmentSatisfaction",
      "constraintIds": [
        "constraint-161ff4ee"
      ],
      "highlight": true
    },
    {
      "lineNumber": 119,
      "type": "range",
      "columnType": "textual",
      "column": "EnvironmentSatisfaction",
      "constraintIds": [
        "constraint-161ff4ee"
      ],
      "highlight": true
    },
    {
      "lineNumber": 121,
      "type": "range",
      "columnType": "textual",
      "column": "EnvironmentSatisfaction",
      "constraintIds": [
        "constraint-161ff4ee"
      ],
      "highlight": true
    },
    {
      "lineNumber": 170,
      "type": "completeness",
      "columnType": "textual",
      "column": "JobRole",
      "constraintIds": [
        "constraint-035ad0b9"
      ],
      "highlight": true
    },
    {
      "lineNumber": 171,
      "type": "completeness",
      "columnType": "textual",
      "column": "JobRole",
      "constraintIds": [
        "constraint-035ad0b9"
      ],
      "highlight": true
    },
    {
      "lineNumber": 117,
      "type": "format",
      "columnType": "textual",
      "column": "JobSatisfaction",
      "constraintIds": [
        "constraint-2856d65e"
      ],
      "highlight": true
    },
    {
      "lineNumber": 118,
      "type": "format",
      "columnType": "textual",
      "column": "JobSatisfaction",
      "constraintIds": [
        "constraint-2856d65e"
      ],
      "highlight": true
    },
    {
      "lineNumber": 119,
      "type": "format",
      "columnType": "textual",
      "column": "JobSatisfaction",
      "constraintIds": [
        "constraint-2856d65e"
      ],
      "highlight": true
    },
    {
      "lineNumber": 117,
      "type": "range",
      "columnType": "textual",
      "column": "JobSatisfaction",
      "constraintIds": [
        "constraint-e4c25999"
      ],
      "highlight": true
    },
    {
      "lineNumber": 118,
      "type": "range",
      "columnType": "textual",
      "column": "JobSatisfaction",
      "constraintIds": [
        "constraint-e4c25999"
      ],
      "highlight": true
    },
    {
      "lineNumber": 119,
      "type": "range",
      "columnType": "textual",
      "column": "JobSatisfaction",
      "constraintIds": [
        "constraint-e4c25999"
      ],
      "highlight": true
    },
    {
      "lineNumber": 117,
      "type": "completeness",
      "columnType": "textual",
      "column": "JobSatisfaction",
      "constraintIds": [
        "constraint-24db5bbd"
      ],
      "highlight": true
    },
    {
      "lineNumber": 118,
      "type": "completeness",
      "columnType": "textual",
      "column": "JobSatisfaction",
      "constraintIds": [
        "constraint-24db5bbd"
      ],
      "highlight": true
    },
    {
      "lineNumber": 119,
      "type": "completeness",
      "columnType": "textual",
      "column": "JobSatisfaction",
      "constraintIds": [
        "constraint-24db5bbd"
      ],
      "highlight": true
    },
    {
      "lineNumber": 29,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-a213a99a"
      ],
      "highlight": true
    },
    {
      "lineNumber": 32,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-a213a99a"
      ],
      "highlight": true
    },
    {
      "lineNumber": 33,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-a213a99a"
      ],
      "highlight": true
    },
    {
      "lineNumber": 34,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-a213a99a"
      ],
      "highlight": true
    },
    {
      "lineNumber": 35,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-a213a99a"
      ],
      "highlight": true
    },
    {
      "lineNumber": 41,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-a213a99a"
      ],
      "highlight": true
    },
    {
      "lineNumber": 185,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-a213a99a"
      ],
      "highlight": true
    },
    {
      "lineNumber": 186,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-a213a99a"
      ],
      "highlight": true
    },
    {
      "lineNumber": 187,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-a213a99a"
      ],
      "highlight": true
    },
    {
      "lineNumber": 29,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-e635f4f8"
      ],
      "highlight": true
    },
    {
      "lineNumber": 32,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-e635f4f8"
      ],
      "highlight": true
    },
    {
      "lineNumber": 33,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-e635f4f8"
      ],
      "highlight": true
    },
    {
      "lineNumber": 34,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-e635f4f8"
      ],
      "highlight": true
    },
    {
      "lineNumber": 35,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-e635f4f8"
      ],
      "highlight": true
    },
    {
      "lineNumber": 41,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-e635f4f8"
      ],
      "highlight": true
    },
    {
      "lineNumber": 185,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-e635f4f8"
      ],
      "highlight": true
    },
    {
      "lineNumber": 186,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-e635f4f8"
      ],
      "highlight": true
    },
    {
      "lineNumber": 187,
      "type": "completeness",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-e635f4f8"
      ],
      "highlight": true
    },
    {
      "lineNumber": 32,
      "type": "range",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-855e308e"
      ],
      "highlight": true
    },
    {
      "lineNumber": 41,
      "type": "statistical",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-cce37835"
      ],
      "highlight": true
    },
    {
      "lineNumber": 42,
      "type": "statistical",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-cce37835"
      ],
      "highlight": true
    },
    {
      "lineNumber": 46,
      "type": "statistical",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-cce37835"
      ],
      "highlight": true
    },
    {
      "lineNumber": 41,
      "type": "statistical",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-47914be6"
      ],
      "highlight": true
    },
    {
      "lineNumber": 42,
      "type": "statistical",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-47914be6"
      ],
      "highlight": true
    },
    {
      "lineNumber": 46,
      "type": "statistical",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-47914be6"
      ],
      "highlight": true
    },
    {
      "lineNumber": 104,
      "type": "enum",
      "columnType": "textual",
      "column": "OverTime",
      "constraintIds": [
        "constraint-a13a8857"
      ],
      "highlight": true
    },
    {
      "lineNumber": 109,
      "type": "enum",
      "columnType": "textual",
      "column": "OverTime",
      "constraintIds": [
        "constraint-a13a8857"
      ],
      "highlight": true
    },
    {
      "lineNumber": 110,
      "type": "enum",
      "columnType": "textual",
      "column": "OverTime",
      "constraintIds": [
        "constraint-a13a8857"
      ],
      "highlight": true
    },
    {
      "lineNumber": 113,
      "type": "enum",
      "columnType": "textual",
      "column": "OverTime",
      "constraintIds": [
        "constraint-a13a8857"
      ],
      "highlight": true
    },
    {
      "lineNumber": 159,
      "type": "enum",
      "columnType": "textual",
      "column": "OverTime",
      "constraintIds": [
        "constraint-a13a8857"
      ],
      "highlight": true
    },
    {
      "lineNumber": 170,
      "type": "enum",
      "columnType": "textual",
      "column": "OverTime",
      "constraintIds": [
        "constraint-a13a8857"
      ],
      "highlight": true
    },
    {
      "lineNumber": 202,
      "type": "enum",
      "columnType": "textual",
      "column": "OverTime",
      "constraintIds": [
        "constraint-a13a8857"
      ],
      "highlight": true
    },
    {
      "lineNumber": 203,
      "type": "enum",
      "columnType": "textual",
      "column": "OverTime",
      "constraintIds": [
        "constraint-a13a8857"
      ],
      "highlight": true
    },
    {
      "lineNumber": 97,
      "type": "completeness",
      "columnType": "textual",
      "column": "PercentSalaryHike",
      "constraintIds": [
        "constraint-1021d1bd"
      ],
      "highlight": true
    },
    {
      "lineNumber": 97,
      "type": "format",
      "columnType": "textual",
      "column": "PercentSalaryHike",
      "constraintIds": [
        "constraint-f82ed2ea"
      ],
      "highlight": true
    },
    {
      "lineNumber": 97,
      "type": "range",
      "columnType": "textual",
      "column": "PercentSalaryHike",
      "constraintIds": [
        "constraint-90eaf62b"
      ],
      "highlight": true
    },
    {
      "lineNumber": 96,
      "type": "completeness",
      "columnType": "textual",
      "column": "PerformanceRating",
      "constraintIds": [
        "constraint-aea4bb4d"
      ],
      "highlight": true
    },
    {
      "lineNumber": 96,
      "type": "enum",
      "columnType": "textual",
      "column": "PerformanceRating",
      "constraintIds": [
        "constraint-af0d4fa7"
      ],
      "highlight": true
    },
    {
      "lineNumber": 96,
      "type": "enum",
      "columnType": "textual",
      "column": "PerformanceRating",
      "constraintIds": [
        "constraint-1a80ff4d"
      ],
      "highlight": true
    },
    {
      "lineNumber": 30,
      "type": "completeness",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-8e45b0a2"
      ],
      "highlight": true
    },
    {
      "lineNumber": 32,
      "type": "completeness",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-8e45b0a2"
      ],
      "highlight": true
    },
    {
      "lineNumber": 33,
      "type": "completeness",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-8e45b0a2"
      ],
      "highlight": true
    },
    {
      "lineNumber": 34,
      "type": "completeness",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-8e45b0a2"
      ],
      "highlight": true
    },
    {
      "lineNumber": 35,
      "type": "completeness",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-8e45b0a2"
      ],
      "highlight": true
    },
    {
      "lineNumber": 40,
      "type": "completeness",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-8e45b0a2"
      ],
      "highlight": true
    },
    {
      "lineNumber": 41,
      "type": "completeness",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-8e45b0a2"
      ],
      "highlight": true
    },
    {
      "lineNumber": 182,
      "type": "completeness",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-8e45b0a2"
      ],
      "highlight": true
    },
    {
      "lineNumber": 25,
      "type": "enum",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-304ce5d0"
      ],
      "highlight": true
    },
    {
      "lineNumber": 32,
      "type": "enum",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-304ce5d0"
      ],
      "highlight": true
    },
    {
      "lineNumber": 33,
      "type": "enum",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-304ce5d0"
      ],
      "highlight": true
    },
    {
      "lineNumber": 34,
      "type": "enum",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-304ce5d0"
      ],
      "highlight": true
    },
    {
      "lineNumber": 35,
      "type": "enum",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-304ce5d0"
      ],
      "highlight": true
    },
    {
      "lineNumber": 40,
      "type": "enum",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-304ce5d0"
      ],
      "highlight": true
    },
    {
      "lineNumber": 41,
      "type": "enum",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-304ce5d0"
      ],
      "highlight": true
    },
    {
      "lineNumber": 182,
      "type": "enum",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-304ce5d0"
      ],
      "highlight": true
    },
    {
      "lineNumber": 32,
      "type": "relationship",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-e8b00bc3"
      ],
      "highlight": true
    },
    {
      "lineNumber": 33,
      "type": "relationship",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-e8b00bc3"
      ],
      "highlight": true
    },
    {
      "lineNumber": 34,
      "type": "relationship",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-e8b00bc3"
      ],
      "highlight": true
    },
    {
      "lineNumber": 35,
      "type": "relationship",
      "columnType": "textual",
      "column": "SalarySlab",
      "constraintIds": [
        "constraint-e8b00bc3"
      ],
      "highlight": true
    },
    {
      "lineNumber": 32,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-35fa7e8a"
      ],
      "highlight": true
    },
    {
      "lineNumber": 33,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-35fa7e8a"
      ],
      "highlight": true
    },
    {
      "lineNumber": 34,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-35fa7e8a"
      ],
      "highlight": true
    },
    {
      "lineNumber": 35,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-35fa7e8a"
      ],
      "highlight": true
    },
    {
      "lineNumber": 32,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-4e3e34db"
      ],
      "highlight": true
    },
    {
      "lineNumber": 33,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-4e3e34db"
      ],
      "highlight": true
    },
    {
      "lineNumber": 34,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-4e3e34db"
      ],
      "highlight": true
    },
    {
      "lineNumber": 35,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-4e3e34db"
      ],
      "highlight": true
    },
    {
      "lineNumber": 32,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-d9f98846"
      ],
      "highlight": true
    },
    {
      "lineNumber": 33,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-d9f98846"
      ],
      "highlight": true
    },
    {
      "lineNumber": 34,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-d9f98846"
      ],
      "highlight": true
    },
    {
      "lineNumber": 35,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-d9f98846"
      ],
      "highlight": true
    },
    {
      "lineNumber": 32,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-aed396fc"
      ],
      "highlight": true
    },
    {
      "lineNumber": 33,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-aed396fc"
      ],
      "highlight": true
    },
    {
      "lineNumber": 34,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-aed396fc"
      ],
      "highlight": true
    },
    {
      "lineNumber": 35,
      "type": "relationship",
      "columnType": "textual",
      "column": "MonthlyIncome",
      "constraintIds": [
        "constraint-aed396fc"
      ],
      "highlight": true
    },
    {
      "lineNumber": 81,
      "type": "relationship",
      "columnType": "textual",
      "column": "TotalWorkingYears",
      "constraintIds": [
        "constraint-ad8c4ddc"
      ],
      "highlight": true
    },
    {
      "lineNumber": 81,
      "type": "relationship",
      "columnType": "textual",
      "column": "YearsAtCompany",
      "constraintIds": [
        "constraint-32997b21"
      ],
      "highlight": true
    },
    {
      "lineNumber": 82,
      "type": "relationship",
      "columnType": "textual",
      "column": "Age",
      "constraintIds": [
        "constraint-bbabdd8f"
      ],
      "highlight": true
    },
    {
      "lineNumber": 88,
      "type": "relationship",
      "columnType": "textual",
      "column": "Age",
      "constraintIds": [
        "constraint-bbabdd8f"
      ],
      "highlight": true
    },
    {
      "lineNumber": 161,
      "type": "relationship",
      "columnType": "textual",
      "column": "Age",
      "constraintIds": [
        "constraint-bbabdd8f"
      ],
      "highlight": true
    },
    {
      "lineNumber": 82,
      "type": "relationship",
      "columnType": "textual",
      "column": "TotalWorkingYears",
      "constraintIds": [
        "constraint-5ae07326"
      ],
      "highlight": true
    },
    {
      "lineNumber": 88,
      "type": "relationship",
      "columnType": "textual",
      "column": "TotalWorkingYears",
      "constraintIds": [
        "constraint-5ae07326"
      ],
      "highlight": true
    },
    {
      "lineNumber": 161,
      "type": "relationship",
      "columnType": "textual",
      "column": "TotalWorkingYears",
      "constraintIds": [
        "constraint-5ae07326"
      ],
      "highlight": true
    },
    {
      "lineNumber": 81,
      "type": "completeness",
      "columnType": "textual",
      "column": "TotalWorkingYears",
      "constraintIds": [
        "constraint-7c7c41a4"
      ],
      "highlight": true
    },
    {
      "lineNumber": 82,
      "type": "completeness",
      "columnType": "textual",
      "column": "TotalWorkingYears",
      "constraintIds": [
        "constraint-7c7c41a4"
      ],
      "highlight": true
    },
    {
      "lineNumber": 87,
      "type": "completeness",
      "columnType": "textual",
      "column": "TotalWorkingYears",
      "constraintIds": [
        "constraint-7c7c41a4"
      ],
      "highlight": true
    },
    {
      "lineNumber": 160,
      "type": "completeness",
      "columnType": "textual",
      "column": "TotalWorkingYears",
      "constraintIds": [
        "constraint-7c7c41a4"
      ],
      "highlight": true
    },
    {
      "lineNumber": 161,
      "type": "completeness",
      "columnType": "textual",
      "column": "TotalWorkingYears",
      "constraintIds": [
        "constraint-7c7c41a4"
      ],
      "highlight": true
    },
    {
      "lineNumber": 117,
      "type": "range",
      "columnType": "textual",
      "column": "WorkLifeBalance",
      "constraintIds": [
        "constraint-47bc5dba"
      ],
      "highlight": true
    },
    {
      "lineNumber": 118,
      "type": "range",
      "columnType": "textual",
      "column": "WorkLifeBalance",
      "constraintIds": [
        "constraint-47bc5dba"
      ],
      "highlight": true
    },
    {
      "lineNumber": 119,
      "type": "range",
      "columnType": "textual",
      "column": "WorkLifeBalance",
      "constraintIds": [
        "constraint-47bc5dba"
      ],
      "highlight": true
    },
    {
      "lineNumber": 121,
      "type": "range",
      "columnType": "textual",
      "column": "WorkLifeBalance",
      "constraintIds": [
        "constraint-47bc5dba"
      ],
      "highlight": true
    },
    {
      "lineNumber": 117,
      "type": "completeness",
      "columnType": "textual",
      "column": "WorkLifeBalance",
      "constraintIds": [
        "constraint-f1a3962e"
      ],
      "highlight": true
    },
    {
      "lineNumber": 118,
      "type": "completeness",
      "columnType": "textual",
      "column": "WorkLifeBalance",
      "constraintIds": [
        "constraint-f1a3962e"
      ],
      "highlight": true
    },
    {
      "lineNumber": 119,
      "type": "completeness",
      "columnType": "textual",
      "column": "WorkLifeBalance",
      "constraintIds": [
        "constraint-f1a3962e"
      ],
      "highlight": true
    },
    {
      "lineNumber": 81,
      "type": "completeness",
      "columnType": "textual",
      "column": "YearsAtCompany",
      "constraintIds": [
        "constraint-a9b33bd8"
      ],
      "highlight": true
    },
    {
      "lineNumber": 83,
      "type": "completeness",
      "columnType": "textual",
      "column": "YearsAtCompany",
      "constraintIds": [
        "constraint-a9b33bd8"
      ],
      "highlight": true
    },
    {
      "lineNumber": 124,
      "type": "completeness",
      "columnType": "textual",
      "column": "YearsAtCompany",
      "constraintIds": [
        "constraint-a9b33bd8"
      ],
      "highlight": true
    },
    {
      "lineNumber": 81,
      "type": "range",
      "columnType": "textual",
      "column": "YearsAtCompany",
      "constraintIds": [
        "constraint-40d32813"
      ],
      "highlight": true
    },
    {
      "lineNumber": 83,
      "type": "range",
      "columnType": "textual",
      "column": "YearsAtCompany",
      "constraintIds": [
        "constraint-40d32813"
      ],
      "highlight": true
    },
    {
      "lineNumber": 124,
      "type": "range",
      "columnType": "textual",
      "column": "YearsAtCompany",
      "constraintIds": [
        "constraint-40d32813"
      ],
      "highlight": true
    },
    {
      "lineNumber": 81,
      "type": "relationship",
      "columnType": "textual",
      "column": "YearsAtCompany",
      "constraintIds": [
        "constraint-bc961088"
      ],
      "highlight": true
    },
    {
      "lineNumber": 83,
      "type": "relationship",
      "columnType": "textual",
      "column": "YearsWithCurrManager",
      "constraintIds": [
        "constraint-9fff019c"
      ],
      "highlight": true
    },
    {
      "lineNumber": 125,
      "type": "relationship",
      "columnType": "textual",
      "column": "YearsAtCompany",
      "constraintIds": [
        "constraint-2b3a8831"
      ],
      "highlight": true
    },
    {
      "lineNumber": 125,
      "type": "relationship",
      "columnType": "textual",
      "column": "YearsSinceLastPromotion",
      "constraintIds": [
        "constraint-2fe2d5d7"
      ],
      "highlight": true
    },
    {
      "lineNumber": 125,
      "type": "range",
      "columnType": "textual",
      "column": "YearsSinceLastPromotion",
      "constraintIds": [
        "constraint-66046bfb"
      ],
      "highlight": true
    },
    {
      "lineNumber": 127,
      "type": "range",
      "columnType": "textual",
      "column": "YearsSinceLastPromotion",
      "constraintIds": [
        "constraint-66046bfb"
      ],
      "highlight": true
    },
    {
      "lineNumber": 125,
      "type": "range",
      "columnType": "textual",
      "column": "YearsSinceLastPromotion",
      "constraintIds": [
        "constraint-724a5e07"
      ],
      "highlight": true
    },
    {
      "lineNumber": 127,
      "type": "range",
      "columnType": "textual",
      "column": "YearsSinceLastPromotion",
      "constraintIds": [
        "constraint-724a5e07"
      ],
      "highlight": true
    },
    {
      "lineNumber": 125,
      "type": "completeness",
      "columnType": "textual",
      "column": "YearsSinceLastPromotion",
      "constraintIds": [
        "constraint-9257fb6f"
      ],
      "highlight": true
    },
    {
      "lineNumber": 124,
      "type": "relationship",
      "columnType": "textual",
      "column": "YearsSinceLastPromotion",
      "constraintIds": [
        "constraint-5adb8210"
      ],
      "highlight": true
    },
    {
      "lineNumber": 125,
      "type": "relationship",
      "columnType": "textual",
      "column": "YearsSinceLastPromotion",
      "constraintIds": [
        "constraint-5adb8210"
      ],
      "highlight": true
    },
    {
      "lineNumber": 127,
      "type": "relationship",
      "columnType": "textual",
      "column": "YearsSinceLastPromotion",
      "constraintIds": [
        "constraint-5adb8210"
      ],
      "highlight": true
    },
    {
      "lineNumber": 83,
      "type": "format",
      "columnType": "textual",
      "column": "YearsWithCurrManager",
      "constraintIds": [
        "constraint-6944215c"
      ],
      "highlight": true
    },
    {
      "lineNumber": 83,
      "type": "range",
      "columnType": "textual",
      "column": "YearsWithCurrManager",
      "constraintIds": [
        "constraint-e7030566"
      ],
      "highlight": true
    },
    {
      "lineNumber": 84,
      "type": "range",
      "columnType": "textual",
      "column": "YearsWithCurrManager",
      "constraintIds": [
        "constraint-e7030566"
      ],
      "highlight": true
    },
    {
      "lineNumber": 83,
      "type": "relationship",
      "columnType": "textual",
      "column": "YearsAtCompany",
      "constraintIds": [
        "constraint-65848a4b"
      ],
      "highlight": true
    },
    {
      "lineNumber": 84,
      "type": "relationship",
      "columnType": "textual",
      "column": "YearsAtCompany",
      "constraintIds": [
        "constraint-65848a4b"
      ],
      "highlight": true
    },
    {
      "lineNumber": 83,
      "type": "relationship",
      "columnType": "textual",
      "column": "YearsWithCurrManager",
      "constraintIds": [
        "constraint-7de2d1ff"
      ],
      "highlight": true
    },
    {
      "lineNumber": 84,
      "type": "relationship",
      "columnType": "textual",
      "column": "YearsWithCurrManager",
      "constraintIds": [
        "constraint-7de2d1ff"
      ],
      "highlight": true
    }
  ],
  "statistics": {
    "constraintCount": 58,
    "assumptionCount": 45,
    "codeLinesCovered": 60,
    "columnsCovered": 18,
    "processingTimeMs": 0,
    "llmCost": 0.7583541200000002,
    "warnings": [],
    "costBreakdown": {
      "columnDetection": 0.005412,
      "dataFlowDetection": 0.0770972,
      "assumptionExtraction": 0.32113672000000004,
      "constraintGeneration": 0.35470820000000014
    }
  }
} as unknown as GenerationResult;

"""DSPy signatures for constraint generation tasks."""

from __future__ import annotations

from typing import Any

try:
    import dspy
except ImportError:
    raise ImportError(
        "dspy is required for generation module. "
        "Install with: uv sync --extra dspy"
    )


class ColumnAccessDetectionSig(dspy.Signature):
    """You are part of a task-aware data validation system that generates data quality constraints by analyzing both datasets and the code that processes them.

    Your role is Column Access Detection: identify which columns from the dataset are accessed or utilized in the given code snippet so we can focus constraint generation on relevant columns.

    You will be given:
    1. A description of available dataset columns (columns_desc)
    2. A code snippet to analyze (code_script)
    3. A description of the downstream task (downstream_task_description)

    Your task:
    - Identify which columns are accessed, read, or used in the code
    - Only return column names that exactly match those in columns_desc
    - For derived columns, map them back to the original raw column names used
    - Return a list of column names (not comma-separated string, but a proper list)
    - If a column appears in conditionals, filters, transformations, or any data operations, include it
    """

    columns_desc: str = dspy.InputField()
    code_script: str = dspy.InputField()
    downstream_task_description: str = dspy.InputField()
    columns: list[str] = dspy.OutputField()


class DataFlowDetectionSig(dspy.Signature):
    """You are an expert in data-flow analysis and code inspection.

    Given a code snippet (with 1-based line numbers) and a target column name,
    identify every line that reads, writes, transforms, filters, merges, or
    otherwise interacts with the target column.

    Include lines that:
    - Directly access the column (e.g., ``df['col']``, ``df.col``)
    - Use derived variables that originated from the column
    - Pass the column through function calls or pipelines
    - Filter, group, or aggregate using the column

    Output only valid JSON with a "sources" array of contiguous 1-based ranges:
      {
        "sources": [
          { "start_line": 2, "end_line": 2 },
          { "start_line": 5, "end_line": 7 }
        ]
      }

    Rules:
      1) Use exact 1-based line numbers from the snippet.
      2) Be exhaustive; any interacting line appears in at least one range.
      3) Adjacent lines should be merged into one range; non-adjacent are separate.
      4) Order of ranges does not matter.
      5) Output only JSON. No extra text.
    """

    code_script: str = dspy.InputField(
        description="The code snippet (with line numbers) to analyze for data flow."
    )
    target_column: str = dspy.InputField(
        description="The specific column name to track in the code."
    )
    task_description: str = dspy.InputField(
        description="Description of the downstream task the code performs."
    )
    sources: list[dict[str, int]] = dspy.OutputField(
        description="List of line ranges that interact with the target column."
    )


class AssumptionExtractionSig(dspy.Signature):
    """You are an expert at analyzing data processing code to infer implicit data quality assumptions.

    Your task is to examine code that processes a dataset and identify what data quality constraints
    the code implicitly assumes or requires. These assumptions will be converted into validation rules.

    Types of assumptions to identify:
    1. **Completeness**: Code assumes no null/missing values (e.g., accessing column without null check)
    2. **Range**: Code filters or expects values within bounds (e.g., age >= 18, price > 0)
    3. **Enum/Categorical**: Code expects specific set of values (e.g., status in ['active', 'pending'])
    4. **Format**: Code expects specific format (e.g., regex patterns, date formats)
    5. **Uniqueness**: Code assumes unique values (e.g., using column as key/ID)
    6. **Statistical**: Code assumes distribution properties (e.g., mean, stddev bounds)
    7. **Relationship**: Code assumes relationships between columns (e.g., end_date > start_date)

    For each assumption you find:
    - Describe it clearly in natural language
    - Identify which column(s) are involved
    - Classify the constraint type
    - Note the specific line numbers where this assumption appears. The code is provided with line numbers. Lines relevant to the target column are highlighted with a ``-**->`` prefix (e.g., ``-**-> 0010: code here``). Non-highlighted lines use ``      0010: code here``. Focus your analysis on highlighted lines but use surrounding context for understanding. Use the exact line numbers in your output.

    Return assumptions as a list of dictionaries with these keys:
    {
        "text": "Natural language description",
        "columns": ["column_name"],
        "type": "completeness|range|enum|format|uniqueness|statistical|relationship",
        "source_lines": [10, 11]
    }

    Focus on columns that are actually accessed in the code (provided in accessed_columns).
    """

    code_script: str = dspy.InputField()
    columns_desc: str = dspy.InputField()
    accessed_columns: str = dspy.InputField()  # Comma-separated
    task_description: str = dspy.InputField()
    assumptions: list[dict[str, Any]] = dspy.OutputField()


class ConstraintCodeGenerationSig(dspy.Signature):
    """You are part of a task-aware data validation system. You serve as the Rule Generation component.

    Your task is to transform code assumptions into formal validation rules. You will generate rules
    in BOTH Great Expectations (GX) format AND Deequ format.

    You will be provided with:
    1. Code snippet being analyzed
    2. Downstream task description
    3. Accessed columns
    4. Extracted assumptions (with text descriptions and source lines)
    5. Available GX expectation function signatures
    6. Available Deequ constraint function signatures

    Your goal is to map each assumption to the appropriate validation rule(s) in both formats.

    For Great Expectations, use function call format like:
    - expect_column_values_to_not_be_null(column="name")
    - expect_column_values_to_be_between(column="age", min_value=18, max_value=65)
    - expect_column_values_to_be_in_set(column="status", value_set=["active", "pending", "closed"])

    For Deequ, use method call format like:
    - .isComplete("name")
    - .isContainedIn("age", 18.0, 65.0)
    - .isContainedIn("status", Array("active", "pending", "closed"))

    Return a JSON object mapping column names to dictionaries with "gx" and "deequ" keys:
    {
        "column_name_1": {
            "gx": ["expect_column_values_to_not_be_null(column='column_name_1')"],
            "deequ": [".isComplete('column_name_1')"]
        },
        "column_name_2": {
            "gx": ["expect_column_values_to_be_between(column='column_name_2', min_value=0, max_value=100)"],
            "deequ": [".isContainedIn('column_name_2', 0.0, 100.0)"]
        }
    }
    """

    code_script: str = dspy.InputField()
    task_description: str = dspy.InputField()
    accessed_columns: str = dspy.InputField()
    assumptions: str = dspy.InputField()  # JSON string
    gx_signatures: str = dspy.InputField()
    deequ_signatures: str = dspy.InputField()
    constraints: dict[str, dict[str, list[str]]] = dspy.OutputField()

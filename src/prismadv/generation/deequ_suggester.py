"""Generate Deequ constraint suggestions using PyDeequ's built-in ConstraintSuggestionRunner."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from prismadv.api.v1.schemas import ConstraintType


# Sentinel column name for dataset-level suggestions (e.g. hasSize).
DATASET_LEVEL_COLUMN = "_dataset_"


@dataclass
class DeequSuggestionItem:
    id: str
    column: str
    constraint_type: ConstraintType
    deequ_code: str
    description: str


def _method_to_constraint_type(code: str) -> ConstraintType:
    """Infer ConstraintType from the Deequ method name in the code string."""
    c = code.lower()
    if any(m in c for m in ("iscomplete", "hascompleteness")):
        return ConstraintType.COMPLETENESS
    if "hasdatatype" in c:
        return ConstraintType.FORMAT
    if any(m in c for m in ("isnonnegative", "ispositive", "hasmin", "hasmax")):
        return ConstraintType.RANGE
    if any(m in c for m in ("isunique", "hasuniqueness", "isprimarykey")):
        return ConstraintType.UNIQUENESS
    if "iscontainedin" in c:
        return ConstraintType.ENUM
    return ConstraintType.STATISTICAL


def _get_or_create_spark():
    """Create or reuse a SparkSession configured for PyDeequ."""
    import pyspark  # type: ignore

    spark_version = ".".join(str(pyspark.__version__).split(".")[:2])
    os.environ.setdefault("SPARK_VERSION", spark_version)

    import pydeequ  # type: ignore
    from pyspark.sql import SparkSession  # type: ignore

    spark = (
        SparkSession.builder.appName("prismadv-deequ-suggestions")
        .master("local[*]")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.jars.packages", pydeequ.deequ_maven_coord)
        .config("spark.jars.excludes", pydeequ.f2j_maven_coord)
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def generate_deequ_suggestions(csv_path: str) -> list[DeequSuggestionItem]:
    """Run PyDeequ's built-in ConstraintSuggestionRunner on a CSV file.

    Uses DEFAULT() rules which cover completeness, data type, non-negativity,
    uniqueness, containment, and size checks.

    Args:
        csv_path: Path to the CSV file to analyse.

    Returns:
        List of DeequSuggestionItem, one per suggested constraint.

    Raises:
        RuntimeError: If PyDeequ/Spark is not available.
    """
    try:
        import pyspark  # type: ignore
        os.environ.setdefault("SPARK_VERSION", ".".join(str(pyspark.__version__).split(".")[:2]))
        from pydeequ.suggestions import ConstraintSuggestionRunner, DEFAULT  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "PyDeequ is not available. Install with `uv sync --all-extras --group dev` "
            "or at least `uv sync --extra deequ`."
        ) from e

    spark = _get_or_create_spark()

    df = (
        spark.read.option("header", "true")
        .option("inferSchema", "true")
        .csv(csv_path)
    )

    result = (
        ConstraintSuggestionRunner(spark)
        .onData(df)
        .addConstraintRule(DEFAULT())
        .run()
    )

    raw_suggestions = result["constraint_suggestions"]

    items: list[DeequSuggestionItem] = []
    for item in raw_suggestions:
        col: str = item.get("column_name") or DATASET_LEVEL_COLUMN
        code: str = item.get("code_for_constraint", "")
        description: str = item.get("description", code)

        # Strip leading dot if present (Deequ sometimes emits ".isComplete(...)")
        deequ_code = code.lstrip(".")

        items.append(
            DeequSuggestionItem(
                id=f"deequ-{uuid.uuid4().hex[:8]}",
                column=col,
                constraint_type=_method_to_constraint_type(code),
                deequ_code=deequ_code,
                description=description,
            )
        )

    return items

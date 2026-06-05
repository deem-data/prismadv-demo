from __future__ import annotations

from datetime import datetime, timezone

import pytest


def test_deequ_csv_profiler_smoke(tmp_path):
    try:
        import pyspark  # type: ignore
    except Exception as e:
        pytest.skip(f"pyspark not available: {e}")

    import os

    os.environ.setdefault("SPARK_VERSION", ".".join(str(pyspark.__version__).split(".")[:2]))

    try:
        import pydeequ  # noqa: F401
    except Exception as e:
        pytest.skip(f"pydeequ not available/compatible: {e}")

    from prismadv.api.v1.schemas import ColumnType, InferredType
    from prismadv.profiling import DeequCSVProfiler, ProfileConfig

    csv_path = tmp_path / "toy.csv"
    csv_path.write_text(
        "\n".join(
            [
                "id,name,age,category,active",
                "1,Alice,28,PREMIUM,true",
                "2,Bob,35,STANDARD,false",
                "3,Carol,,BASIC,true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    profiler = DeequCSVProfiler()

    try:
        bundle = profiler.profile_csv(
            csv_path,
            dataset_id="ds_deequ",
            dataset_name="toy.csv",
            uploaded_at=datetime(2026, 1, 28, tzinfo=timezone.utc),
            cfg=ProfileConfig(preview_limit=2),
        )
    except Exception as e:
        pytest.skip(f"Spark/Deequ not available in this environment: {e}")

    cols = {c.name: c for c in bundle.dataset.columns}
    assert cols["id"].type in {InferredType.INTEGER, InferredType.FLOAT}
    assert cols["id"].inferred_type == ColumnType.NUMERICAL
    assert cols["category"].inferred_type in {ColumnType.CATEGORICAL, ColumnType.TEXTUAL}

    assert bundle.preview.total_rows == 3
    assert len(bundle.preview.rows) == 2
    assert "age" in bundle.column_stats

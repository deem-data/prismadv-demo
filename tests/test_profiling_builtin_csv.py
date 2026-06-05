from __future__ import annotations

from datetime import datetime, timezone

from prismadv.api.v1.schemas import ColumnType, InferredType
from prismadv.profiling import BuiltinCSVProfiler, ProfileConfig


def test_builtin_csv_profiler_profiles_dataset(tmp_path):
    csv_path = tmp_path / "toy.csv"
    categories = ["PREMIUM"] * 5 + ["STANDARD"] * 10 + ["BASIC"] * 5
    lines = ["id,name,age,category,active"]
    for i in range(1, 21):
        name = f"Name{i}"
        age = "" if i == 3 else str(17 + i)  # one missing value; otherwise 18..37
        category = categories[i - 1]
        active = "true" if i % 2 == 1 else "false"
        lines.append(f"{i},{name},{age},{category},{active}")
    csv_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    profiler = BuiltinCSVProfiler()
    bundle = profiler.profile_csv(
        csv_path,
        dataset_id="ds_1",
        dataset_name="toy.csv",
        uploaded_at=datetime(2026, 1, 28, tzinfo=timezone.utc),
        cfg=ProfileConfig(preview_limit=2),
    )

    assert bundle.dataset.id == "ds_1"
    assert bundle.dataset.row_count == 20
    assert bundle.dataset.column_count == 5

    cols = {c.name: c for c in bundle.dataset.columns}
    assert cols["id"].type == InferredType.INTEGER
    assert cols["id"].inferred_type == ColumnType.NUMERICAL
    assert cols["age"].nullable is True
    assert cols["category"].inferred_type == ColumnType.CATEGORICAL

    assert bundle.preview.total_rows == 20
    assert len(bundle.preview.rows) == 2
    assert bundle.preview.rows[0]["id"] == 1
    assert bundle.preview.rows[0]["age"] == 18
    assert bundle.preview.rows[1]["active"] is False

    age_stats = bundle.column_stats["age"].stats
    assert age_stats.null_count == 1
    assert age_stats.min == 18
    assert age_stats.max == 37

    assert 0.0 <= bundle.quality.metrics.completeness <= 1.0

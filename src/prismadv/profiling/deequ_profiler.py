from __future__ import annotations

import math
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from prismadv.api.v1 import schemas as api
from prismadv.profiling.config import ProfileConfig
from prismadv.profiling.errors import MissingDependencyError
from prismadv.profiling.results import ProfileBundle


def _import_deequ():
    import os
    try:
        import pyspark  # type: ignore
        spark_version = ".".join(str(pyspark.__version__).split(".")[:2])
        os.environ.setdefault("SPARK_VERSION", spark_version)

        import pydeequ  # type: ignore
        from pydeequ.profiles import ColumnProfilerRunner  # type: ignore
        from pyspark.sql import SparkSession, functions as F, types as T  # type: ignore
    except RuntimeError as e:  # pragma: no cover
        # pydeequ raises RuntimeError on missing/unsupported SPARK_VERSION at import time
        msg = str(e)
        if "SPARK_VERSION environment variable is required" in msg:
            raise MissingDependencyError(
                "pydeequ requires SPARK_VERSION to be set. "
                "If you use Spark 3.5, you can set `SPARK_VERSION=3.5`."
            ) from e
        raise
    except Exception as e:  # pragma: no cover
        raise MissingDependencyError(
            "Missing deequ dependencies. Install with `uv sync --all-extras --group dev` "
            "or at least `uv sync --extra deequ`."
        ) from e
    return pydeequ, ColumnProfilerRunner, SparkSession, F, T


def _json_safe(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (int, float, bool, str)):
        return v
    if isinstance(v, Decimal):
        return float(v)
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception:
            return str(v)
    return str(v)


def _spark_type_to_inferred(t) -> api.InferredType:
    pydeequ, ColumnProfilerRunner, SparkSession, F, T = _import_deequ()
    if isinstance(t, (T.ByteType, T.ShortType, T.IntegerType, T.LongType)):
        return api.InferredType.INTEGER
    if isinstance(t, (T.FloatType, T.DoubleType, T.DecimalType)):
        return api.InferredType.FLOAT
    if isinstance(t, T.BooleanType):
        return api.InferredType.BOOLEAN
    if isinstance(t, (T.DateType, T.TimestampType)):
        return api.InferredType.DATE
    return api.InferredType.STRING


def _infer_column_type(
    inferred_type: api.InferredType,
    *,
    unique_count: int,
    non_null_count: int,
    cfg: ProfileConfig,
) -> api.ColumnType:
    if inferred_type in {api.InferredType.INTEGER, api.InferredType.FLOAT}:
        return api.ColumnType.NUMERICAL
    if inferred_type == api.InferredType.BOOLEAN:
        return api.ColumnType.CATEGORICAL
    if non_null_count == 0:
        return api.ColumnType.TEXTUAL
    ratio = unique_count / non_null_count
    if unique_count <= cfg.max_categories and ratio <= cfg.categorical_ratio_threshold:
        return api.ColumnType.CATEGORICAL
    return api.ColumnType.TEXTUAL


class DeequCSVProfiler:
    """
    Deequ-based profiler (Spark + PyDeequ).

    Produces API-aligned outputs for dataset preview, per-column stats, and dataset-level quality metrics.
    """

    def __init__(self, spark=None):
        self._spark = spark

    def _get_or_create_spark(self):
        pydeequ, ColumnProfilerRunner, SparkSession, F, T = _import_deequ()
        if self._spark is not None:
            return self._spark

        spark = (
            SparkSession.builder.appName("prismadv-profiler")
            .master("local[*]")
            .config("spark.ui.showConsoleProgress", "false")
            .config("spark.sql.shuffle.partitions", "8")
            .config("spark.jars.packages", pydeequ.deequ_maven_coord)
            .config("spark.jars.excludes", pydeequ.f2j_maven_coord)
            .getOrCreate()
        )
        spark.sparkContext.setLogLevel("ERROR")
        return spark

    def profile_csv(
        self,
        path: str | Path,
        *,
        dataset_id: str,
        dataset_name: str | None = None,
        uploaded_at: datetime | None = None,
        cfg: ProfileConfig | None = None,
    ) -> ProfileBundle:
        cfg = cfg or ProfileConfig()
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(str(p))

        uploaded_at = uploaded_at or datetime.now(timezone.utc)

        pydeequ, ColumnProfilerRunner, SparkSession, F, T = _import_deequ()
        spark = self._get_or_create_spark()

        df = (
            spark.read.option("header", "true")
            .option("inferSchema", "true")
            .csv(str(p))
        )

        row_count = int(df.count())
        columns = list(df.columns)

        profile_result = ColumnProfilerRunner(spark).onData(df).run()
        col_profiles = profile_result.profiles

        columns_meta: list[api.Column] = []
        inferred_types: dict[str, api.InferredType] = {}
        column_types: dict[str, api.ColumnType] = {}
        unique_counts: dict[str, int] = {}
        null_counts: dict[str, int] = {}

        for field in df.schema.fields:
            col = field.name
            inferred = _spark_type_to_inferred(field.dataType)
            inferred_types[col] = inferred

            prof = col_profiles.get(col)
            completeness = float(getattr(prof, "completeness", 0.0) or 0.0)
            approx_distinct = getattr(prof, "approximateNumDistinctValues", None)
            unique_count = int(round(float(approx_distinct))) if approx_distinct is not None else 0
            non_null_count = int(round(completeness * row_count)) if row_count else 0
            null_count = max(row_count - non_null_count, 0)

            unique_counts[col] = unique_count
            null_counts[col] = null_count

            col_type = _infer_column_type(
                inferred, unique_count=unique_count, non_null_count=non_null_count, cfg=cfg
            )
            column_types[col] = col_type

            columns_meta.append(
                api.Column(
                    name=col,
                    type=inferred,
                    inferred_type=col_type,
                    nullable=null_count > 0,
                )
            )

        dataset = api.Dataset(
            id=dataset_id,
            name=dataset_name or p.name,
            size=p.stat().st_size,
            row_count=row_count,
            column_count=len(columns),
            columns=columns_meta,
            uploaded_at=uploaded_at,
        )

        preview_rows = [
            {k: _json_safe(v) for k, v in r.asDict(recursive=True).items()}
            for r in df.limit(cfg.preview_limit).collect()
        ]
        preview = api.DatasetPreviewResponse(
            dataset_id=dataset_id,
            name=dataset.name,
            columns=[
                api.DatasetPreviewColumn(name=c.name, type=c.type, inferred_type=c.inferred_type)
                for c in columns_meta
            ],
            rows=preview_rows,
            total_rows=row_count,
        )

        column_stats: dict[str, api.ColumnStatsResponse] = {}
        total_cells = row_count * len(columns)
        total_nulls = sum(null_counts.values())

        for col in columns:
            inferred = inferred_types[col]
            col_type = column_types[col]
            null_count = null_counts[col]
            null_pct = null_count / row_count if row_count else 0.0
            unique_count = unique_counts[col]

            base_kwargs = dict(
                count=row_count,
                null_count=null_count,
                null_percentage=null_pct,
                unique_count=unique_count,
                constraint_ids=[],
            )

            c = F.col(col)

            if col_type == api.ColumnType.NUMERICAL:
                numeric = df.select(c.cast("double").alias(col)).where(c.isNotNull())
                agg = numeric.agg(
                    F.min(col).alias("min"),
                    F.max(col).alias("max"),
                    F.avg(col).alias("mean"),
                    F.stddev_samp(col).alias("stddev"),
                ).first()
                min_v = float(agg["min"]) if agg["min"] is not None else 0.0
                max_v = float(agg["max"]) if agg["max"] is not None else 0.0
                mean_v = float(agg["mean"]) if agg["mean"] is not None else 0.0
                std_v = float(agg["stddev"]) if agg["stddev"] is not None else 0.0

                try:
                    q1, median, q3 = df.approxQuantile(col, [0.25, 0.5, 0.75], 0.01)
                except Exception:
                    q1, median, q3 = 0.0, 0.0, 0.0

                # coarse histogram
                distribution: dict[str, int] = {}
                if row_count and min_v != max_v and cfg.numeric_buckets > 0:
                    width = (max_v - min_v) / cfg.numeric_buckets
                    if width > 0:
                        idx = F.floor((c.cast("double") - F.lit(min_v)) / F.lit(width))
                        bucketed = (
                            df.where(c.isNotNull())
                            .select(idx.alias("b"))
                            .groupBy("b")
                            .count()
                            .collect()
                        )
                        for r in bucketed:
                            b = int(r["b"])
                            b = max(0, min(b, cfg.numeric_buckets - 1))
                            lo = min_v + b * width
                            hi = min_v + (b + 1) * width
                            key = f"{lo:g}-{hi:g}"
                            distribution[key] = int(r["count"])
                elif row_count and min_v == max_v:
                    distribution[f"{min_v:g}-{max_v:g}"] = row_count - null_count

                # mode (best-effort)
                mode_v = None
                try:
                    mode_row = (
                        df.where(c.isNotNull())
                        .groupBy(col)
                        .count()
                        .orderBy(F.desc("count"))
                        .limit(1)
                        .collect()
                    )
                    if mode_row:
                        mode_v = float(mode_row[0][col])
                except Exception:
                    mode_v = None

                stats = api.NumericalColumnStats(
                    **base_kwargs,
                    min=min_v,
                    max=max_v,
                    mean=mean_v,
                    median=float(median),
                    mode=mode_v,
                    std_dev=std_v,
                    q1=float(q1),
                    q3=float(q3),
                    distribution=distribution,
                    outliers=[],
                )
                column_stats[col] = api.NumericalColumnStatsResponse(
                    dataset_id=dataset_id,
                    column_name=col,
                    type=inferred,
                    stats=stats,
                )
                continue

            if col_type == api.ColumnType.CATEGORICAL:
                dist_rows = (
                    df.groupBy(col)
                    .count()
                    .orderBy(F.desc("count"))
                    .limit(cfg.max_categories)
                    .collect()
                )
                distribution = {
                    str(r[col]): int(r["count"])
                    for r in dist_rows
                    if r[col] is not None and str(r[col]) != ""
                }
                unique_values = list(distribution.keys())
                stats = api.CategoricalColumnStats(
                    **base_kwargs,
                    unique_values=unique_values,
                    distribution=distribution,
                )
                column_stats[col] = api.CategoricalColumnStatsResponse(
                    dataset_id=dataset_id,
                    column_name=col,
                    type=inferred,
                    stats=stats,
                )
                continue

            # TEXTUAL
            lengths_df = df.where(c.isNotNull()).select(F.length(c).alias("len"), c.alias("v"))
            agg = lengths_df.agg(
                F.avg("len").alias("avg"),
                F.min("len").alias("min"),
                F.max("len").alias("max"),
            ).first()
            avg_len = float(agg["avg"]) if agg["avg"] is not None else 0.0
            min_len = int(agg["min"]) if agg["min"] is not None else 0
            max_len = int(agg["max"]) if agg["max"] is not None else 0

            length_dist_rows = lengths_df.groupBy("len").count().orderBy("len").collect()
            length_distribution = {str(r["len"]): int(r["count"]) for r in length_dist_rows}

            sample_rows = (
                df.where(c.isNotNull()).select(c.cast("string").alias("v")).distinct().limit(cfg.max_sample_values).collect()
            )
            sample_values = [str(r["v"]) for r in sample_rows if r["v"] is not None]

            stats = api.TextualColumnStats(
                **base_kwargs,
                avg_length=avg_len,
                min_length=min_len,
                max_length=max_len,
                length_distribution=length_distribution,
                sample_values=sample_values,
                pattern=None,
                completeness=1.0 - null_pct,
            )
            column_stats[col] = api.TextualColumnStatsResponse(
                dataset_id=dataset_id,
                column_name=col,
                type=inferred,
                stats=stats,
            )

        completeness = (total_cells - total_nulls) / total_cells if total_cells else 1.0
        validity = 1.0
        overall_health = (
            api.OverallHealth.HEALTHY
            if completeness >= 0.98
            else api.OverallHealth.WARNING
            if completeness >= 0.9
            else api.OverallHealth.ISSUES
        )

        quality = api.DatasetQualityResponse(
            dataset_id=dataset_id,
            metrics=api.DataQualityMetrics(
                completeness=completeness,
                validity=validity,
                constraint_count=0,
                active_constraints=0,
                disabled_constraints=0,
                violation_count=0,
                violations_by_constraint={},
                overall_health=overall_health,
            ),
        )

        return ProfileBundle(
            dataset=dataset,
            preview=preview,
            column_stats=column_stats,
            quality=quality,
        )

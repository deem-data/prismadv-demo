from __future__ import annotations

import math
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from prismadv.api.v1 import schemas as api
from prismadv.profiling.config import ProfileConfig
from prismadv.profiling.errors import MissingDependencyError
from prismadv.profiling.results import ProfileBundle


def _import_pandas():
    try:
        import pandas as pd  # type: ignore
    except Exception as e:  # pragma: no cover
        raise MissingDependencyError("Missing pandas dependency. Install with `uv sync --extra pandas`.") from e
    return pd


def _is_nan(v: Any) -> bool:
    try:
        return isinstance(v, float) and math.isnan(v)
    except Exception:
        return False


def _json_safe(v: Any) -> Any:
    if v is None or _is_nan(v):
        return None

    # numpy / pandas scalars
    try:
        import numpy as np  # type: ignore

        if isinstance(v, (np.integer, np.floating, np.bool_)):
            return v.item()
    except Exception:
        pass

    # pandas Timestamp, datetime/date
    if hasattr(v, "to_pydatetime"):
        try:
            return v.to_pydatetime().isoformat()
        except Exception:
            return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()

    return v


def _try_bool_str(s: str) -> bool | None:
    t = s.strip().lower()
    if t == "true":
        return True
    if t == "false":
        return False
    return None


def _try_date_str(s: str) -> date | None:
    t = s.strip()
    try:
        return date.fromisoformat(t)
    except Exception:
        return None


def _infer_type_for_series(pd, series) -> api.InferredType:
    if pd.api.types.is_bool_dtype(series.dtype):
        return api.InferredType.BOOLEAN
    if pd.api.types.is_integer_dtype(series.dtype):
        return api.InferredType.INTEGER
    if pd.api.types.is_float_dtype(series.dtype):
        return api.InferredType.FLOAT
    if pd.api.types.is_datetime64_any_dtype(series.dtype):
        return api.InferredType.DATE

    # object/string: attempt boolean/date
    non_null = series.dropna()
    if non_null.empty:
        return api.InferredType.STRING

    as_str = non_null.astype(str)
    bool_vals = [_try_bool_str(v) for v in as_str]
    if all(b is not None for b in bool_vals):
        return api.InferredType.BOOLEAN

    date_vals = [_try_date_str(v) for v in as_str]
    if all(d is not None for d in date_vals):
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


def _bucketize_numeric(vals: list[float], buckets: int) -> dict[str, int]:
    if not vals:
        return {}
    min_v = min(vals)
    max_v = max(vals)
    if buckets <= 1 or min_v == max_v:
        return {f"{min_v:g}-{max_v:g}": len(vals)}

    width = (max_v - min_v) / buckets
    if width <= 0:
        return {f"{min_v:g}-{max_v:g}": len(vals)}

    out: dict[str, int] = {}
    for v in vals:
        idx = min(int((v - min_v) / width), buckets - 1)
        lo = min_v + idx * width
        hi = min_v + (idx + 1) * width
        key = f"{lo:g}-{hi:g}"
        out[key] = out.get(key, 0) + 1
    return out


def _cast_value(v: Any, inferred_type: api.InferredType) -> Any:
    if v is None or _is_nan(v):
        return None
    if inferred_type == api.InferredType.BOOLEAN:
        if isinstance(v, bool):
            return v
        b = _try_bool_str(str(v))
        return b if b is not None else None
    if inferred_type == api.InferredType.INTEGER:
        try:
            return int(v)
        except Exception:
            return None
    if inferred_type == api.InferredType.FLOAT:
        try:
            return float(v)
        except Exception:
            return None
    # DATE and STRING are returned as-is; _json_safe handles Timestamp -> ISO string.
    return v


class PandasCSVProfiler:
    """
    Pandas-based CSV profiler.

    Produces API-aligned outputs for dataset preview, per-column stats, and dataset-level quality metrics.
    """

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

        pd = _import_pandas()

        df = pd.read_csv(p)
        row_count = int(len(df))
        columns = list(df.columns)

        inferred_types: dict[str, api.InferredType] = {}
        column_types: dict[str, api.ColumnType] = {}
        columns_meta: list[api.Column] = []
        null_counts: dict[str, int] = {}
        unique_counts: dict[str, int] = {}

        for col in columns:
            series = df[col]

            # Treat empty/whitespace strings as nulls for object columns
            if pd.api.types.is_object_dtype(series.dtype) or pd.api.types.is_string_dtype(series.dtype):
                s = series.astype("string")
                empty_mask = s.str.strip().eq("").fillna(False)
                series = series.mask(empty_mask, other=pd.NA)

            null_count = int(series.isna().sum())
            non_null = series.dropna()
            non_null_count = int(len(non_null))
            unique_count = int(non_null.nunique(dropna=True))

            null_counts[col] = null_count
            unique_counts[col] = unique_count

            inferred = _infer_type_for_series(pd, non_null)
            inferred_types[col] = inferred

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

        preview_df = df.head(cfg.preview_limit)
        preview_rows = []
        for row in preview_df.to_dict(orient="records"):
            casted = {
                k: _json_safe(_cast_value(v, inferred_types[k]))
                for k, v in row.items()
                if k in inferred_types
            }
            preview_rows.append(casted)

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
            series = df[col]
            if pd.api.types.is_object_dtype(series.dtype) or pd.api.types.is_string_dtype(series.dtype):
                s = series.astype("string")
                empty_mask = s.str.strip().eq("").fillna(False)
                series = series.mask(empty_mask, other=pd.NA)

            null_count = null_counts[col]
            null_pct = null_count / row_count if row_count else 0.0
            unique_count = unique_counts[col]
            inferred = inferred_types[col]
            col_type = column_types[col]

            base_kwargs = dict(
                count=row_count,
                null_count=null_count,
                null_percentage=null_pct,
                unique_count=unique_count,
                constraint_ids=[],
            )

            non_null = series.dropna()

            if col_type == api.ColumnType.NUMERICAL:
                numeric = pd.to_numeric(non_null, errors="coerce").dropna()
                values = [float(x) for x in numeric.tolist()]
                values.sort()
                if values:
                    mean = float(pd.Series(values).mean())
                    std = float(pd.Series(values).std(ddof=1)) if len(values) >= 2 else 0.0
                    q1 = float(pd.Series(values).quantile(0.25))
                    median = float(pd.Series(values).quantile(0.5))
                    q3 = float(pd.Series(values).quantile(0.75))
                    mode_series = pd.Series(values).mode()
                    mode = float(mode_series.iloc[0]) if not mode_series.empty else None
                    min_v = float(values[0])
                    max_v = float(values[-1])
                else:
                    mean = std = q1 = median = q3 = min_v = max_v = 0.0
                    mode = None

                stats = api.NumericalColumnStats(
                    **base_kwargs,
                    min=min_v,
                    max=max_v,
                    mean=mean,
                    median=median,
                    mode=mode,
                    std_dev=std,
                    q1=q1,
                    q3=q3,
                    distribution=_bucketize_numeric(values, cfg.numeric_buckets),
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
                vc = non_null.astype(str).value_counts().head(cfg.max_categories)
                distribution = {str(k): int(v) for k, v in vc.to_dict().items()}
                stats = api.CategoricalColumnStats(
                    **base_kwargs,
                    unique_values=list(distribution.keys()),
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
            as_str = non_null.astype(str)
            lengths = as_str.str.len()
            length_distribution = {str(k): int(v) for k, v in lengths.value_counts().sort_index().to_dict().items()}
            sample_values = list(dict.fromkeys(as_str.tolist()))[: cfg.max_sample_values]
            stats = api.TextualColumnStats(
                **base_kwargs,
                avg_length=float(lengths.mean()) if not lengths.empty else 0.0,
                min_length=int(lengths.min()) if not lengths.empty else 0,
                max_length=int(lengths.max()) if not lengths.empty else 0,
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
                completeness=float(completeness),
                validity=float(validity),
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

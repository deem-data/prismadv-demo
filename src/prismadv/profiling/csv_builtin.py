from __future__ import annotations

import csv
import math
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from prismadv.api.v1 import schemas as api
from prismadv.api.v1.schemas import HEALTH_COMPLETENESS_HEALTHY, HEALTH_COMPLETENESS_WARNING
from prismadv.profiling.config import ProfileConfig
from prismadv.profiling.results import ProfileBundle


def _is_null(v: object) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    return False


def _try_int(s: str) -> int | None:
    try:
        if s.strip() == "":
            return None
        # Disallow floats written as "1.0"
        if any(ch in s for ch in [".", "e", "E"]):
            return None
        return int(s)
    except Exception:
        return None


def _try_float(s: str) -> float | None:
    try:
        if s.strip() == "":
            return None
        return float(s)
    except Exception:
        return None


def _try_bool(s: str) -> bool | None:
    t = s.strip().lower()
    if t in {"true", "false"}:
        return t == "true"
    return None


def _try_date(s: str) -> date | None:
    t = s.strip()
    try:
        return date.fromisoformat(t)
    except Exception:
        return None


def _quantile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return float("nan")
    if q <= 0:
        return float(sorted_vals[0])
    if q >= 1:
        return float(sorted_vals[-1])
    n = len(sorted_vals)
    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(sorted_vals[lo])
    frac = pos - lo
    return float(sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac)


def _mean(vals: Iterable[float]) -> float:
    total = 0.0
    count = 0
    for v in vals:
        total += v
        count += 1
    return total / count if count else float("nan")


def _std_dev(vals: list[float], mean: float) -> float:
    if len(vals) < 2:
        return 0.0
    var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
    return math.sqrt(var)


def _bucketize_numeric(vals: list[float], buckets: int) -> dict[str, int]:
    if not vals:
        return {}
    min_v = min(vals)
    max_v = max(vals)
    if buckets <= 1 or min_v == max_v:
        return {f"{min_v:g}-{max_v:g}": len(vals)}

    width = (max_v - min_v) / buckets
    out: dict[str, int] = {}
    for v in vals:
        idx = min(int((v - min_v) / width), buckets - 1)
        lo = min_v + idx * width
        hi = min_v + (idx + 1) * width
        key = f"{lo:g}-{hi:g}"
        out[key] = out.get(key, 0) + 1
    return out


def _infer_type(non_null: list[str]) -> api.InferredType:
    if not non_null:
        return api.InferredType.STRING

    ints = [_try_int(v) for v in non_null]
    if all(x is not None for x in ints):
        return api.InferredType.INTEGER

    floats = [_try_float(v) for v in non_null]
    if all(x is not None for x in floats):
        return api.InferredType.FLOAT

    bools = [_try_bool(v) for v in non_null]
    if all(x is not None for x in bools):
        return api.InferredType.BOOLEAN

    dates = [_try_date(v) for v in non_null]
    if all(x is not None for x in dates):
        return api.InferredType.DATE

    return api.InferredType.STRING


def _infer_column_type(
    inferred_type: api.InferredType,
    unique_count: int,
    non_null_count: int,
    cfg: ProfileConfig,
) -> api.ColumnType:
    if inferred_type in {api.InferredType.INTEGER, api.InferredType.FLOAT}:
        return api.ColumnType.NUMERICAL
    if inferred_type in {api.InferredType.BOOLEAN}:
        return api.ColumnType.CATEGORICAL

    # date or string: decide categorical vs textual based on cardinality
    if non_null_count == 0:
        return api.ColumnType.TEXTUAL

    ratio = unique_count / non_null_count
    if unique_count <= cfg.max_categories and ratio <= cfg.categorical_ratio_threshold:
        return api.ColumnType.CATEGORICAL
    return api.ColumnType.TEXTUAL


def _cast_value(raw: str, inferred_type: api.InferredType) -> Any:
    if _is_null(raw):
        return None
    s = str(raw).strip()
    if inferred_type == api.InferredType.INTEGER:
        return int(s)
    if inferred_type == api.InferredType.FLOAT:
        return float(s)
    if inferred_type == api.InferredType.BOOLEAN:
        return s.lower() == "true"
    if inferred_type == api.InferredType.DATE:
        # Keep ISO string for transport
        return s
    return s


@dataclass
class _ColumnRaw:
    values: list[Optional[str]]

    @property
    def non_null(self) -> list[str]:
        return [v for v in self.values if not _is_null(v)]

    @property
    def null_count(self) -> int:
        return sum(1 for v in self.values if _is_null(v))

    @property
    def count(self) -> int:
        return len(self.values)


class BuiltinCSVProfiler:
    """
    A dependency-free CSV profiler.

    This backend exists to keep core profiling testable without optional deps.
    Production deployments should prefer `deequ` (default) or other engines.
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
        uploaded_at = uploaded_at or datetime.now(timezone.utc)

        with p.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise ValueError("CSV has no header row")
            columns = list(reader.fieldnames)

            raws: dict[str, _ColumnRaw] = {c: _ColumnRaw([]) for c in columns}
            preview_raw_rows: list[dict[str, Optional[str]]] = []

            for row in reader:
                if len(preview_raw_rows) < cfg.preview_limit:
                    preview_raw_rows.append({k: row.get(k) for k in columns})
                for c in columns:
                    raws[c].values.append(row.get(c))

        row_count = raws[columns[0]].count if columns else 0

        # Infer types & build column metadata
        inferred_types: dict[str, api.InferredType] = {}
        column_types: dict[str, api.ColumnType] = {}
        columns_meta: list[api.Column] = []

        for col in columns:
            non_null = raws[col].non_null
            inferred = _infer_type(non_null)
            inferred_types[col] = inferred
            unique_count = len(set(non_null))
            col_type = _infer_column_type(inferred, unique_count, len(non_null), cfg)
            column_types[col] = col_type
            columns_meta.append(
                api.Column(
                    name=col,
                    type=inferred,
                    inferred_type=col_type,
                    nullable=raws[col].null_count > 0,
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

        preview_rows: list[dict[str, Any]] = []
        for raw_row in preview_raw_rows:
            typed = {
                col: _cast_value(raw_row.get(col), inferred_types[col]) for col in columns
            }
            preview_rows.append(typed)

        preview = api.DatasetPreviewResponse(
            dataset_id=dataset_id,
            name=dataset.name,
            columns=[
                api.DatasetPreviewColumn(
                    name=c.name,
                    type=c.type,
                    inferred_type=c.inferred_type,
                )
                for c in columns_meta
            ],
            rows=preview_rows,
            total_rows=row_count,
        )

        # Column stats
        column_stats: dict[str, api.ColumnStatsResponse] = {}
        total_cells = row_count * len(columns)
        total_nulls = 0

        for col in columns:
            raw = raws[col]
            non_null = raw.non_null
            null_count = raw.null_count
            total_nulls += null_count
            null_pct = null_count / raw.count if raw.count else 0.0
            unique_count = len(set(non_null))
            base_kwargs = dict(
                count=raw.count,
                null_count=null_count,
                null_percentage=null_pct,
                unique_count=unique_count,
                constraint_ids=[],
            )

            inferred = inferred_types[col]
            col_type = column_types[col]

            if col_type == api.ColumnType.TEXTUAL:
                lengths = [len(v) for v in non_null]
                stats = api.TextualColumnStats(
                    **base_kwargs,
                    avg_length=_mean([float(x) for x in lengths]) if lengths else 0.0,
                    min_length=min(lengths) if lengths else 0,
                    max_length=max(lengths) if lengths else 0,
                    length_distribution=dict(Counter(str(x) for x in lengths)),
                    sample_values=list(dict.fromkeys(non_null))[: cfg.max_sample_values],
                    pattern=None,
                    completeness=1.0 - null_pct,
                )
                column_stats[col] = api.TextualColumnStatsResponse(
                    dataset_id=dataset_id,
                    column_name=col,
                    type=inferred,
                    stats=stats,
                )
                continue

            if col_type == api.ColumnType.CATEGORICAL:
                values = non_null
                dist = Counter(values)
                unique_values = list(dist.keys())[: cfg.max_categories]
                stats = api.CategoricalColumnStats(
                    **base_kwargs,
                    unique_values=unique_values,
                    distribution={k: int(v) for k, v in dist.items()},
                )
                column_stats[col] = api.CategoricalColumnStatsResponse(
                    dataset_id=dataset_id,
                    column_name=col,
                    type=inferred,
                    stats=stats,
                )
                continue

            # Numerical
            parsed: list[float] = []
            for v in non_null:
                fv = _try_float(v)
                if fv is not None and not math.isnan(fv):
                    parsed.append(float(fv))
            parsed.sort()
            mean = _mean(parsed) if parsed else 0.0
            mode = None
            if parsed:
                c = Counter(parsed)
                mode = max(c.items(), key=lambda kv: kv[1])[0]

            stats = api.NumericalColumnStats(
                **base_kwargs,
                min=min(parsed) if parsed else 0.0,
                max=max(parsed) if parsed else 0.0,
                mean=mean,
                median=_quantile(parsed, 0.5) if parsed else 0.0,
                mode=mode,
                std_dev=_std_dev(parsed, mean) if parsed else 0.0,
                q1=_quantile(parsed, 0.25) if parsed else 0.0,
                q3=_quantile(parsed, 0.75) if parsed else 0.0,
                distribution=_bucketize_numeric(parsed, cfg.numeric_buckets),
                outliers=[],
            )
            column_stats[col] = api.NumericalColumnStatsResponse(
                dataset_id=dataset_id,
                column_name=col,
                type=inferred,
                stats=stats,
            )

        completeness = (total_cells - total_nulls) / total_cells if total_cells else 1.0
        validity = 1.0
        overall_health = (
            api.OverallHealth.HEALTHY
            if completeness >= HEALTH_COMPLETENESS_HEALTHY
            else api.OverallHealth.WARNING
            if completeness >= HEALTH_COMPLETENESS_WARNING
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
            dataset=dataset, preview=preview, column_stats=column_stats, quality=quality
        )


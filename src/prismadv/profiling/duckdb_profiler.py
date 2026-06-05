from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from prismadv.api.v1 import schemas as api
from prismadv.profiling.config import ProfileConfig
from prismadv.profiling.errors import MissingDependencyError
from prismadv.profiling.results import ProfileBundle


def _import_duckdb():
    try:
        import duckdb  # type: ignore
    except Exception as e:  # pragma: no cover
        raise MissingDependencyError("Missing duckdb dependency. Install with `uv sync --extra duckdb`.") from e
    return duckdb


def _quote_ident(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'


def _quote_literal(v: str) -> str:
    return "'" + v.replace("'", "''") + "'"


def _json_safe(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def _cast_value(v: Any, inferred_type: api.InferredType) -> Any:
    if v is None:
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    if inferred_type == api.InferredType.BOOLEAN:
        if isinstance(v, bool):
            return v
        t = str(v).strip().lower()
        if t == "true":
            return True
        if t == "false":
            return False
        return None
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
    if inferred_type == api.InferredType.DATE:
        if isinstance(v, (datetime, date)):
            return v.isoformat()
        return str(v).strip()
    return v


def _duckdb_type_to_inferred(type_str: str) -> api.InferredType:
    t = type_str.strip().upper()
    if any(
        x in t
        for x in [
            "INT",
            "HUGEINT",
            "UBIGINT",
            "USMALLINT",
            "UTINYINT",
            "INTEGER",
            "BIGINT",
            "SMALLINT",
            "TINYINT",
        ]
    ):
        return api.InferredType.INTEGER
    if any(x in t for x in ["DOUBLE", "FLOAT", "REAL", "DECIMAL", "NUMERIC"]):
        return api.InferredType.FLOAT
    if "BOOL" in t:
        return api.InferredType.BOOLEAN
    if any(x in t for x in ["DATE", "TIMESTAMP", "TIME"]):
        return api.InferredType.DATE
    return api.InferredType.STRING


def _refine_inferred_type_for_string_column(
    *,
    con,
    table: str,
    nonnull_expr: str,
    non_null_count: int,
) -> api.InferredType:
    if non_null_count == 0:
        return api.InferredType.STRING

    row = con.execute(
        f"""
        SELECT
          COUNT(TRY_CAST({nonnull_expr} AS BIGINT))  AS int_ok,
          COUNT(TRY_CAST({nonnull_expr} AS DOUBLE))  AS float_ok,
          COUNT(TRY_CAST({nonnull_expr} AS BOOLEAN)) AS bool_ok,
          COUNT(TRY_CAST({nonnull_expr} AS DATE))    AS date_ok
        FROM {table}
        WHERE {nonnull_expr} IS NOT NULL
        """
    ).fetchone()
    int_ok, float_ok, bool_ok, date_ok = (int(row[0]), int(row[1]), int(row[2]), int(row[3]))

    if int_ok == non_null_count:
        return api.InferredType.INTEGER
    if float_ok == non_null_count:
        return api.InferredType.FLOAT
    if bool_ok == non_null_count:
        return api.InferredType.BOOLEAN
    if date_ok == non_null_count:
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


def _bucketize_numeric(
    *,
    con,
    table: str,
    value_expr: str,
    min_v: float,
    max_v: float,
    buckets: int,
) -> dict[str, int]:
    if buckets <= 0:
        return {}

    nn = int(con.execute(f"SELECT COUNT(({value_expr})) FROM {table}").fetchone()[0])
    if nn <= 0:
        return {}

    if min_v == max_v:
        return {f"{min_v:g}-{max_v:g}": nn}

    width = (max_v - min_v) / buckets
    if width <= 0:
        return {f"{min_v:g}-{max_v:g}": nn}

    v = f"({value_expr})"
    # floor((x - min)/width), clamped to [0, buckets-1]
    idx_expr = f"""
        LEAST(
            GREATEST(
                CAST(FLOOR((CAST({v} AS DOUBLE) - {min_v}) / {width}) AS INTEGER),
                0
            ),
            {buckets - 1}
        )
    """.strip()
    rows = con.execute(
        f"SELECT {idx_expr} AS b, COUNT(*) AS c FROM {table} WHERE {v} IS NOT NULL GROUP BY 1"
    ).fetchall()

    out: dict[str, int] = {}
    for b, c in rows:
        b_int = int(b)
        lo = min_v + b_int * width
        hi = min_v + (b_int + 1) * width
        out[f"{lo:g}-{hi:g}"] = int(c)
    return out


class DuckDBCSVProfiler:
    """
    DuckDB-based CSV profiler.

    Produces API-aligned outputs for dataset preview, per-column stats, and dataset-level quality metrics.
    """

    def __init__(self):
        self._duckdb = _import_duckdb()

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

        duckdb = self._duckdb
        con = duckdb.connect(database=":memory:")

        table = "t"
        con.execute(
            f"CREATE VIEW {table} AS SELECT * FROM read_csv_auto({_quote_literal(str(p))}, header=true)"
        )

        row_count = int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

        # DESCRIBE returns: column_name, column_type, null, key, default, extra
        desc_rows = con.execute(f"DESCRIBE {table}").fetchall()
        col_types: dict[str, str] = {r[0]: r[1] for r in desc_rows}
        columns = list(col_types.keys())

        inferred_types: dict[str, api.InferredType] = {}
        column_types: dict[str, api.ColumnType] = {}
        columns_meta: list[api.Column] = []
        storage_is_string: dict[str, bool] = {}
        null_counts: dict[str, int] = {}
        unique_counts: dict[str, int] = {}
        non_null_counts: dict[str, int] = {}

        for col in columns:
            storage_inferred = _duckdb_type_to_inferred(col_types[col])
            is_storage_string = storage_inferred == api.InferredType.STRING
            storage_is_string[col] = is_storage_string

            col_q = _quote_ident(col)
            if is_storage_string:
                nonnull_expr = f"NULLIF(TRIM(CAST({col_q} AS VARCHAR)), '')"
            else:
                nonnull_expr = col_q

            non_null_count = int(
                con.execute(f"SELECT COUNT({nonnull_expr}) FROM {table}").fetchone()[0]
            )
            null_count = max(row_count - non_null_count, 0)
            unique_count = int(
                con.execute(f"SELECT COUNT(DISTINCT {nonnull_expr}) FROM {table}").fetchone()[0]
            )

            non_null_counts[col] = non_null_count
            null_counts[col] = null_count
            unique_counts[col] = unique_count

            inferred = storage_inferred
            if is_storage_string:
                inferred = _refine_inferred_type_for_string_column(
                    con=con,
                    table=table,
                    nonnull_expr=nonnull_expr,
                    non_null_count=non_null_count,
                )
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

        cur = con.execute(f"SELECT * FROM {table} LIMIT {cfg.preview_limit}")
        preview_cols = [d[0] for d in (cur.description or [])]
        preview_rows = [
            {
                preview_cols[i]: _json_safe(
                    _cast_value(v, inferred_types.get(preview_cols[i], api.InferredType.STRING))
                )
                for i, v in enumerate(row)
            }
            for row in cur.fetchall()
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

            col_q = _quote_ident(col)
            if storage_is_string.get(col, False):
                nonnull_expr = f"NULLIF(TRIM(CAST({col_q} AS VARCHAR)), '')"
            else:
                nonnull_expr = col_q

            if col_type == api.ColumnType.NUMERICAL:
                value_expr = (
                    f"TRY_CAST({nonnull_expr} AS DOUBLE)"
                    if storage_is_string.get(col, False)
                    else f"CAST({col_q} AS DOUBLE)"
                )
                agg = con.execute(
                    f"""
                    SELECT
                      MIN({value_expr}) AS min,
                      MAX({value_expr}) AS max,
                      AVG({value_expr}) AS mean,
                      STDDEV_SAMP({value_expr}) AS std,
                      QUANTILE_CONT({value_expr}, 0.25) AS q1,
                      QUANTILE_CONT({value_expr}, 0.5) AS median,
                      QUANTILE_CONT({value_expr}, 0.75) AS q3
                    FROM {table}
                    WHERE {value_expr} IS NOT NULL
                    """
                ).fetchone()

                min_v = float(_json_safe(agg[0]) or 0.0)
                max_v = float(_json_safe(agg[1]) or 0.0)
                mean_v = float(_json_safe(agg[2]) or 0.0)
                std_v = float(_json_safe(agg[3]) or 0.0)
                q1 = float(_json_safe(agg[4]) or 0.0)
                median = float(_json_safe(agg[5]) or 0.0)
                q3 = float(_json_safe(agg[6]) or 0.0)

                mode_v = None
                try:
                    mode_row = con.execute(
                        f"""
                        SELECT v, COUNT(*) AS c
                        FROM (
                          SELECT {value_expr} AS v
                          FROM {table}
                        ) s
                        WHERE v IS NOT NULL
                        GROUP BY 1
                        ORDER BY c DESC
                        LIMIT 1
                        """
                    ).fetchone()
                    if mode_row:
                        mode_v = float(mode_row[0])
                except Exception:
                    mode_v = None

                distribution = _bucketize_numeric(
                    con=con,
                    table=table,
                    value_expr=value_expr,
                    min_v=min_v,
                    max_v=max_v,
                    buckets=cfg.numeric_buckets,
                )

                stats = api.NumericalColumnStats(
                    **base_kwargs,
                    min=min_v,
                    max=max_v,
                    mean=mean_v,
                    median=median,
                    mode=mode_v,
                    std_dev=std_v,
                    q1=q1,
                    q3=q3,
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
                dist_rows = con.execute(
                    f"""
                    SELECT CAST({nonnull_expr} AS VARCHAR) AS v, COUNT(*) AS c
                    FROM {table}
                    WHERE {nonnull_expr} IS NOT NULL
                    GROUP BY 1
                    ORDER BY c DESC
                    LIMIT {cfg.max_categories}
                    """
                ).fetchall()
                distribution = {str(v): int(c) for v, c in dist_rows}
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
            len_expr = f"LENGTH(CAST({nonnull_expr} AS VARCHAR))"
            agg = con.execute(
                f"""
                SELECT
                  AVG({len_expr}) AS avg,
                  MIN({len_expr}) AS min,
                  MAX({len_expr}) AS max
                FROM {table}
                WHERE {nonnull_expr} IS NOT NULL
                """
            ).fetchone()
            avg_len = float(_json_safe(agg[0]) or 0.0)
            min_len = int(_json_safe(agg[1]) or 0)
            max_len = int(_json_safe(agg[2]) or 0)

            len_dist_rows = con.execute(
                f"""
                SELECT {len_expr} AS len, COUNT(*) AS c
                FROM {table}
                WHERE {nonnull_expr} IS NOT NULL
                GROUP BY 1
                ORDER BY 1
                """
            ).fetchall()
            length_distribution = {str(int(l)): int(c) for l, c in len_dist_rows if l is not None}

            sample_rows = con.execute(
                f"""
                SELECT DISTINCT CAST({nonnull_expr} AS VARCHAR) AS v
                FROM {table}
                WHERE {nonnull_expr} IS NOT NULL
                LIMIT {cfg.max_sample_values}
                """
            ).fetchall()
            sample_values = [str(r[0]) for r in sample_rows if r and r[0] is not None]

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

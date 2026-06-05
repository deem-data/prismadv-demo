from __future__ import annotations

from enum import StrEnum

from prismadv.profiling.csv_builtin import BuiltinCSVProfiler
from prismadv.profiling.errors import MissingDependencyError


class ProfilerBackend(StrEnum):
    DEEQU = "deequ"
    PANDAS = "pandas"
    POLARS = "polars"
    DUCKDB = "duckdb"
    BUILTIN = "builtin"


def get_profiler(backend: ProfilerBackend):
    if backend == ProfilerBackend.BUILTIN:
        return BuiltinCSVProfiler()

    if backend == ProfilerBackend.DEEQU:
        try:
            from prismadv.profiling.deequ_profiler import DeequCSVProfiler
        except Exception as e:  # pragma: no cover
            raise MissingDependencyError(
                "Deequ profiler dependencies are missing. Install with `uv sync --extra deequ`."
            ) from e
        return DeequCSVProfiler()

    if backend == ProfilerBackend.PANDAS:
        try:
            from prismadv.profiling.pandas_profiler import PandasCSVProfiler
        except Exception as e:  # pragma: no cover
            raise MissingDependencyError(
                "Pandas profiler dependencies are missing. Install with `uv sync --extra pandas`."
            ) from e
        return PandasCSVProfiler()
    if backend == ProfilerBackend.POLARS:
        raise MissingDependencyError("Polars profiler not implemented yet.")
    if backend == ProfilerBackend.DUCKDB:
        try:
            from prismadv.profiling.duckdb_profiler import DuckDBCSVProfiler
        except Exception as e:  # pragma: no cover
            raise MissingDependencyError(
                "DuckDB profiler dependencies are missing. Install with `uv sync --extra duckdb`."
            ) from e
        return DuckDBCSVProfiler()

    raise ValueError(f"Unknown profiler backend: {backend}")

from __future__ import annotations

from typing import TYPE_CHECKING

from prismadv.profiling.config import ProfileConfig
from prismadv.profiling.csv_builtin import BuiltinCSVProfiler
from prismadv.profiling.errors import MissingDependencyError
from prismadv.profiling.registry import ProfilerBackend, get_profiler
from prismadv.profiling.results import ProfileBundle

if TYPE_CHECKING:
    from prismadv.profiling.deequ_profiler import DeequCSVProfiler
    from prismadv.profiling.duckdb_profiler import DuckDBCSVProfiler
    from prismadv.profiling.pandas_profiler import PandasCSVProfiler

__all__ = [
    "BuiltinCSVProfiler",
    "DeequCSVProfiler",
    "DuckDBCSVProfiler",
    "PandasCSVProfiler",
    "ProfileBundle",
    "ProfileConfig",
    "ProfilerBackend",
    "get_profiler",
]


def __getattr__(name: str):
    if name == "DeequCSVProfiler":
        try:
            from prismadv.profiling.deequ_profiler import DeequCSVProfiler as cls
        except Exception as e:  # pragma: no cover
            raise MissingDependencyError(
                "Deequ profiler dependencies are missing. Install with `uv sync --extra deequ`."
            ) from e
        return cls

    if name == "PandasCSVProfiler":
        try:
            from prismadv.profiling.pandas_profiler import PandasCSVProfiler as cls
        except Exception as e:  # pragma: no cover
            raise MissingDependencyError(
                "Pandas profiler dependencies are missing. Install with `uv sync --extra pandas`."
            ) from e
        return cls

    if name == "DuckDBCSVProfiler":
        try:
            from prismadv.profiling.duckdb_profiler import DuckDBCSVProfiler as cls
        except Exception as e:  # pragma: no cover
            raise MissingDependencyError(
                "DuckDB profiler dependencies are missing. Install with `uv sync --extra duckdb`."
            ) from e
        return cls

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

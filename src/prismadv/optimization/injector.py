"""Error injection engine for the GEPA optimization module.

Ported from code/prismadv/error_injection/ so the demo optimization module
has no dependency on the research codebase.

Supports the YAML error-config format used in benchmarks/EIDBench/{dataset}/errors/.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base class (mirrors code/prismadv/error_injection/abstract_corruption.py)
# ---------------------------------------------------------------------------

class TabularCorruption(ABC):
    def __init__(self, columns=None, severity=None, sampling=None, **kwargs):
        self.columns = columns
        self.severity = 1.0 if severity is None else severity
        self.sampling = "CAR" if sampling is None else sampling

    @abstractmethod
    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        pass

    def sample_rows(self, data: pd.DataFrame):
        if self.severity >= 1.0:
            return data.index
        if self.sampling.endswith("CAR"):
            return np.random.permutation(data.index)[: int(len(data) * self.severity)]
        if self.sampling.endswith("NAR"):
            n = int(len(data) * min(self.severity, 1.0))
            start = np.random.randint(0, max(len(data) - n, 1))
            idx = range(start, start + n)
            return data[self.columns[0] if isinstance(self.columns, list) else self.columns].sort_values().iloc[idx].index
        if self.sampling.endswith("AR"):
            n = int(len(data) * min(self.severity, 1.0))
            start = np.random.randint(0, max(len(data) - n, 1))
            idx = range(start, start + n)
            depends = np.random.choice(
                list(set(data.columns) - {self.columns if isinstance(self.columns, str) else self.columns[0]})
            )
            return data[depends].sort_values().iloc[idx].index
        raise ValueError(f"Unknown sampling type: {self.sampling!r}")


# ---------------------------------------------------------------------------
# Operator implementations
# ---------------------------------------------------------------------------

class GaussianNoise(TabularCorruption):
    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        df = dataframe.copy(deep=True)
        cols = self.columns if isinstance(self.columns, list) else [self.columns]
        for col in cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                continue
            std = np.std(df[col])
            if std == 0 or np.isnan(std) or np.isinf(std):
                continue
            if self.severity <= 0:
                continue
            rows = self.sample_rows(df)
            if len(rows) == 0:
                continue
            scale = np.random.uniform(1, 5)
            noise = np.random.normal(0, scale * std, size=len(rows))
            if df[col].dtype == np.dtype("int64"):
                noise = noise.astype(int)
            df.loc[rows, col] += noise
        return df


class MaskValues(TabularCorruption):
    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        df = dataframe.copy(deep=True)
        cols = self.columns if isinstance(self.columns, list) else [self.columns]
        for col in cols:
            mask_value = None if pd.api.types.is_integer_dtype(df[col]) else np.random.choice(["?", "NA", "missing"])
            rows = self.sample_rows(df)
            df.loc[rows, col] = mask_value
        return df


class ColumnDropping(TabularCorruption):
    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        df = dataframe.copy(deep=True)
        cols = self.columns if isinstance(self.columns, list) else [self.columns]
        existing = [c for c in cols if c in df.columns]
        if existing:
            df.drop(columns=existing, inplace=True)
        return df


class ColumnInserting(TabularCorruption):
    def __init__(self, columns=None, severity=1.0, corrupt_strategy: str = "add_prefix", **kwargs):
        super().__init__(columns, severity=severity, **kwargs)
        self.corrupt_strategy = corrupt_strategy

    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        df = dataframe.copy(deep=True)
        cols = self.columns if isinstance(self.columns, list) else [self.columns]
        for col in cols:
            if col not in df.columns:
                continue
            if self.corrupt_strategy == "add_prefix":
                prefix = "corrupted_"
                df[prefix + col] = df[col].apply(lambda x: f"{prefix}{x}" if pd.notna(x) else x)
            elif self.corrupt_strategy == "sanitize_to_identifier":
                df[col + "_sanitized"] = df[col].apply(
                    lambda x: re.sub(r"\W|^(?=\d)", "_", str(x)) if pd.notna(x) else x
                )
            # 'concatenate' requires 2 columns; skip in single-column loop
        return df


class MissingCategoricalValueCorruption(TabularCorruption):
    def __init__(self, columns=None, severity: float = 0.1, corrupt_strategy: str = "to_nan",
                 max_unique_num: int = 30, **kwargs):
        super().__init__(columns, **kwargs)
        self.severity = severity
        self.corrupt_strategy = corrupt_strategy
        self.max_unique_num = max_unique_num

    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        df = dataframe.copy()
        cols = self.columns if isinstance(self.columns, list) else [self.columns]
        for col in cols:
            if col not in df.columns:
                continue
            df = self._corrupt_column(df, col)
        return df

    def _corrupt_column(self, df: pd.DataFrame, col: str) -> pd.DataFrame:
        value_counts = df[col].value_counts()
        total_to_remove = int(self.severity * len(df))
        sorted_cats = value_counts.sort_values(ascending=True).index
        to_remove: list = []
        removed = 0
        for cat in sorted_cats:
            cnt = value_counts[cat]
            if removed + cnt > total_to_remove and len(to_remove) > 0:
                break
            to_remove.append(cat)
            removed += cnt
        mask = df[col].isin(to_remove)
        if self.corrupt_strategy == "to_nan":
            df[col] = df[col].astype("object")
            df.loc[mask, col] = np.nan
        elif self.corrupt_strategy == "to_majority":
            df[col] = df[col].astype("object")
            majority = df[col].mode().values[0]
            df.loc[mask, col] = majority
        elif self.corrupt_strategy == "to_random":
            df[col] = df[col].astype("object")
            others = list(set(df[col].dropna().unique()) - set(to_remove)) or list(to_remove)
            df.loc[mask, col] = np.random.choice(others, mask.sum())
        elif self.corrupt_strategy == "remove":
            df = df[~mask]
        return df


class RangeViolation(TabularCorruption):
    def __init__(self, columns=None, severity=None, sampling=None,
                 min_value=None, max_value=None, strategy: str = "random",
                 violation_factor: float = 1.5, **kwargs):
        super().__init__(columns, severity=severity, sampling=sampling, **kwargs)
        self.min_value = min_value
        self.max_value = max_value
        self.strategy = strategy
        self.violation_factor = violation_factor

    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        if not self.columns:
            return dataframe
        df = dataframe.copy(deep=True)
        rows = self.sample_rows(df)
        cols = self.columns if isinstance(self.columns, list) else [self.columns]
        for col in cols:
            if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
                continue
            col_min = self.min_value if self.min_value is not None else df[col].min()
            col_max = self.max_value if self.max_value is not None else df[col].max()
            span = col_max - col_min or abs(col_max) or 1
            for idx in rows:
                side = "below" if (self.strategy == "below_min" or
                                   (self.strategy == "random" and np.random.random() < 0.5)) else "above"
                amt = span * self.violation_factor * np.random.uniform(0.1, 1.0)
                df.loc[idx, col] = col_min - amt if side == "below" else col_max + amt
        return df


class OutlierInjection(TabularCorruption):
    def __init__(self, columns=None, severity=None, sampling=None,
                 strategy: str = "iqr_based", factor: float = 3.0, **kwargs):
        super().__init__(columns, severity=severity, sampling=sampling, **kwargs)
        self.strategy = strategy
        self.factor = factor

    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        if not self.columns:
            return dataframe
        df = dataframe.copy(deep=True)
        rows = self.sample_rows(df)
        cols = self.columns if isinstance(self.columns, list) else [self.columns]
        for col in cols:
            if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
                continue
            q1, q3 = df[col].quantile([0.25, 0.75])
            iqr = q3 - q1 or 1
            upper = q3 + self.factor * iqr
            lower = q1 - self.factor * iqr
            for idx in rows:
                df.loc[idx, col] = upper if np.random.random() < 0.5 else lower
        return df


class StringNoise(TabularCorruption):
    def __init__(self, columns=None, severity=None, sampling=None,
                 noise_level: float = 0.2, **kwargs):
        super().__init__(columns, severity=severity, sampling=sampling, **kwargs)
        self.noise_level = noise_level

    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        df = dataframe.copy(deep=True)
        cols = self.columns if isinstance(self.columns, list) else [self.columns]
        for col in cols:
            if col not in df.columns:
                continue
            rows = self.sample_rows(df)
            df.loc[rows, col] = df.loc[rows, col].apply(self._add_noise)
        return df

    def _add_noise(self, val):
        if pd.isna(val):
            return val
        s = str(val)
        if not s:
            return s
        n_chars = max(1, int(len(s) * self.noise_level))
        positions = np.random.choice(len(s), size=min(n_chars, len(s)), replace=False)
        lst = list(s)
        for p in positions:
            lst[p] = np.random.choice(list("abcdefghijklmnopqrstuvwxyz0123456789!@#"))
        return "".join(lst)


class Scaling(TabularCorruption):
    def __init__(self, columns=None, severity=None, sampling=None,
                 factor: float = 10.0, **kwargs):
        super().__init__(columns, severity=severity, sampling=sampling, **kwargs)
        self.factor = factor

    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        df = dataframe.copy(deep=True)
        cols = self.columns if isinstance(self.columns, list) else [self.columns]
        for col in cols:
            if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
                continue
            rows = self.sample_rows(df)
            df.loc[rows, col] = df.loc[rows, col] * self.factor
        return df


class DuplicatedRows(TabularCorruption):
    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        df = dataframe.copy(deep=True)
        rows = self.sample_rows(df)
        duplicates = df.loc[rows]
        return pd.concat([df, duplicates], ignore_index=True)


class DataTypeViolation(TabularCorruption):
    def __init__(self, columns=None, severity=None, sampling=None,
                 violation_type: str = "string_in_numeric", **kwargs):
        super().__init__(columns, severity=severity, sampling=sampling, **kwargs)
        self.violation_type = violation_type

    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        df = dataframe.copy(deep=True)
        cols = self.columns if isinstance(self.columns, list) else [self.columns]
        for col in cols:
            if col not in df.columns:
                continue
            rows = self.sample_rows(df)
            if self.violation_type == "string_in_numeric":
                df[col] = df[col].astype(object)
                df.loc[rows, col] = "INVALID"
            elif self.violation_type == "none":
                df.loc[rows, col] = None
        return df


# ---------------------------------------------------------------------------
# Operator registry — maps YAML key to class
# ---------------------------------------------------------------------------

_OPERATOR_REGISTRY: dict[str, type[TabularCorruption]] = {
    "GaussianNoise": GaussianNoise,
    "MaskValues": MaskValues,
    "ColumnDropping": ColumnDropping,
    "ColumnInserting": ColumnInserting,
    "MissingCategoricalValueCorruption": MissingCategoricalValueCorruption,
    "RangeViolation": RangeViolation,
    "OutlierInjection": OutlierInjection,
    "StringNoise": StringNoise,
    "Scaling": Scaling,
    "DuplicatedRows": DuplicatedRows,
    "DataTypeViolation": DataTypeViolation,
}


def apply_error_config(df: pd.DataFrame, config: list[dict[str, Any]]) -> pd.DataFrame:
    """Apply a list of error injection operations to a DataFrame.

    Args:
        df: Input DataFrame (not modified in-place)
        config: List of operator dicts from the EIDBench YAML error configs.
            Each entry: {OperatorName: {Columns: [...], Params: {...}}}

    Returns:
        New DataFrame with all error injections applied in order.
    """
    result = df.copy()
    for entry in config:
        for op_name, op_cfg in entry.items():
            cls = _OPERATOR_REGISTRY.get(op_name)
            if cls is None:
                logger.debug("Unknown error injection operator %r — skipping", op_name)
                continue
            columns = op_cfg.get("Columns", [])
            params = op_cfg.get("Params", {}) or {}
            try:
                operator = cls(columns=columns, **params)
                result = operator.transform(result)
            except Exception as exc:
                logger.warning("Error injection %r failed on columns %r: %s", op_name, columns, exc)
    return result

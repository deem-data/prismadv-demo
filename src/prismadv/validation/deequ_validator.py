from __future__ import annotations

import os
import operator
import traceback as tb
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prismadv.ir.deequ import (
    DeequCallSpec,
    DeequConstraintSpec,
    DeequEnumValueSpec,
    DeequLambdaAssertionSpec,
    DeequSatisfiesSpec,
    parse_deequ_constraint,
)
from prismadv.validation.base import BaseValidator
from prismadv.validation.errors import MissingDependencyError
from prismadv.validation.models import (
    ValidationConfig,
    ValidationConstraint,
    ValidationReport,
    ValidationResultItem,
    ValidationSeverity,
    ValidationStatus,
    ValidatorBackend,
)


def _import_deequ():
    try:
        import pyspark  # type: ignore

        os.environ.setdefault("SPARK_VERSION", ".".join(str(pyspark.__version__).split(".")[:2]))

        import pydeequ  # type: ignore
        from pydeequ.checks import Check, CheckLevel, ConstrainableDataTypes  # type: ignore
        from pydeequ.verification import VerificationResult, VerificationSuite  # type: ignore
        from pyspark.sql import SparkSession  # type: ignore
    except RuntimeError as e:  # pragma: no cover
        msg = str(e)
        if "SPARK_VERSION environment variable is required" in msg:
            raise MissingDependencyError(
                "pydeequ requires SPARK_VERSION to be set. "
                "If you use Spark 3.5, you can set `SPARK_VERSION=3.5`."
            ) from e
        raise
    except Exception as e:  # pragma: no cover
        raise MissingDependencyError(
            "Missing Deequ validator dependencies. Install with `uv sync --extra deequ`."
        ) from e
    return pydeequ, SparkSession, Check, CheckLevel, ConstrainableDataTypes, VerificationSuite, VerificationResult


_ASSERTION_OPS: dict[str, Callable[[float, float], bool]] = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def _deequ_lambda_assertion_to_callable(spec: DeequLambdaAssertionSpec) -> Callable[[float], bool]:
    def eval_clause(x: float, *, op: str, value: float) -> bool:
        fn = _ASSERTION_OPS.get(op)
        if fn is None:
            raise ValueError(f"Unsupported assertion operator: {op}")
        return bool(fn(float(x), float(value)))

    if len(spec.clauses) == 1:
        clause = spec.clauses[0]
        return lambda x: eval_clause(x, op=clause.op, value=clause.value)

    if spec.combiner == "and":
        return lambda x: all(eval_clause(x, op=c.op, value=c.value) for c in spec.clauses)
    if spec.combiner == "or":
        return lambda x: any(eval_clause(x, op=c.op, value=c.value) for c in spec.clauses)

    raise ValueError("Unsupported/missing boolean combiner for multi-clause lambda assertion")


def _to_pydeequ_value(v: Any, *, ConstrainableDataTypes: Any) -> Any:
    if isinstance(v, DeequLambdaAssertionSpec):
        return _deequ_lambda_assertion_to_callable(v)
    if isinstance(v, DeequEnumValueSpec):
        if v.enum != "ConstrainableDataTypes":
            raise ValueError(f"Unsupported Deequ enum: {v.enum}")
        try:
            return getattr(ConstrainableDataTypes, v.value)
        except AttributeError as e:
            raise ValueError(f"Unknown ConstrainableDataTypes value: {v.value}") from e
    return v


def _apply_deequ_constraint(check: Any, spec: DeequConstraintSpec, *, ConstrainableDataTypes: Any) -> Any:
    if isinstance(spec, DeequCallSpec):
        fn = getattr(check, spec.method)
        args = [_to_pydeequ_value(a, ConstrainableDataTypes=ConstrainableDataTypes) for a in spec.args]
        kwargs = {
            k: _to_pydeequ_value(v, ConstrainableDataTypes=ConstrainableDataTypes)
            for k, v in spec.kwargs.items()
        }
        return fn(*args, **kwargs)
    if isinstance(spec, DeequSatisfiesSpec):
        fn = getattr(check, "satisfies")
        args = [spec.column_condition, spec.constraint_name]
        if spec.assertion is not None:
            args.append(_to_pydeequ_value(spec.assertion, ConstrainableDataTypes=ConstrainableDataTypes))
        return fn(*args)
    raise TypeError(f"Unsupported DeequConstraintSpec: {type(spec)!r}")


class DeequValidator(BaseValidator):
    backend = ValidatorBackend.DEEQU

    def __init__(self, spark=None):
        self._spark = spark

    def _get_or_create_spark(self):
        pydeequ, SparkSession, Check, CheckLevel, ConstrainableDataTypes, VerificationSuite, VerificationResult = (
            _import_deequ()
        )
        if self._spark is not None:
            return self._spark

        spark = (
            SparkSession.builder.appName("prismadv-validator")
            .master("local[*]")
            .config("spark.ui.showConsoleProgress", "false")
            .config("spark.sql.shuffle.partitions", "8")
            .config("spark.jars.packages", pydeequ.deequ_maven_coord)
            .config("spark.jars.excludes", pydeequ.f2j_maven_coord)
            .getOrCreate()
        )
        spark.sparkContext.setLogLevel("ERROR")
        self._spark = spark
        return spark

    def validate_csv(
        self,
        path: str | Path,
        *,
        dataset_id: str,
        constraints: Sequence[ValidationConstraint],
        cfg: ValidationConfig | None = None,
    ) -> ValidationReport:
        cfg = cfg or ValidationConfig()
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(str(p))

        pydeequ, SparkSession, Check, CheckLevel, ConstrainableDataTypes, VerificationSuite, VerificationResult = (
            _import_deequ()
        )
        spark = self._get_or_create_spark()

        df = spark.read.option("header", "true").option("inferSchema", "true").csv(str(p))

        report_started = datetime.now(timezone.utc)
        items: list[ValidationResultItem] = []

        for c in constraints:
            started_at = datetime.now(timezone.utc)
            code = c.code.deequ

            if not c.enabled:
                finished_at = datetime.now(timezone.utc)
                items.append(
                    ValidationResultItem(
                        constraint_id=c.id,
                        backend=self.backend,
                        status=ValidationStatus.SKIPPED,
                        severity=c.severity,
                        column=c.column,
                        columns=c.columns,
                        code=code,
                        message="Constraint disabled",
                        started_at=started_at,
                        finished_at=finished_at,
                        duration_ms=int(max((finished_at - started_at).total_seconds() * 1000, 0)),
                    )
                )
                continue

            if not code:
                finished_at = datetime.now(timezone.utc)
                items.append(
                    ValidationResultItem(
                        constraint_id=c.id,
                        backend=self.backend,
                        status=ValidationStatus.ERROR,
                        severity=c.severity,
                        column=c.column,
                        columns=c.columns,
                        code=None,
                        error="Missing Deequ code for constraint",
                        started_at=started_at,
                        finished_at=finished_at,
                        duration_ms=int(max((finished_at - started_at).total_seconds() * 1000, 0)),
                    )
                )
                continue

            level = (
                CheckLevel.Error
                if c.severity == ValidationSeverity.ERROR
                else CheckLevel.Warning
                if c.severity == ValidationSeverity.WARNING
                else CheckLevel.Warning
            )

            try:
                spec = parse_deequ_constraint(code)
                check = Check(spark, level, "prismadv-check")
                check = _apply_deequ_constraint(check, spec, ConstrainableDataTypes=ConstrainableDataTypes)

                result = VerificationSuite(spark).onData(df).addCheck(check).run()
                rows = VerificationResult.checkResultsAsDataFrame(spark, result).collect()
                row0 = rows[0] if rows else None
                row_dict: Mapping[str, Any] = (
                    row0.asDict(recursive=True) if row0 is not None and hasattr(row0, "asDict") else {}
                )
                status_str = str(row_dict.get("constraint_status") or "")
                message = str(row_dict.get("constraint_message") or "")

                status = (
                    ValidationStatus.PASSED
                    if status_str == "Success"
                    else ValidationStatus.FAILED
                    if status_str == "Failure"
                    else ValidationStatus.ERROR
                )
                finished_at = datetime.now(timezone.utc)
                items.append(
                    ValidationResultItem(
                        constraint_id=c.id,
                        backend=self.backend,
                        status=status,
                        severity=c.severity,
                        column=c.column,
                        columns=c.columns,
                        code=code,
                        message=message,
                        details=row_dict if cfg.include_details else None,
                        started_at=started_at,
                        finished_at=finished_at,
                        duration_ms=int(max((finished_at - started_at).total_seconds() * 1000, 0)),
                    )
                )
            except Exception as e:  # pragma: no cover
                finished_at = datetime.now(timezone.utc)
                trace = tb.format_exc()
                items.append(
                    ValidationResultItem(
                        constraint_id=c.id,
                        backend=self.backend,
                        status=ValidationStatus.ERROR,
                        severity=c.severity,
                        column=c.column,
                        columns=c.columns,
                        code=code,
                        error=str(e),
                        traceback=(
                            trace[: cfg.max_traceback_chars] if cfg.include_traceback and cfg.max_traceback_chars else None
                        ),
                        started_at=started_at,
                        finished_at=finished_at,
                        duration_ms=int(max((finished_at - started_at).total_seconds() * 1000, 0)),
                    )
                )

        report_finished = datetime.now(timezone.utc)
        return ValidationReport.from_items(
            dataset_id=dataset_id,
            backend=self.backend,
            started_at=report_started,
            finished_at=report_finished,
            items=items,
        )

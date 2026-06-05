from __future__ import annotations

import traceback as tb
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from prismadv.ir.gx import parse_gx_expectation
from prismadv.validation.base import BaseValidator
from prismadv.validation.errors import MissingDependencyError
from prismadv.validation.models import (
    ValidationConfig,
    ValidationConstraint,
    ValidationReport,
    ValidationResultItem,
    ValidationStatus,
    ValidatorBackend,
)


def _import_gx():
    try:
        import great_expectations as gx  # type: ignore
    except Exception as e:  # pragma: no cover
        raise MissingDependencyError(
            "Missing Great Expectations dependency. Install with `uv sync --extra gx`."
        ) from e

    try:
        import pandas as pd  # type: ignore
    except Exception as e:  # pragma: no cover
        raise MissingDependencyError("Missing pandas dependency. Install with `uv sync --extra gx`.") from e

    return gx, pd


def _summarize_validation_result(vr: Any) -> str:
    try:
        exc = getattr(vr, "exception_info", None) or {}
        if exc.get("raised_exception") and exc.get("exception_message"):
            return str(exc.get("exception_message"))
    except Exception:
        pass

    try:
        result = getattr(vr, "result", None) or {}
        unexpected = result.get("unexpected_count")
        pct = result.get("unexpected_percent")
        if unexpected is not None and pct is not None:
            return f"unexpected_count={unexpected} ({pct:.2f}%)"
        if unexpected is not None:
            return f"unexpected_count={unexpected}"
    except Exception:
        pass

    return ""


class GreatExpectationsValidator(BaseValidator):
    backend = ValidatorBackend.GREAT_EXPECTATIONS

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

        gx, pd = _import_gx()

        df = pd.read_csv(p)

        report_started = datetime.now(timezone.utc)
        items_by_id: dict[str, ValidationResultItem] = {}
        expectations: list[Any] = []

        # Create an ephemeral context and suite for in-memory validation.
        context = gx.get_context(mode="ephemeral")
        suite = context.suites.add(gx.ExpectationSuite(name="prismadv-suite"))

        for c in constraints:
            started_at = datetime.now(timezone.utc)
            code = c.code.great_expectations

            if not c.enabled:
                finished_at = datetime.now(timezone.utc)
                items_by_id[c.id] = ValidationResultItem(
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
                continue

            if not code:
                finished_at = datetime.now(timezone.utc)
                items_by_id[c.id] = ValidationResultItem(
                    constraint_id=c.id,
                    backend=self.backend,
                    status=ValidationStatus.ERROR,
                    severity=c.severity,
                    column=c.column,
                    columns=c.columns,
                    code=None,
                    error="Missing Great Expectations code for constraint",
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=int(max((finished_at - started_at).total_seconds() * 1000, 0)),
                )
                continue

            try:
                spec = parse_gx_expectation(code)
                expectation_name = spec.to_class_name()
                expectation_cls = getattr(gx.expectations, expectation_name)
                expectation = expectation_cls(**spec.kwargs)
                expectation.meta = {"constraint_id": c.id, "code": code}
                suite.add_expectation(expectation)
                expectations.append(expectation)
            except Exception as e:
                finished_at = datetime.now(timezone.utc)
                trace = tb.format_exc()
                items_by_id[c.id] = ValidationResultItem(
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

        if expectations:
            data_source = context.data_sources.add_or_update_pandas(name="prismadv-pandas")
            data_asset = data_source.add_dataframe_asset(name="df")
            batch_definition = data_asset.add_batch_definition_whole_dataframe("batch")
            batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

            try:
                validation_results = batch.validate(suite)
            except Exception as e:  # pragma: no cover
                # Fatal run-level error: mark remaining constraints as errored.
                finished_at = datetime.now(timezone.utc)
                for c in constraints:
                    if c.id in items_by_id or not c.enabled:
                        continue
                    items_by_id[c.id] = ValidationResultItem(
                        constraint_id=c.id,
                        backend=self.backend,
                        status=ValidationStatus.ERROR,
                        severity=c.severity,
                        column=c.column,
                        columns=c.columns,
                        code=c.code.great_expectations,
                        error=f"GX validation failed: {e}",
                        started_at=finished_at,
                        finished_at=finished_at,
                        duration_ms=0,
                    )
                validation_results = None

            if validation_results is not None:
                for vr in validation_results.results:
                    try:
                        meta = vr.expectation_config.to_json_dict().get("meta", {}) or {}
                        constraint_id = meta.get("constraint_id")
                    except Exception:
                        constraint_id = None

                    if not constraint_id:
                        continue

                    finished_at = datetime.now(timezone.utc)
                    c = next((x for x in constraints if x.id == constraint_id), None)
                    if c is None:
                        continue

                    items_by_id[constraint_id] = ValidationResultItem(
                        constraint_id=constraint_id,
                        backend=self.backend,
                        status=ValidationStatus.PASSED if vr.success else ValidationStatus.FAILED,
                        severity=c.severity,
                        column=c.column,
                        columns=c.columns,
                        code=c.code.great_expectations,
                        message=_summarize_validation_result(vr),
                        details=vr.to_json_dict() if cfg.include_details else None,
                        started_at=finished_at,
                        finished_at=finished_at,
                        duration_ms=0,
                    )

        report_finished = datetime.now(timezone.utc)
        items: list[ValidationResultItem] = []
        for c in constraints:
            item = items_by_id.get(c.id)
            if item is None:
                # Should not happen; keep report consistent.
                now = datetime.now(timezone.utc)
                item = ValidationResultItem(
                    constraint_id=c.id,
                    backend=self.backend,
                    status=ValidationStatus.ERROR,
                    severity=c.severity,
                    column=c.column,
                    columns=c.columns,
                    code=c.code.great_expectations,
                    error="Missing validation result",
                    started_at=now,
                    finished_at=now,
                    duration_ms=0,
                )
            items.append(item)

        return ValidationReport.from_items(
            dataset_id=dataset_id,
            backend=self.backend,
            started_at=report_started,
            finished_at=report_finished,
            items=items,
        )

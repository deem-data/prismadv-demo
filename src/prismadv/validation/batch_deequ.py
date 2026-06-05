"""Batched Deequ validation for error-benchmark comparisons.

Runs constraints via PyDeequ's VerificationSuite. Attempts a single batched
run first; if that fails (one bad check can poison the whole suite), falls
back to running each constraint individually.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from prismadv.ir.deequ import parse_deequ_constraint
from prismadv.validation.deequ_validator import (
    _apply_deequ_constraint,
    _import_deequ,
)

logger = logging.getLogger(__name__)

_ARRAY_RE = re.compile(r'\bArray\(([^)]*)\)')
_HINT_RE = re.compile(r',\s*"[^"]*"\s*\)$')


def _normalise_deequ_code(code: str) -> str:
    """Normalise LLM-generated Deequ code for the Python parser."""
    result = _ARRAY_RE.sub(r'[\1]', code)
    result = _HINT_RE.sub(')', result)
    return result


def _prepare_check(
    constraint_id: str,
    deequ_code: str,
    spark_session: Any,
    Check: Any,
    CheckLevel: Any,
    ConstrainableDataTypes: Any,
) -> Any | None:
    """Parse and build a Deequ Check object. Returns None on failure."""
    if not deequ_code:
        return None
    try:
        normalised = _normalise_deequ_code(deequ_code)
        spec = parse_deequ_constraint(normalised)
        check = Check(spark_session, CheckLevel.Warning, constraint_id)
        check = _apply_deequ_constraint(check, spec, ConstrainableDataTypes=ConstrainableDataTypes)
        return check
    except Exception as exc:
        logger.warning("Failed to parse Deequ constraint %s: %s", constraint_id, exc)
        return None


def _run_single(
    spark_df: Any,
    constraint_id: str,
    check: Any,
    spark_session: Any,
    VerificationSuite: Any,
    VerificationResult: Any,
) -> bool | None:
    """Run a single Check and return True (violated), False (passed), or None (error)."""
    try:
        result = VerificationSuite(spark_session).onData(spark_df).addCheck(check).run()
        rows = VerificationResult.checkResultsAsDataFrame(spark_session, result).collect()
        if not rows:
            return None
        row_dict = rows[0].asDict(recursive=True) if hasattr(rows[0], "asDict") else {}
        status_str = str(row_dict.get("constraint_status") or "")
        return status_str == "Failure"
    except Exception as exc:
        logger.warning("Deequ constraint %s failed at runtime: %s", constraint_id, exc)
        return None


def validate_constraints_batch(
    spark_df: Any,
    constraint_codes: list[tuple[str, str]],
    spark_session: Any,
) -> dict[str, bool | None]:
    """Run Deequ constraints and return per-constraint results.

    Returns:
        {constraint_id: result} where:
          True  = constraint FAILED (violation detected)
          False = constraint PASSED (no issue)
          None  = constraint could not be parsed/executed (error)
    """
    if not constraint_codes:
        return {}

    pydeequ, SparkSession, Check, CheckLevel, ConstrainableDataTypes, VerificationSuite, VerificationResult = (
        _import_deequ()
    )

    # Phase 1: parse all constraints, separate good from bad
    checks: dict[str, Any] = {}  # constraint_id -> Check object
    results: dict[str, bool | None] = {}

    for constraint_id, deequ_code in constraint_codes:
        check = _prepare_check(constraint_id, deequ_code, spark_session, Check, CheckLevel, ConstrainableDataTypes)
        if check is None:
            results[constraint_id] = None
        else:
            checks[constraint_id] = check

    if not checks:
        return results

    # Phase 2: try batched run first (fast path)
    try:
        suite = VerificationSuite(spark_session).onData(spark_df)
        for check in checks.values():
            suite = suite.addCheck(check)
        run_result = suite.run()
        rows = VerificationResult.checkResultsAsDataFrame(spark_session, run_result).collect()

        for row in rows:
            row_dict = row.asDict(recursive=True) if hasattr(row, "asDict") else {}
            check_desc = str(row_dict.get("check") or "")
            status_str = str(row_dict.get("constraint_status") or "")
            if check_desc in checks:
                results[check_desc] = (status_str == "Failure")

        # Any checks not in results → something went wrong for them
        for cid in checks:
            if cid not in results:
                results[cid] = None

        return results

    except Exception:
        logger.warning(
            "Batched VerificationSuite failed for %d checks, falling back to individual runs",
            len(checks),
        )

    # Phase 3: fallback — run each constraint individually
    for constraint_id, check in checks.items():
        results[constraint_id] = _run_single(
            spark_df, constraint_id, check, spark_session, VerificationSuite, VerificationResult
        )

    return results

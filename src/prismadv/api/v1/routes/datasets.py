"""Dataset query endpoints."""

from __future__ import annotations

import csv
import logging
import statistics
from collections import Counter
from io import StringIO

from fastapi import APIRouter, HTTPException, Query

from prismadv.api.v1 import dependencies
from prismadv.api.v1.schemas import (
    CategoricalColumnStats,
    CategoricalColumnStatsResponse,
    ColumnStatsResponse,
    ColumnType,
    DataQualityMetrics,
    DatasetPreviewColumn,
    DatasetPreviewResponse,
    DatasetQualityResponse,
    HEALTH_COMPLETENESS_HEALTHY,
    HEALTH_COMPLETENESS_WARNING,
    HEALTH_VALIDITY_HEALTHY,
    HEALTH_VALIDITY_WARNING,
    InferredType,
    NumericalColumnStats,
    NumericalColumnStatsResponse,
    OverallHealth,
    TextualColumnStats,
    TextualColumnStatsResponse,
    ValidateConstraintRequest,
    ValidateConstraintResponse,
)
from prismadv.api.v1.storage import SessionStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["datasets"])


def infer_column_type(value: str) -> InferredType:
    """Infer the type of a column value.

    Args:
        value: String value to analyze

    Returns:
        Inferred type
    """
    if not value or value.strip() == "":
        return InferredType.STRING

    # Try integer
    try:
        int(value)
        return InferredType.INTEGER
    except ValueError:
        pass

    # Try float
    try:
        float(value)
        return InferredType.FLOAT
    except ValueError:
        pass

    # Try boolean
    if value.lower() in {"true", "false", "yes", "no", "1", "0"}:
        return InferredType.BOOLEAN

    # Default to string
    return InferredType.STRING


def categorize_column(column_name: str, values: list[str]) -> ColumnType:
    """Categorize a column based on its values.

    Args:
        column_name: Column name
        values: Sample values from the column

    Returns:
        Column type category
    """
    # Check if mostly numeric
    numeric_count = 0
    for val in values:
        if not val or val.strip() == "":
            continue
        try:
            float(val)
            numeric_count += 1
        except ValueError:
            pass

    if numeric_count / max(len(values), 1) > 0.8:
        return ColumnType.NUMERICAL

    # Check unique ratio for categorical
    unique_values = set(values)
    unique_ratio = len(unique_values) / max(len(values), 1)

    if unique_ratio < 0.5 or len(unique_values) < 20:
        return ColumnType.CATEGORICAL

    return ColumnType.TEXTUAL


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
async def get_dataset_preview(
    dataset_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> DatasetPreviewResponse:
    """Get preview of dataset rows.

    Args:
        dataset_id: Dataset file ID
        limit: Maximum number of rows to return (1-100)
        storage: Session storage

    Returns:
        Dataset preview with rows and column info

    Raises:
        HTTPException: If dataset not found or invalid
    """
    # Retrieve dataset file
    dataset_file = storage.get_file(dataset_id)
    if not dataset_file:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset not found: {dataset_id}",
        )

    # Parse CSV content
    try:
        csv_content = str(dataset_file.content)
        csv_file = StringIO(csv_content)
        reader = csv.DictReader(csv_file)

        # Read rows
        rows: list[dict[str, str]] = []
        all_rows: list[dict[str, str]] = []
        for i, row in enumerate(reader):
            all_rows.append(row)
            if i < limit:
                rows.append(row)

        if not rows:
            raise HTTPException(
                status_code=400,
                detail="Dataset is empty or has no data rows",
            )

        # Extract column info
        column_names = list(rows[0].keys())
        columns: list[DatasetPreviewColumn] = []

        for col_name in column_names:
            # Get sample values for type inference
            sample_values = [row.get(col_name, "") for row in all_rows[:100]]

            # Infer type from first non-empty value
            inferred_type = InferredType.STRING
            for val in sample_values:
                if val and val.strip():
                    inferred_type = infer_column_type(val)
                    break

            # Categorize column
            column_type = categorize_column(col_name, sample_values)

            columns.append(
                DatasetPreviewColumn(
                    name=col_name,
                    type=inferred_type,
                    inferred_type=column_type,
                )
            )

        logger.info(
            f"Preview dataset {dataset_id}: {len(rows)} rows, {len(columns)} columns"
        )

        return DatasetPreviewResponse(
            dataset_id=dataset_id,
            name=dataset_file.name,
            columns=columns,
            rows=rows,
            total_rows=len(all_rows),
        )

    except csv.Error as e:
        logger.error(f"Failed to parse CSV for dataset {dataset_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid CSV format. Please check the file contents.",
        )
    except Exception as e:
        logger.error(f"Failed to preview dataset {dataset_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to preview dataset.",
        )


@router.get("/{dataset_id}/columns/{column_name}/stats")
async def get_column_stats(
    dataset_id: str,
    column_name: str,
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> ColumnStatsResponse:
    """Get detailed statistics for a specific column.

    Args:
        dataset_id: Dataset file ID
        column_name: Column name to analyze
        storage: Session storage

    Returns:
        Column statistics (type depends on column type)

    Raises:
        HTTPException: If dataset not found or column doesn't exist
    """
    # Retrieve dataset file
    dataset_file = storage.get_file(dataset_id)
    if not dataset_file:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset not found: {dataset_id}",
        )

    # Parse CSV content
    try:
        csv_content = str(dataset_file.content)
        csv_file = StringIO(csv_content)
        reader = csv.DictReader(csv_file)

        # Read all rows
        rows: list[dict[str, str]] = list(reader)

        if not rows:
            raise HTTPException(
                status_code=400,
                detail="Dataset is empty",
            )

        # Check if column exists
        if column_name not in rows[0]:
            raise HTTPException(
                status_code=404,
                detail=f"Column '{column_name}' not found in dataset",
            )

        # Extract column values
        values = [row.get(column_name, "") for row in rows]

        # Calculate basic stats
        count = len(values)
        null_count = sum(1 for v in values if not v or v.strip() == "")
        null_percentage = (null_count / count) if count > 0 else 0.0
        non_null_values = [v for v in values if v and v.strip()]
        unique_count = len(set(non_null_values))

        # Get constraint IDs for this column from generation context
        constraint_ids = []
        jobs = storage.list_jobs()
        if jobs:
            # Get the most recent completed job
            latest_job = max(
                (j for j in jobs if j.status == "completed" and j.context),
                key=lambda j: j.id,
                default=None,
            )
            if latest_job and latest_job.context:
                # Find constraints that apply to this column
                for constraint in latest_job.context.constraints:
                    if constraint.column == column_name:
                        constraint_ids.append(constraint.id)

        # Infer column type and calculate type-specific stats
        inferred_type = infer_column_type(non_null_values[0] if non_null_values else "")
        column_type = categorize_column(column_name, values)

        if column_type == ColumnType.NUMERICAL:
            # Parse numeric values
            numeric_values = []
            for v in non_null_values:
                try:
                    numeric_values.append(float(v))
                except ValueError:
                    pass

            if not numeric_values:
                raise HTTPException(
                    status_code=400,
                    detail=f"Column '{column_name}' has no valid numeric values",
                )

            # Calculate numerical stats
            sorted_values = sorted(numeric_values)
            mean_val = statistics.mean(numeric_values)
            median_val = statistics.median(numeric_values)
            std_dev = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0.0
            q1 = statistics.quantiles(numeric_values, n=4)[0] if len(numeric_values) > 3 else sorted_values[0]
            q3 = statistics.quantiles(numeric_values, n=4)[2] if len(numeric_values) > 3 else sorted_values[-1]

            # Find mode
            mode_val = None
            try:
                mode_val = statistics.mode(numeric_values)
            except statistics.StatisticsError:
                pass

            # Calculate IQR and outliers
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outliers = [v for v in numeric_values if v < lower_bound or v > upper_bound]

            # Create distribution (histogram)
            num_bins = min(10, len(set(numeric_values)))
            if num_bins > 1:
                bin_width = (max(numeric_values) - min(numeric_values)) / num_bins
                distribution = {}
                for v in numeric_values:
                    bin_idx = min(int((v - min(numeric_values)) / bin_width), num_bins - 1)
                    bin_label = f"{min(numeric_values) + bin_idx * bin_width:.2f}-{min(numeric_values) + (bin_idx + 1) * bin_width:.2f}"
                    distribution[bin_label] = distribution.get(bin_label, 0) + 1
            else:
                distribution = {str(numeric_values[0]): len(numeric_values)}

            stats = NumericalColumnStats(
                count=count,
                null_count=null_count,
                null_percentage=null_percentage,
                unique_count=unique_count,
                constraint_ids=constraint_ids,
                min=min(numeric_values),
                max=max(numeric_values),
                mean=mean_val,
                median=median_val,
                mode=mode_val,
                std_dev=std_dev,
                q1=q1,
                q3=q3,
                distribution=distribution,
                outliers=outliers[:10],  # Limit to 10 outliers
            )

            return NumericalColumnStatsResponse(
                dataset_id=dataset_id,
                column_name=column_name,
                type=inferred_type,
                stats=stats,
            )

        elif column_type == ColumnType.CATEGORICAL:
            # Calculate categorical stats
            value_counts = Counter(non_null_values)
            unique_values = list(value_counts.keys())[:50]  # Limit to 50 unique values
            distribution = {k: v for k, v in value_counts.most_common(20)}  # Top 20

            stats = CategoricalColumnStats(
                count=count,
                null_count=null_count,
                null_percentage=null_percentage,
                unique_count=unique_count,
                constraint_ids=constraint_ids,
                unique_values=unique_values,
                distribution=distribution,
            )

            return CategoricalColumnStatsResponse(
                dataset_id=dataset_id,
                column_name=column_name,
                type=inferred_type,
                stats=stats,
            )

        else:  # TEXTUAL
            # Calculate textual stats
            lengths = [len(v) for v in non_null_values]
            avg_length = sum(lengths) / len(lengths) if lengths else 0.0
            min_length = min(lengths) if lengths else 0
            max_length = max(lengths) if lengths else 0

            # Length distribution
            length_distribution = {}
            for length in lengths:
                bucket = f"{(length // 10) * 10}-{(length // 10) * 10 + 9}"
                length_distribution[bucket] = length_distribution.get(bucket, 0) + 1

            # Sample values
            sample_values = non_null_values[:10]

            # Simple pattern detection
            pattern = None
            if all("@" in v for v in non_null_values[:10]):
                pattern = "email"
            elif all(v.isdigit() for v in non_null_values[:10]):
                pattern = "numeric_string"

            completeness = (count - null_count) / count if count > 0 else 0.0

            stats = TextualColumnStats(
                count=count,
                null_count=null_count,
                null_percentage=null_percentage,
                unique_count=unique_count,
                constraint_ids=constraint_ids,
                avg_length=avg_length,
                min_length=min_length,
                max_length=max_length,
                length_distribution=length_distribution,
                sample_values=sample_values,
                pattern=pattern,
                completeness=completeness,
            )

            return TextualColumnStatsResponse(
                dataset_id=dataset_id,
                column_name=column_name,
                type=inferred_type,
                stats=stats,
            )

    except csv.Error as e:
        logger.error(f"Failed to parse CSV for dataset {dataset_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid CSV format. Please check the file contents.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get column stats for {column_name} in dataset {dataset_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to get column stats.",
        )


@router.get("/{dataset_id}/quality", response_model=DatasetQualityResponse)
async def get_data_quality_metrics(
    dataset_id: str,
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> DatasetQualityResponse:
    """Get overall data quality metrics for a dataset.

    Args:
        dataset_id: Dataset file ID
        storage: Session storage

    Returns:
        Data quality metrics including completeness, validity, and constraint info

    Raises:
        HTTPException: If dataset not found
    """
    # Retrieve dataset file
    dataset_file = storage.get_file(dataset_id)
    if not dataset_file:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset not found: {dataset_id}",
        )

    # Get the most recent completed job for constraint info
    jobs = storage.list_jobs()
    completed_jobs = [j for j in jobs if j.status == "completed" and j.context]

    if not completed_jobs:
        # No constraints generated yet - return basic metrics with actual completeness
        logger.info(f"No constraints found for dataset {dataset_id}, returning basic metrics")
        basic_completeness = 0.0
        try:
            csv_content = str(dataset_file.content)
            csv_file = StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            if rows:
                total_cells = len(rows) * len(rows[0])
                null_cells = sum(
                    1 for row in rows for value in row.values()
                    if not value or value.strip() == ""
                )
                basic_completeness = ((total_cells - null_cells) / total_cells) if total_cells > 0 else 0.0
        except Exception:
            pass
        metrics = DataQualityMetrics(
            completeness=basic_completeness,
            validity=0.0,
            constraint_count=0,
            active_constraints=0,
            disabled_constraints=0,
            violation_count=0,
            violations_by_constraint={},
            overall_health=OverallHealth.HEALTHY if basic_completeness >= 0.9 else OverallHealth.WARNING,
        )
        return DatasetQualityResponse(dataset_id=dataset_id, metrics=metrics)

    # Use the most recent job
    latest_job = max(completed_jobs, key=lambda j: j.created_at)
    context = latest_job.context

    if not context:
        raise HTTPException(
            status_code=500,
            detail="Generation context not found",
        )

    # Parse CSV to calculate completeness
    try:
        csv_content = str(dataset_file.content)
        csv_file = StringIO(csv_content)
        reader = csv.DictReader(csv_file)
        rows = list(reader)

        if not rows:
            raise HTTPException(
                status_code=400,
                detail="Dataset is empty",
            )

        # Calculate overall completeness (% of non-null values)
        total_cells = len(rows) * len(rows[0])
        null_cells = sum(
            1
            for row in rows
            for value in row.values()
            if not value or value.strip() == ""
        )
        completeness = ((total_cells - null_cells) / total_cells) if total_cells > 0 else 0.0

        # Get constraints from context
        from prismadv.generation import generation_context_to_api

        result = generation_context_to_api(context)
        constraints = result.constraints

        # Count active/disabled constraints
        active_constraints = sum(1 for c in constraints if c.enabled)
        disabled_constraints = sum(1 for c in constraints if not c.enabled)

        # Run actual validation using Great Expectations
        violations_by_constraint = {}
        validation_messages: dict[str, str] = {}
        violation_count = 0

        try:
            import tempfile
            from prismadv.validation import GreatExpectationsValidator, ValidationConstraint
            from prismadv.validation.models import ConstraintCode as ValidationConstraintCode, ValidationStatus

            # Convert API constraints to validation constraints
            validation_constraints = []
            for c in constraints:
                validation_constraints.append(ValidationConstraint(
                    id=c.id,
                    column=c.column,
                    enabled=c.enabled,
                    code=ValidationConstraintCode(
                        great_expectations=c.code.great_expectations,
                        deequ=c.code.deequ,
                    ),
                    label=c.label,
                ))

            # Write CSV to temp file for validation
            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
                tmp.write(csv_content)
                tmp_path = tmp.name

            try:
                validator = GreatExpectationsValidator()
                report = validator.validate_csv(
                    tmp_path,
                    dataset_id=dataset_id,
                    constraints=validation_constraints,
                )

                # Extract violations per constraint
                for item in report.items:
                    if item.status == ValidationStatus.FAILED:
                        violations_by_constraint[item.constraint_id] = 1
                        violation_count += 1
                        validation_messages[item.constraint_id] = item.message or "Constraint violated"
                    elif item.status == ValidationStatus.PASSED:
                        violations_by_constraint[item.constraint_id] = 0
                    elif item.status == ValidationStatus.ERROR:
                        violations_by_constraint[item.constraint_id] = 2  # Validation error
                        validation_messages[item.constraint_id] = item.error or "Could not evaluate constraint"
                    # Skip SKIPPED (disabled) constraints

                logger.info(
                    f"Validation complete: {report.summary.passed} passed, "
                    f"{report.summary.failed} failed, {report.summary.skipped} skipped"
                )
            finally:
                import os
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except ImportError as e:
            logger.warning(f"Great Expectations not available for validation: {e}")
            # Fallback: mark all as unknown (no violations data)
        except Exception as e:
            logger.warning(f"Validation failed, using fallback: {e}")
            # Fallback: mark all as unknown

        # Calculate validity based on validation results
        column_count = len(rows[0]) if rows else 0
        if violations_by_constraint:
            passed_count = sum(1 for v in violations_by_constraint.values() if v == 0)
            validity = passed_count / len(violations_by_constraint) if violations_by_constraint else 0.0
        else:
            # Fallback: use constraint coverage
            columns_with_constraints = len(set(c.column for c in constraints))
            validity = (columns_with_constraints / column_count) if column_count > 0 else 0.0

        # Determine overall health
        if completeness >= HEALTH_COMPLETENESS_HEALTHY and validity >= HEALTH_VALIDITY_HEALTHY and violation_count == 0:
            overall_health = OverallHealth.HEALTHY
        elif completeness >= HEALTH_COMPLETENESS_WARNING and validity >= HEALTH_VALIDITY_WARNING:
            overall_health = OverallHealth.WARNING
        else:
            overall_health = OverallHealth.ISSUES

        metrics = DataQualityMetrics(
            completeness=completeness,
            validity=validity,
            constraint_count=len(constraints),
            active_constraints=active_constraints,
            disabled_constraints=disabled_constraints,
            violation_count=violation_count,
            violations_by_constraint=violations_by_constraint,
            validation_messages=validation_messages,
            overall_health=overall_health,
        )

        logger.info(
            f"Data quality metrics for {dataset_id}: "
            f"completeness={completeness:.2%}, validity={validity:.2%}, "
            f"health={overall_health.value}"
        )

        return DatasetQualityResponse(dataset_id=dataset_id, metrics=metrics)

    except csv.Error as e:
        logger.error(f"Failed to parse CSV for dataset {dataset_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid CSV format. Please check the file contents.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get quality metrics for dataset {dataset_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to get quality metrics.",
        )


@router.post("/{dataset_id}/validate-constraint", response_model=ValidateConstraintResponse)
async def validate_single_constraint(
    dataset_id: str,
    request: ValidateConstraintRequest,
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> ValidateConstraintResponse:
    """Validate a single constraint against the dataset.

    Supports both Great Expectations and Deequ backends. The ``backend``
    field selects which validator to run.

    Args:
        dataset_id: Dataset file ID
        request: Constraint validation request
        storage: Session storage

    Returns:
        Validation result with status, message, and error details
    """
    dataset_file = storage.get_file(dataset_id)
    if not dataset_file:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")

    backend = request.backend or "great_expectations"

    try:
        import os
        import tempfile

        from prismadv.validation.models import (
            ConstraintCode as ValidationConstraintCode,
            ValidationConstraint,
            ValidationStatus,
        )

        csv_content = str(dataset_file.content)

        validation_constraint = ValidationConstraint(
            id=request.constraint_id,
            column=request.column,
            enabled=True,
            code=ValidationConstraintCode(
                great_expectations=request.great_expectations_code or None,
                deequ=request.deequ_code or None,
            ),
            label=request.constraint_id,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write(csv_content)
            tmp_path = tmp.name

        try:
            if backend == "deequ":
                from prismadv.validation import DeequValidator
                validator = DeequValidator()
            else:
                from prismadv.validation import GreatExpectationsValidator
                validator = GreatExpectationsValidator()

            report = validator.validate_csv(
                tmp_path,
                dataset_id=dataset_id,
                constraints=[validation_constraint],
            )

            if not report.items:
                return ValidateConstraintResponse(
                    constraint_id=request.constraint_id,
                    backend=backend,
                    status="error",
                    message="No validation result returned",
                    duration_ms=report.duration_ms,
                )

            item = report.items[0]

            if item.status == ValidationStatus.PASSED:
                return ValidateConstraintResponse(
                    constraint_id=request.constraint_id,
                    backend=backend,
                    status="passed",
                    message=item.message or "Constraint satisfied — no violations detected.",
                    duration_ms=item.duration_ms,
                )
            elif item.status == ValidationStatus.FAILED:
                return ValidateConstraintResponse(
                    constraint_id=request.constraint_id,
                    backend=backend,
                    status="failed",
                    message=item.message or "Constraint violated.",
                    duration_ms=item.duration_ms,
                )
            else:
                return ValidateConstraintResponse(
                    constraint_id=request.constraint_id,
                    backend=backend,
                    status="error",
                    message=item.message or "",
                    error=item.error or "Could not evaluate constraint.",
                    duration_ms=item.duration_ms,
                )
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    except ImportError as e:
        logger.warning(f"Validator not available for backend {backend}: {e}")
        raise HTTPException(
            status_code=501,
            detail=f"Validation is not available ({backend} dependencies not installed).",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to validate constraint for dataset {dataset_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to validate constraint.",
        )

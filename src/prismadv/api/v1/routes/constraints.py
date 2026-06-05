"""Constraint generation endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import Response

from prismadv.api.v1 import dependencies
from prismadv.api.v1.dependencies import limiter
from prismadv.api.v1.schemas import (
    BatchResult,
    DeequSuggestion,
    DeequSuggestionsRequest,
    DeequSuggestionsResponse,
    DetectColumnsRequest,
    DetectColumnsResponse,
    ErrorBenchmarkJobStatus,
    ErrorBenchmarkRequest,
    ErrorBenchmarkResult,
    ExportConstraintsRequest,
    ExportFormat,
    GenerateConstraintsRequest,
    GenerateConstraintsResponse,
    GenerateFromAssumptionRequest,
    GenerateFromAssumptionResponse,
    GenerationStatus,
    GetJobStatusResponse,
    JobStatus,
)
from prismadv.api.v1.storage import SessionStorage, StoredFile
from prismadv.generation import GenerationOrchestrator, generation_context_to_api
from prismadv.llm import create_lm, create_lm_from_env

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/constraints", tags=["constraints"])

# Thread pool for running generation in background
_executor = ThreadPoolExecutor(max_workers=4)


class _JobCancelledError(Exception):
    """Raised inside _run_generation when the job is cancelled by the user."""


def _run_generation(
    job_id: str,
    storage: SessionStorage,
    task_file: StoredFile,
    dataset_file: StoredFile,
    options: dict | None,
) -> None:
    """Run constraint generation in background thread.

    Updates job progress as each stage completes.
    """

    def update_progress(progress: float, step: str) -> None:
        """Update job progress."""
        storage.update_job(job_id, progress=progress, current_step=step)
        logger.debug(f"Job {job_id}: {step} ({progress:.0%})")

    try:
        # Stage 1: Initialize LLM
        update_progress(0.05, "Initializing LLM...")

        try:
            if options and options.get("api_key"):
                provider = options.get("llm_provider") or "gemini"
                model = options.get("model")
                api_key = options["api_key"]

                lm = create_lm(
                    provider=provider,
                    api_key=api_key,
                    model=model,
                )
            else:
                model = options.get("model") if options else None
                lm = create_lm_from_env(model=model)
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}", exc_info=True)
            storage.update_job(
                job_id,
                status="failed",
                error="Failed to initialize LLM. Check your API key and provider settings.",
                progress=0.0,
                current_step="Failed",
            )
            return

        # Stage 2: Write dataset to temp file
        update_progress(0.1, "Preparing dataset...")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            tmp.write(str(dataset_file.content))
            dataset_path = tmp.name

        try:
            # Create progress callback for orchestrator
            def on_orchestrator_progress(progress: float, step: str) -> None:
                # Check if job was cancelled before updating progress
                job = storage.get_job(job_id)
                if job and job.cancelled:
                    raise _JobCancelledError()
                # Map orchestrator progress (0-1) to our range (0.1-0.95)
                mapped_progress = 0.1 + (progress * 0.85)
                update_progress(mapped_progress, step)

            # Stage 3-6: Run orchestrator with progress tracking
            max_parallel_calls = int(options.get("max_parallel_calls", 5)) if options else 5
            orchestrator = GenerationOrchestrator(
                lm=lm,
                max_parallel_llm_calls=max_parallel_calls,
            )

            # Apply optimized prompts if the user has activated them
            try:
                from prismadv.optimization.config import get_active_instructions
                from prismadv.optimization.adapter import _patch_instructions
                active = get_active_instructions()
                if active:
                    _patch_instructions(orchestrator, active)
            except ImportError as _ie:
                logger.debug("Optimization module not available, skipping prompt patching: %s", _ie)

            logger.info(
                f"Starting constraint generation for job {job_id} "
                f"(task: {task_file.name}, dataset: {dataset_file.name})"
            )

            selected_columns = options.get("selected_columns") if options else None

            # Recover column detection cost from cache (detection ran in a separate API call)
            column_detection_cost = 0.0
            if selected_columns is not None:
                cached_detection = storage.find_column_detection(
                    task_file.id, dataset_file.id
                )
                if cached_detection:
                    column_detection_cost = cached_detection.detection_cost

            # Stage callback to store intermediate results for progressive UI
            def on_stage_complete(stage: str, partial_context: GenerationContext) -> None:
                try:
                    partial_result = generation_context_to_api(partial_context)
                    storage.update_job(
                        job_id,
                        intermediate_result=partial_result.model_dump(by_alias=True),
                    )
                except Exception as e:
                    logger.debug(f"Failed to build intermediate result for stage {stage}: {e}")

            context = orchestrator.generate(
                task_code=str(task_file.content),
                task_file_name=task_file.name,
                dataset_path=dataset_path,
                task_description=f"Analysis of {dataset_file.name}",
                progress_callback=on_orchestrator_progress,
                stage_callback=on_stage_complete,
                selected_columns=selected_columns,
                column_detection_cost=column_detection_cost,
            )

            # Stage 7: Finalize
            update_progress(0.98, "Finalizing results...")

            # Store generation context in job
            storage.update_job(
                job_id,
                context=context,
                status="completed",
                progress=1.0,
                current_step="Complete!",
            )

            result = generation_context_to_api(context)
            logger.info(
                f"✓ Generated {len(result.constraints)} constraints "
                f"from {len(context.assumptions)} assumptions "
                f"for job {job_id}"
            )

        except _JobCancelledError:
            logger.info(f"Job {job_id} cancelled by user")
            storage.update_job(
                job_id,
                status="cancelled",
                current_step="Cancelled by user",
                progress=0.0,
            )
        except Exception as e:
            logger.error(f"Constraint generation failed for job {job_id}: {e}", exc_info=True)
            storage.update_job(
                job_id,
                status="failed",
                error="Constraint generation failed. Please try again.",
                progress=0.0,
                current_step="Failed",
            )
        finally:
            # Clean up temp file
            try:
                os.unlink(dataset_path)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Unexpected error in generation for job {job_id}: {e}", exc_info=True)
        storage.update_job(
            job_id,
            status="failed",
            error="An unexpected error occurred during generation.",
            progress=0.0,
            current_step="Failed",
        )


@router.post("/detect-columns", response_model=DetectColumnsResponse)
@limiter.limit("10/minute")
async def detect_columns(
    request: Request,
    body: DetectColumnsRequest,
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> DetectColumnsResponse:
    """Detect which dataset columns are accessed by the task code.

    Runs dataset profiling and LLM-based column access detection.
    Use this as a lightweight pre-flight before /generate to show the
    user which columns were detected, letting them confirm or adjust
    the selection before the full generation run.

    Args:
        request: FastAPI request (used by rate limiter)
        body: Task file ID, dataset ID, and optional LLM options
        storage: Session storage

    Returns:
        All dataset columns and the subset the LLM detected as accessed

    Raises:
        HTTPException: If files not found or LLM fails
    """
    import tempfile

    task_file = storage.get_file(body.task_file_id)
    if not task_file:
        raise HTTPException(status_code=404, detail=f"Task file not found: {body.task_file_id}")

    dataset_file = storage.get_file(body.dataset_id)
    if not dataset_file:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {body.dataset_id}")

    options = body.options

    # Return cached result if available and force_redetect not requested
    if not body.force_redetect:
        cached = storage.find_column_detection(body.task_file_id, body.dataset_id)
        if cached:
            logger.info(
                f"Using cached column detection for task={body.task_file_id} "
                f"dataset={body.dataset_id}"
            )
            return DetectColumnsResponse(
                all_columns=cached.all_columns,
                accessed_columns=cached.accessed_columns,
                cached=True,
            )

    try:
        if options and options.api_key:
            from prismadv.llm import create_lm
            lm = create_lm(
                provider=options.llm_provider or "gemini",
                api_key=options.api_key,
                model=options.model,
            )
        else:
            model = options.model if options else None
            lm = create_lm_from_env(model=model)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to initialize LLM. Check your API key and provider settings.")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        tmp.write(str(dataset_file.content))
        dataset_path = tmp.name

    try:
        import os
        from pathlib import Path
        from prismadv.generation.column_access import ColumnAccessDetector
        from prismadv.profiling import ProfilerBackend, get_profiler

        profiler = get_profiler(ProfilerBackend.BUILTIN)
        import uuid as _uuid
        dataset_id = f"dataset-{_uuid.uuid4().hex[:8]}"
        profile = profiler.profile_csv(
            dataset_path,
            dataset_id=dataset_id,
            dataset_name=Path(dataset_path).name,
        )
        all_columns = [col.name for col in profile.dataset.columns]

        detector = ColumnAccessDetector(lm=lm)
        accessed_columns = detector.detect(
            columns=all_columns,
            code_script=str(task_file.content),
            downstream_task_description=f"Analysis of {dataset_file.name}",
        )

        # Calculate detection cost from LM history
        detection_cost = 0.0
        try:
            import litellm as _litellm
            for entry in getattr(lm, "history", []):
                response = entry.get("response")
                if response:
                    try:
                        detection_cost += _litellm.completion_cost(completion_response=response)
                    except Exception:
                        pass
        except Exception:
            pass

        storage.store_column_detection(
            task_file_id=body.task_file_id,
            dataset_id=body.dataset_id,
            all_columns=all_columns,
            accessed_columns=accessed_columns,
            detection_cost=detection_cost,
        )

        return DetectColumnsResponse(
            all_columns=all_columns,
            accessed_columns=accessed_columns,
            cached=False,
        )
    except Exception as e:
        logger.error(f"Column detection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Column detection failed. Please try again.")
    finally:
        try:
            os.unlink(dataset_path)
        except Exception:
            pass


@router.post("/generate", response_model=GenerateConstraintsResponse)
@limiter.limit("10/minute")
async def generate_constraints(
    request: Request,
    body: GenerateConstraintsRequest,
    background_tasks: BackgroundTasks,
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> GenerateConstraintsResponse:
    """Generate data quality constraints from task code and dataset.

    This endpoint starts the generation process asynchronously and returns
    immediately with a job ID. Poll /constraints/jobs/{job_id} for progress.

    Pipeline stages:
    1. Profiles the dataset
    2. Detects columns accessed in code
    3. Extracts assumptions from code
    4. Generates constraints (Deequ + Great Expectations)
    5. Builds flow graph for visualization

    Args:
        request: FastAPI request (used by rate limiter)
        body: Generation request with file IDs and options
        background_tasks: FastAPI background tasks
        storage: Session storage

    Returns:
        Job ID and initial status (processing)

    Raises:
        HTTPException: If files not found
    """
    # Retrieve task file
    task_file = storage.get_file(body.task_file_id)
    if not task_file:
        raise HTTPException(
            status_code=404,
            detail=f"Task file not found: {body.task_file_id}",
        )

    # Retrieve dataset file
    dataset_file = storage.get_file(body.dataset_id)
    if not dataset_file:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset not found: {body.dataset_id}",
        )

    # Determine the model name and selected columns for caching
    model_name = body.options.model if body.options else None
    force_regenerate = body.options.force_regenerate if body.options else False
    selected_columns = body.options.selected_columns if body.options else None

    # Check for cached result (unless force_regenerate is set)
    if not force_regenerate:
        cached_job = storage.find_completed_job(
            task_file_id=body.task_file_id,
            dataset_id=body.dataset_id,
            model=model_name,
            selected_columns=selected_columns,
        )

        if cached_job and cached_job.context:
            logger.info(
                f"Using cached result from job {cached_job.id} "
                f"(task: {task_file.name}, dataset: {dataset_file.name}, model: {model_name})"
            )
            result = generation_context_to_api(cached_job.context)
            return GenerateConstraintsResponse(
                job_id=cached_job.id,
                status=GenerationStatus.COMPLETED,
                progress=1.0,
                current_step="Complete! (cached)",
                cached=True,
                result=result,
            )

    # Create generation job
    job_id = storage.store_job(
        task_file_id=body.task_file_id,
        dataset_id=body.dataset_id,
        model=model_name,
        selected_columns=selected_columns,
    )

    # Update job status to processing
    storage.update_job(
        job_id,
        status="processing",
        progress=0.0,
        current_step="Starting generation...",
    )

    # Prepare options dict for background task
    options_dict = None
    if body.options:
        options_dict = {
            "api_key": body.options.api_key,
            "llm_provider": body.options.llm_provider,
            "model": body.options.model,
            "selected_columns": body.options.selected_columns,
            "max_parallel_calls": body.options.max_parallel_calls,
        }

    # Run generation in background thread
    loop = asyncio.get_running_loop()
    loop.run_in_executor(
        _executor,
        _run_generation,
        job_id,
        storage,
        task_file,
        dataset_file,
        options_dict,
    )

    # Return immediately with job ID
    return GenerateConstraintsResponse(
        job_id=job_id,
        status=GenerationStatus.PROCESSING,
        progress=0.0,
        current_step="Starting generation...",
        result=None,
    )


@router.get("/jobs/{job_id}", response_model=GenerateConstraintsResponse)
async def get_job_status(
    job_id: str,
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> GenerateConstraintsResponse:
    """Get the status and progress of a generation job.

    Poll this endpoint to track generation progress and get the result
    when complete.

    Args:
        job_id: Job identifier from /generate response
        storage: Session storage

    Returns:
        Current job status, progress, and result (if complete)

    Raises:
        HTTPException: If job not found
    """
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}",
        )

    # Map internal status to API status
    status_map = {
        "pending": GenerationStatus.PROCESSING,
        "processing": GenerationStatus.PROCESSING,
        "completed": GenerationStatus.COMPLETED,
        "failed": GenerationStatus.FAILED,
        "cancelled": GenerationStatus.CANCELLED,
    }
    status = status_map.get(job.status, GenerationStatus.PROCESSING)

    # Build response
    result = None
    intermediate_result = None
    if job.status == "completed" and job.context:
        result = generation_context_to_api(job.context)
    elif job.intermediate_result:
        intermediate_result = job.intermediate_result

    response = GenerateConstraintsResponse(
        job_id=job_id,
        status=status,
        progress=job.progress,
        current_step=job.current_step,
        result=result,
        intermediate_result=intermediate_result,
    )

    # Include error in current_step if failed
    if job.status == "failed" and job.error:
        response.current_step = f"Failed: {job.error}"

    return response


@router.delete("/jobs/{job_id}", status_code=204)
async def cancel_job(
    job_id: str,
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> None:
    """Cancel a running or pending generation job.

    Args:
        job_id: Job identifier
        storage: Session storage

    Raises:
        HTTPException: If job not found
    """
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    cancelled = storage.cancel_job(job_id)
    if not cancelled:
        logger.info(f"Cancel requested for job {job_id} but it is already in terminal state: {job.status}")


@router.post("/deequ-suggestions", response_model=DeequSuggestionsResponse)
async def get_deequ_suggestions(
    body: DeequSuggestionsRequest,
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> DeequSuggestionsResponse:
    """Generate Deequ baseline constraint suggestions for a dataset.

    Profiles the dataset using the built-in profiler and produces Deequ-style
    constraint suggestions (completeness, range, uniqueness, enum, format) purely
    from data statistics — without any LLM calls or task-code awareness.

    Args:
        body: Request containing the dataset_id.
        storage: Session storage.

    Returns:
        DeequSuggestionsResponse with a list of suggested constraints.

    Raises:
        HTTPException: If dataset not found.
    """
    import os
    import tempfile

    from prismadv.generation.deequ_suggester import generate_deequ_suggestions

    dataset_file = storage.get_file(body.dataset_id)
    if not dataset_file:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {body.dataset_id}")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        tmp.write(str(dataset_file.content))
        dataset_path = tmp.name

    try:
        items = generate_deequ_suggestions(dataset_path)

        suggestions = [
            DeequSuggestion(
                id=item.id,
                column=item.column,
                constraint_type=item.constraint_type,
                deequ_code=item.deequ_code,
                description=item.description,
            )
            for item in items
        ]

        return DeequSuggestionsResponse(
            dataset_id=body.dataset_id,
            suggestions=suggestions,
        )
    except Exception as e:
        logger.error(f"Deequ suggestion generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate Deequ suggestions.")
    finally:
        try:
            os.unlink(dataset_path)
        except Exception:
            pass


@router.post("/export")
async def export_constraints(
    request: ExportConstraintsRequest,
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> Response:
    """Export constraints in specified format.

    Args:
        request: Export request with constraint IDs and format
        storage: Session storage

    Returns:
        Exported constraints as downloadable file

    Raises:
        HTTPException: If no constraints found or export fails
    """
    # Get the most recent completed job
    jobs = storage.list_jobs()
    completed_jobs = [j for j in jobs if j.status == "completed" and j.context]

    if not completed_jobs:
        raise HTTPException(
            status_code=404,
            detail="No completed constraint generation found. Generate constraints first.",
        )

    # Use the most recent job
    latest_job = max(completed_jobs, key=lambda j: j.created_at)
    context = latest_job.context

    if not context:
        raise HTTPException(
            status_code=500,
            detail="Generation context not found",
        )

    # Convert to API format to get constraints
    result = generation_context_to_api(context)

    # Filter constraints if IDs specified
    if request.constraint_ids:
        constraints = [c for c in result.constraints if c.id in request.constraint_ids]
    else:
        constraints = result.constraints

    if not constraints:
        raise HTTPException(
            status_code=404,
            detail="No constraints found to export",
        )

    # Get task and dataset info
    task_file = storage.get_file(latest_job.task_file_id)
    dataset_file = storage.get_file(latest_job.dataset_id)
    task_name = task_file.name if task_file else "unknown"
    dataset_name = dataset_file.name if dataset_file else "unknown"

    # Generate export content
    try:
        if request.format == ExportFormat.GREAT_EXPECTATIONS:
            content = _export_great_expectations(constraints, task_name, dataset_name)
            media_type = "application/x-python"
            filename = "prismadv_constraints.py"

        elif request.format == ExportFormat.DEEQU:
            content = _export_deequ(constraints, task_name, dataset_name)
            media_type = "text/x-scala"
            filename = "prismadv_constraints.scala"

        else:  # JSON
            content = _export_json(constraints, task_name, dataset_name)
            media_type = "application/json"
            filename = "prismadv_constraints.json"

        logger.info(
            f"Exported {len(constraints)} constraints in {request.format.value} format"
        )

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except Exception as e:
        logger.error(f"Failed to export constraints: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export constraints: {str(e)}",
        )


def _export_great_expectations(constraints, task_name: str, dataset_name: str) -> str:
    """Export constraints as Great Expectations Python code."""
    lines = [
        '"""Data quality constraints generated by PrismaDV"""',
        "",
        "import great_expectations as gx",
        "from great_expectations.dataset import PandasDataset",
        "",
        "",
        f"def validate_{_sanitize_name(dataset_name)}():",
        f'    """Generated from: {task_name} on {dataset_name}"""',
        "    # Load your data",
        "    # df = pd.read_csv('your_data.csv')",
        "    # dataset = PandasDataset(df)",
        "",
        "    # Constraints:",
    ]

    for constraint in constraints:
        lines.append(f"    # {constraint.label}")
        # Extract just the expectation line from the GX code
        gx_code = constraint.code.great_expectations.strip()
        # Add indentation
        for code_line in gx_code.split("\n"):
            if code_line.strip():
                lines.append(f"    {code_line}")
        lines.append("")

    return "\n".join(lines)


def _export_deequ(constraints, task_name: str, dataset_name: str) -> str:
    """Export constraints as Deequ Scala code."""
    lines = [
        "/**",
        " * Data quality constraints generated by PrismaDV",
        f" * Source: {task_name}",
        f" * Dataset: {dataset_name}",
        " */",
        "",
        "import com.amazon.deequ.checks.{Check, CheckLevel}",
        "import com.amazon.deequ.VerificationSuite",
        "import org.apache.spark.sql.SparkSession",
        "",
        f"object {_sanitize_name(dataset_name, capitalize=True)}Validation {{",
        "  def validate(spark: SparkSession): Unit = {",
        "    // Load your data",
        '    // val df = spark.read.csv("your_data.csv")',
        "",
        '    val check = Check(CheckLevel.Error, "PrismaDV Constraints")',
    ]

    for constraint in constraints:
        lines.append(f"      // {constraint.label}")
        # Extract the check method from Deequ code
        deequ_code = constraint.code.deequ.strip()
        for code_line in deequ_code.split("\n"):
            if code_line.strip():
                lines.append(f"      {code_line}")

    lines.extend(
        [
            "",
            "    val result = VerificationSuite()",
            "      .onData(df)",
            "      .addCheck(check)",
            "      .run()",
            "",
            "    assert(result.status == CheckStatus.Success)",
            "  }",
            "}",
        ]
    )

    return "\n".join(lines)


def _export_json(constraints, task_name: str, dataset_name: str) -> str:
    """Export constraints as JSON."""
    data = {
        "metadata": {
            "generatedBy": "PrismaDV",
            "version": "1.0",
            "timestamp": datetime.now(UTC).isoformat(),
            "taskFile": task_name,
            "dataset": dataset_name,
        },
        "constraints": [
            {
                "id": c.id,
                "column": c.column,
                "type": c.type.value,
                "columnType": c.column_type.value,
                "label": c.label,
                "enabled": c.enabled,
                "code": {
                    "greatExpectations": c.code.great_expectations,
                    "deequ": c.code.deequ,
                },
                "assumption": {
                    "text": c.assumption.text,
                    "sourceCodeLines": c.assumption.source_code_lines,
                    "sourceFile": c.assumption.source_file,
                },
            }
            for c in constraints
        ],
    }

    return json.dumps(data, indent=2)


@router.post("/generate-from-assumption", response_model=GenerateFromAssumptionResponse)
@limiter.limit("10/minute")
async def generate_from_assumption(
    request: Request,
    body: GenerateFromAssumptionRequest,
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> GenerateFromAssumptionResponse:
    """Generate constraints from a single user-provided assumption.

    Runs the constraint generator on one assumption synchronously
    and returns the resulting constraints.
    """
    import uuid
    from prismadv.generation.constraint_generator import ConstraintGenerator
    from prismadv.generation.adapters import constraint_ir_to_api
    from prismadv.ir import AssumptionIR

    task_file = storage.get_file(body.task_file_id)
    if not task_file:
        raise HTTPException(status_code=404, detail=f"Task file not found: {body.task_file_id}")
    dataset_file = storage.get_file(body.dataset_id)
    if not dataset_file:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {body.dataset_id}")

    # Initialize LLM
    try:
        options = body.options
        if options and options.api_key:
            lm = create_lm(
                provider=options.llm_provider or "gemini",
                api_key=options.api_key,
                model=options.model,
            )
        else:
            model = options.model if options else None
            lm = create_lm_from_env(model=model)
    except Exception as e:
        logger.error(f"Failed to initialize LLM for assumption generation: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to initialize LLM. Check your API key and provider settings.")

    # Build AssumptionIR
    assumption_ir = AssumptionIR(
        id=f"assumption-{uuid.uuid4().hex[:8]}",
        text=body.assumption_text,
        columns=[body.column],
        constraint_type="general",
        sources=[],
    )

    try:
        # If existing constraints are provided, run gap analysis first
        existing = body.existing_constraints or []
        if existing:
            from prismadv.generation.gap_analyzer import ConstraintGapAnalyzer

            existing_code = [
                {"greatExpectations": ec.great_expectations, "deequ": ec.deequ}
                for ec in existing
            ]
            analyzer = ConstraintGapAnalyzer(lm=lm)
            constraint_irs, message = analyzer.analyze_and_generate(
                assumption=assumption_ir,
                existing_constraints_code=existing_code,
                code_script=str(task_file.content),
                task_description=f"Task from {task_file.name}",
            )
        else:
            generator = ConstraintGenerator(lm=lm)
            constraint_irs = generator.generate(
                assumptions=[assumption_ir],
                code_script=str(task_file.content),
                accessed_columns=[body.column],
                task_description=f"Task from {task_file.name}",
            )
            message = None

        api_constraints = [
            constraint_ir_to_api(c, [assumption_ir])
            for c in constraint_irs
        ]

        logger.info(f"Generated {len(api_constraints)} constraints from user assumption (gap analysis: {bool(existing)})")
        return GenerateFromAssumptionResponse(constraints=api_constraints, message=message)

    except Exception as e:
        logger.error(f"Failed to generate constraints from assumption: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate constraints from assumption.")


# ---------------------------------------------------------------------------
# Error-batch benchmark (PrismaDV vs Deequ)
# ---------------------------------------------------------------------------

_EIDBENCH_DIR = Path(__file__).resolve().parents[5] / "benchmarks" / "EIDBench"


def _resolve_eidbench_dataset(csv_filename: str) -> str | None:
    """Match an uploaded CSV filename to an EIDBench dataset directory."""
    if not _EIDBENCH_DIR.is_dir():
        return None
    for dataset_dir in _EIDBENCH_DIR.iterdir():
        if not dataset_dir.is_dir() or dataset_dir.name.startswith("."):
            continue
        files_dir = dataset_dir / "files"
        if files_dir.is_dir():
            for f in files_dir.iterdir():
                if f.suffix == ".csv" and f.name == csv_filename:
                    return dataset_dir.name
    return None


def _describe_error_config(config: list[dict]) -> str:
    """Build a short human-readable description of an error config."""
    parts: list[str] = []
    for entry in config:
        for op_name, op_cfg in entry.items():
            cols = op_cfg.get("Columns", [])
            col_str = ", ".join(cols[:2])
            if len(cols) > 2:
                col_str += f" +{len(cols)-2}"
            parts.append(f"{op_name} on {col_str}" if col_str else op_name)
    return "; ".join(parts) or "Unknown"


def _load_error_labels(dataset_name: str, task_name: str) -> dict[str, bool]:
    """Load ground-truth labels: {error_batch_id: harmful}."""
    import json as _json
    labels_path = _EIDBENCH_DIR / "error_labels.json"
    if not labels_path.exists():
        return {}
    all_labels = _json.loads(labels_path.read_text())
    return all_labels.get(dataset_name, {}).get(task_name, {})


def _run_error_benchmark(
    job_id: str,
    storage: SessionStorage,
    dataset_name: str,
    task_name: str,
    prismadv_codes: list[tuple[str, str]],
    deequ_codes: list[tuple[str, str]],
    sample_rows: int | None,
) -> None:
    """Run error-batch benchmark in background thread."""
    import yaml
    import pandas as pd

    from prismadv.optimization.injector import apply_error_config
    from prismadv.validation.batch_deequ import validate_constraints_batch
    from prismadv.validation.deequ_validator import _import_deequ

    def _update(progress: float, step: str) -> None:
        storage.benchmark_jobs[job_id].update(
            progress=progress, current_step=step
        )

    try:
        storage.benchmark_jobs[job_id]["status"] = "running"
        _update(0.0, "Initializing Spark...")

        # Get Spark session
        pydeequ, SparkSession, *_ = _import_deequ()
        spark = (
            SparkSession.builder.appName("prismadv-benchmark")
            .master("local[*]")
            .config("spark.ui.showConsoleProgress", "false")
            .config("spark.sql.shuffle.partitions", "8")
            .config("spark.jars.packages", pydeequ.deequ_maven_coord)
            .config("spark.jars.excludes", pydeequ.f2j_maven_coord)
            .getOrCreate()
        )
        spark.sparkContext.setLogLevel("ERROR")

        _update(0.05, "Loading dataset and labels...")

        # Load ground-truth labels
        error_labels = _load_error_labels(dataset_name, task_name)

        # Load clean CSV
        dataset_dir = _EIDBENCH_DIR / dataset_name
        files_dir = dataset_dir / "files"
        csv_files = [f for f in files_dir.iterdir() if f.suffix == ".csv"]
        if not csv_files:
            raise FileNotFoundError(f"No CSV in {files_dir}")
        clean_csv_path = csv_files[0]
        clean_df = pd.read_csv(clean_csv_path)

        # Load error configs (1-25)
        errors_dir = dataset_dir / "errors"
        error_configs: list[tuple[str, list[dict]]] = []  # (batch_id, config)
        for i in range(1, 26):
            yaml_path = errors_dir / f"general_task_{i}.yaml"
            if yaml_path.exists():
                with open(yaml_path) as f:
                    config = yaml.safe_load(f) or []
                error_configs.append((str(i), config))

        total_batches = 1 + len(error_configs)  # clean + error batches
        batch_results: list[BatchResult] = []

        # --- Phase 1: validate on clean data to filter PrismaDV constraints ---
        _update(0.05, "Validating on clean data...")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            clean_df.to_csv(tmp.name, index=False)
            tmp_csv = tmp.name

        try:
            spark_df = spark.read.option("header", "true").option("inferSchema", "true").csv(tmp_csv)
            prismadv_clean_results = validate_constraints_batch(spark_df, prismadv_codes, spark)
            deequ_clean_results = validate_constraints_batch(spark_df, deequ_codes, spark)
        finally:
            try:
                os.unlink(tmp_csv)
            except Exception:
                pass

        # Keep only PrismaDV constraints that actually ran (not None) AND passed (False)
        prismadv_passed_codes = [
            (cid, code) for cid, code in prismadv_codes
            if prismadv_clean_results.get(cid) is False  # explicitly False, not None
        ]
        # Similarly filter Deequ suggestions to only those that actually ran
        deequ_working_codes = [
            (cid, code) for cid, code in deequ_codes
            if deequ_clean_results.get(cid) is not None
        ]
        prismadv_errored = sum(1 for v in prismadv_clean_results.values() if v is None)
        prismadv_violated = sum(1 for v in prismadv_clean_results.values() if v is True)
        deequ_errored = sum(1 for v in deequ_clean_results.values() if v is None)
        logger.warning(
            "Clean-data filter: PrismaDV %d/%d passed, %d violated, %d errors (of %d total). "
            "Deequ %d/%d working (%d errors)",
            len(prismadv_passed_codes), len(prismadv_codes), prismadv_violated, prismadv_errored, len(prismadv_codes),
            len(deequ_working_codes), len(deequ_codes), deequ_errored,
        )
        # Log individual PrismaDV results for debugging
        for cid, code in prismadv_codes[:5]:
            r = prismadv_clean_results.get(cid, "MISSING")
            logger.warning("  PrismaDV %s: result=%s code=%s", cid, r, code[:60])

        prismadv_clean_violations = sum(1 for v in prismadv_clean_results.values() if v is True)
        deequ_clean_violations = sum(1 for v in deequ_clean_results.values() if v is True)

        batch_results.append(BatchResult(
            batch_id="clean",
            error_description="Clean baseline",
            harmful=False,
            prismadv_violations=prismadv_clean_violations,
            prismadv_total=len(prismadv_codes),
            deequ_violations=deequ_clean_violations,
            deequ_total=len(deequ_codes),
        ))

        # --- Phase 2: run error batches with only passing PrismaDV constraints ---
        for batch_idx, (batch_id, config) in enumerate(error_configs):
            step_name = f"Validating error batch {batch_id}/{len(error_configs)}..."
            _update(0.10 + 0.85 * (batch_idx / len(error_configs)), step_name)

            batch_df = apply_error_config(clean_df, config)

            # Sample if requested
            if sample_rows and len(batch_df) > sample_rows:
                batch_df = batch_df.sample(n=sample_rows, random_state=42)

            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
                batch_df.to_csv(tmp.name, index=False)
                tmp_csv = tmp.name

            try:
                spark_df = spark.read.option("header", "true").option("inferSchema", "true").csv(tmp_csv)

                # Use only constraints that actually worked on clean data
                prismadv_results = validate_constraints_batch(spark_df, prismadv_passed_codes, spark)
                prismadv_violations = sum(1 for v in prismadv_results.values() if v is True)

                deequ_results = validate_constraints_batch(spark_df, deequ_working_codes, spark)
                deequ_violations = sum(1 for v in deequ_results.values() if v is True)
            finally:
                try:
                    os.unlink(tmp_csv)
                except Exception:
                    pass

            harmful = error_labels.get(batch_id, True)  # default harmful if no label
            batch_results.append(BatchResult(
                batch_id=batch_id,
                error_description=_describe_error_config(config),
                harmful=harmful,
                prismadv_violations=prismadv_violations,
                prismadv_total=len(prismadv_passed_codes),
                deequ_violations=deequ_violations,
                deequ_total=len(deequ_working_codes),
            ))

        # Compute summary metrics using ground-truth labels
        harmful_batches = [b for b in batch_results if b.harmful]
        safe_batches = [b for b in batch_results if not b.harmful and b.batch_id != "clean"]

        n_harmful = len(harmful_batches) or 1
        n_safe = len(safe_batches) or 1

        # Detection rate = % of harmful batches where >= 1 constraint fires
        prismadv_detected = sum(1 for b in harmful_batches if b.prismadv_violations > 0)
        deequ_detected = sum(1 for b in harmful_batches if b.deequ_violations > 0)

        # False alarm rate = % of non-harmful error batches where >= 1 constraint fires
        prismadv_false_alarms = sum(1 for b in safe_batches if b.prismadv_violations > 0)
        deequ_false_alarms = sum(1 for b in safe_batches if b.deequ_violations > 0)

        result = ErrorBenchmarkResult(
            dataset_name=dataset_name,
            total_batches=len(harmful_batches),
            prismadv_constraint_count=len(prismadv_passed_codes),
            deequ_suggestion_count=len(deequ_working_codes),
            batches=batch_results,
            prismadv_detection_rate=prismadv_detected / n_harmful,
            deequ_detection_rate=deequ_detected / n_harmful,
            prismadv_false_alarm_rate=prismadv_false_alarms / n_safe if safe_batches else 0.0,
            deequ_false_alarm_rate=deequ_false_alarms / n_safe if safe_batches else 0.0,
            prismadv_clean_violations=prismadv_clean_violations,
            deequ_clean_violations=deequ_clean_violations,
        )

        storage.benchmark_jobs[job_id].update(
            status="completed",
            progress=1.0,
            current_step="Complete!",
            result=result.model_dump(by_alias=True),
        )
        logger.info(
            "Error benchmark completed: PrismaDV detected %d/%d, Deequ detected %d/%d",
            prismadv_detected, n_harmful, deequ_detected, n_harmful,
        )

    except Exception as e:
        logger.error("Error benchmark failed: %s", e, exc_info=True)
        storage.benchmark_jobs[job_id].update(
            status="failed",
            progress=0.0,
            current_step="Failed",
            error=str(e),
        )


@router.post("/error-benchmark", response_model=ErrorBenchmarkJobStatus)
async def start_error_benchmark(
    body: ErrorBenchmarkRequest,
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> ErrorBenchmarkJobStatus:
    """Start an error-batch benchmark comparing PrismaDV constraints vs Deequ suggestions."""
    # Resolve dataset directory — accept either a directory name or a CSV filename
    dataset_name = body.dataset_name
    dataset_dir = _EIDBENCH_DIR / dataset_name
    if not dataset_dir.is_dir():
        # Try resolving from CSV filename
        resolved = _resolve_eidbench_dataset(dataset_name)
        if resolved:
            dataset_name = resolved
            dataset_dir = _EIDBENCH_DIR / dataset_name
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Error benchmark requires a supported benchmark dataset. Dataset not found: {body.dataset_name}",
            )

    prismadv_codes = [(c.id, c.deequ_code) for c in body.prismadv_constraints if c.deequ_code]
    if not prismadv_codes:
        raise HTTPException(status_code=400, detail="No PrismaDV constraints with Deequ code provided.")

    deequ_codes = [(c.id, c.deequ_code) for c in body.deequ_suggestions if c.deequ_code]
    if not deequ_codes:
        raise HTTPException(status_code=400, detail="No Deequ suggestions provided.")

    # Create benchmark job
    job_id = str(uuid.uuid4())
    storage.benchmark_jobs[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "current_step": "Starting...",
        "result": None,
        "error": None,
    }

    # Run in background
    loop = asyncio.get_running_loop()
    loop.run_in_executor(
        _executor,
        _run_error_benchmark,
        job_id,
        storage,
        dataset_name,
        body.task_name,
        prismadv_codes,
        deequ_codes,
        body.sample_rows,
    )

    return ErrorBenchmarkJobStatus(
        job_id=job_id,
        status="pending",
        progress=0.0,
        current_step="Starting...",
    )


@router.get("/error-benchmark/jobs/{job_id}", response_model=ErrorBenchmarkJobStatus)
async def get_error_benchmark_status(
    job_id: str,
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> ErrorBenchmarkJobStatus:
    """Poll error-benchmark job status."""
    job = storage.benchmark_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Benchmark job not found: {job_id}")

    return ErrorBenchmarkJobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress", 0.0),
        current_step=job.get("current_step", ""),
        result=job.get("result"),
        error=job.get("error"),
    )


def _sanitize_name(name: str, capitalize: bool = False) -> str:
    """Sanitize a filename for use as a function/class name."""
    # Remove extension
    name = Path(name).stem
    # Replace non-alphanumeric with underscore
    name = "".join(c if c.isalnum() else "_" for c in name)
    # Remove leading digits
    name = name.lstrip("0123456789_")
    # Ensure not empty
    name = name or "data"
    # Capitalize if needed
    if capitalize:
        name = name[0].upper() + name[1:] if name else "Data"
    return name

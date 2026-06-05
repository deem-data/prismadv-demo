"""Optimization endpoints — expose GEPA prompt optimization via REST API."""

from __future__ import annotations

import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from prismadv.api.v1.schemas import (
    GenerationStatus,
    OptimizationJobResult,
    OptimizationJobStatus,
    OptimizationRequest,
    PromptInstructions,
    PromptsResponse,
)
from prismadv.llm import create_lm, create_lm_from_env

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/optimization", tags=["optimization"])

_executor = ThreadPoolExecutor(max_workers=2)

# ---------------------------------------------------------------------------
# In-memory job registry (global, not per-session)
# ---------------------------------------------------------------------------

@dataclass
class _OptimizationJob:
    id: str
    status: str = "pending"
    progress: float = 0.0
    current_step: str = "Initializing..."
    step_log: list[str] = field(default_factory=list)
    result_data: Any = None  # OptimizationResult
    error: str | None = None
    cancelled: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


_jobs: dict[str, _OptimizationJob] = {}


# ---------------------------------------------------------------------------
# Helper: extract baseline instructions without needing a real LM
# ---------------------------------------------------------------------------

def _get_baseline_instructions() -> PromptInstructions:
    try:
        import dspy
        from prismadv.generation.signatures import (
            AssumptionExtractionSig,
            ConstraintCodeGenerationSig,
            DataFlowDetectionSig,
        )
        return PromptInstructions(
            column_access=dspy.Predict(DataFlowDetectionSig).signature.instructions,
            assumption_extraction=dspy.Predict(AssumptionExtractionSig).signature.instructions,
            constraint_generation=dspy.Predict(ConstraintCodeGenerationSig).signature.instructions,
        )
    except Exception as exc:
        logger.warning("Could not extract baseline instructions: %s", exc)
        return PromptInstructions(
            column_access="(unavailable)",
            assumption_extraction="(unavailable)",
            constraint_generation="(unavailable)",
        )


def _active_prompt_instructions() -> PromptInstructions | None:
    try:
        from prismadv.optimization.config import get_active_instructions
        active = get_active_instructions()
        if active:
            return PromptInstructions(
                column_access=active.get("column_access", ""),
                assumption_extraction=active.get("assumption_extraction", ""),
                constraint_generation=active.get("constraint_generation", ""),
            )
    except ImportError:
        pass
    return None


# ---------------------------------------------------------------------------
# Background optimization runner
# ---------------------------------------------------------------------------

def _run_optimization(job_id: str, request: OptimizationRequest) -> None:
    job = _jobs.get(job_id)
    if job is None:
        return

    class CancelledError(Exception):
        pass

    def update(progress: float, step: str) -> None:
        if job.cancelled:
            raise CancelledError("Optimization cancelled by user")
        job.progress = progress
        job.current_step = step
        job.step_log.append(step)
        job.status = "running"

    try:
        update(0.0, "Initializing LLMs...")

        opts = request.options
        if opts and opts.api_key:
            lm = create_lm(
                provider=opts.llm_provider or "gemini",
                api_key=opts.api_key,
                model=opts.model,
            )
        else:
            lm = create_lm_from_env(model=opts.model if opts else None)

        # Create a separate (optionally stronger) LM for the proposer/reflection step
        proposer_lm = None
        proposer_model = opts.proposer_model if opts else None
        if proposer_model:
            if opts and opts.api_key:
                proposer_lm = create_lm(
                    provider=opts.llm_provider or "openai",
                    api_key=opts.api_key,
                    model=proposer_model,
                )
            else:
                proposer_lm = create_lm_from_env(model=proposer_model)

        update(0.05, f"Loading training data ({request.dataset})...")

        from prismadv.optimization.training import EIDBenchLoader
        loader = EIDBenchLoader()
        units = loader.load_training_units(
            request.dataset,
            max_units=request.max_units,
        )

        if not units:
            raise ValueError(
                f"No training units found for dataset {request.dataset!r}. "
                "Check that benchmarks/data_processed/ contains evaluation labels."
            )

        update(0.10, f"Loaded {len(units)} training units — starting optimization...")

        from prismadv.optimization.engine import run_gepa

        result = run_gepa(
            lm=lm,
            training_units=units,
            n_rounds=request.n_rounds,
            n_train=request.n_train,
            budget=request.budget,
            proposer_lm=proposer_lm,
            progress_callback=update,
        )

        job.result_data = result
        job.status = "completed"
        job.progress = 1.0
        job.current_step = (
            f"Complete! Score: {result.eval_score_before:.3f} → {result.eval_score_after:.3f}"
        )

    except CancelledError:
        logger.info("Optimization job %s cancelled by user", job_id)
        job.status = "cancelled"
        job.current_step = "Cancelled"
        job.progress = 0.0

    except Exception as exc:
        logger.error("Optimization job %s failed: %s", job_id, exc, exc_info=True)
        job.status = "failed"
        job.error = str(exc)
        job.current_step = f"Failed: {exc}"
        job.progress = 0.0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/prompts", response_model=PromptsResponse)
async def get_prompts() -> PromptsResponse:
    """Return the current and (if active) optimized module instructions."""
    baseline = _get_baseline_instructions()
    optimized = _active_prompt_instructions()
    return PromptsResponse(
        current=baseline,
        optimized=optimized,
        optimization_active=optimized is not None,
    )


@router.post("/run", response_model=OptimizationJobStatus)
async def run_optimization(request: OptimizationRequest) -> OptimizationJobStatus:
    """Start an async GEPA optimization job.

    Returns a job_id. Poll /optimization/jobs/{job_id} for progress.
    """
    job_id = str(uuid.uuid4())
    job = _OptimizationJob(id=job_id)
    _jobs[job_id] = job

    loop = asyncio.get_running_loop()
    loop.run_in_executor(_executor, _run_optimization, job_id, request)

    return OptimizationJobStatus(
        job_id=job_id,
        status=GenerationStatus.PROCESSING,
        progress=0.0,
        current_step="Starting optimization...",
    )


@router.get("/jobs/{job_id}", response_model=OptimizationJobStatus)
async def get_optimization_job(job_id: str) -> OptimizationJobStatus:
    """Poll the status of an optimization job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Optimization job not found: {job_id}")

    status_map = {
        "pending": GenerationStatus.PROCESSING,
        "running": GenerationStatus.PROCESSING,
        "completed": GenerationStatus.COMPLETED,
        "failed": GenerationStatus.FAILED,
    }
    api_status = status_map.get(job.status, GenerationStatus.PROCESSING)

    result: OptimizationJobResult | None = None
    if job.status == "completed" and job.result_data is not None:
        r = job.result_data
        result = OptimizationJobResult(
            before_instructions=PromptInstructions(
                column_access=r.before_instructions.get("column_access", ""),
                assumption_extraction=r.before_instructions.get("assumption_extraction", ""),
                constraint_generation=r.before_instructions.get("constraint_generation", ""),
            ),
            after_instructions=PromptInstructions(
                column_access=r.after_instructions.get("column_access", ""),
                assumption_extraction=r.after_instructions.get("assumption_extraction", ""),
                constraint_generation=r.after_instructions.get("constraint_generation", ""),
            ),
            eval_score_before=r.eval_score_before,
            eval_score_after=r.eval_score_after,
            improved=r.improved,
            n_rounds_completed=r.n_rounds_completed,
            llm_cost=r.llm_cost,
        )

    response = OptimizationJobStatus(
        job_id=job_id,
        status=api_status,
        progress=job.progress,
        current_step=job.current_step if job.status != "failed" else f"Failed: {job.error}",
        step_log=list(job.step_log),
        result=result,
    )
    return response


@router.post("/jobs/{job_id}/cancel", status_code=204)
async def cancel_optimization_job(job_id: str) -> None:
    """Cancel a running optimization job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    job.cancelled = True
    logger.info("Cancellation requested for optimization job %s", job_id)


@router.post("/apply", status_code=204)
async def apply_optimized_prompts(job_id: str) -> None:
    """Apply the optimized instructions from a completed job as the active set.

    Future constraint generation runs will use these instructions until reset.
    """
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    if job.status != "completed" or job.result_data is None:
        raise HTTPException(status_code=400, detail="Job has not completed successfully")

    try:
        from prismadv.optimization.config import set_active_instructions
        set_active_instructions(job.result_data.after_instructions)
        logger.info("Applied optimized instructions from job %s", job_id)
    except Exception as exc:
        logger.error("Failed to apply optimized instructions: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to apply optimized instructions.")


@router.post("/reset", status_code=204)
async def reset_to_baseline() -> None:
    """Reset active instructions back to the original baseline."""
    try:
        from prismadv.optimization.config import clear_active_instructions
        clear_active_instructions()
        logger.info("Reset to baseline instructions")
    except Exception as exc:
        logger.error("Failed to reset instructions: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reset instructions.")

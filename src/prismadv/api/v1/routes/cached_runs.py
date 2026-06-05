"""Cached optimization runs — browse and apply pre-computed GEPA results."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from prismadv.api.v1.schemas import (
    CachedRunDetail,
    CachedRunListResponse,
    CachedRunSummary,
    OptimizationConfig,
    PromptInstructions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/optimization/cached-runs", tags=["optimization"])

# Instruction key mapping: research codebase → demo API
_KEY_MAP = {
    "dataflow_inspector": "column_access",
    "assumption_generation": "assumption_extraction",
    "ir_generation": "constraint_generation",
    "generator": "constraint_generation",
}


def _runs_dir() -> Path:
    """Resolve the optimization_runs directory in the demo repo root."""
    # src/prismadv/api/v1/routes/cached_runs.py → go up 5 levels to repo root
    repo_root = Path(__file__).resolve().parents[5]
    return repo_root / "benchmarks" / "optimization_runs"


def _map_instructions(raw: dict[str, str]) -> PromptInstructions:
    """Map research-codebase instruction keys to demo API keys."""
    return PromptInstructions(
        column_access=raw.get("dataflow_inspector", ""),
        assumption_extraction=raw.get("assumption_generation", ""),
        constraint_generation=raw.get("ir_generation", raw.get("generator", "")),
    )


def _extract_f1_scores(run_dir: Path) -> tuple[float, float]:
    """Extract initial and final F1 scores from test trajectory files.

    Uses test_1 (cross_new_data) as the primary test.
    Returns (initial_f1, final_f1) as percentages, or (0.0, 0.0) on failure.
    """
    test_files = sorted(run_dir.glob("test_trajectory_test_1_*"))
    if not test_files:
        return 0.0, 0.0
    try:
        traj = json.loads(test_files[0].read_text()).get("trajectory", [])
        if not traj:
            return 0.0, 0.0
        initial_f1 = traj[0].get("test_f1", 0.0) * 100
        final_f1 = traj[-1].get("test_f1", 0.0) * 100
        return initial_f1, final_f1
    except Exception:
        return 0.0, 0.0


def _load_summary(run_dir: Path) -> CachedRunSummary | None:
    """Load a CachedRunSummary from a run directory, or None on failure."""
    summary_path = run_dir / "summary.json"
    final_path = run_dir / "final_program.json"
    if not summary_path.exists() or not final_path.exists():
        return None

    try:
        summary = json.loads(summary_path.read_text())
        final = json.loads(final_path.read_text())
    except Exception as exc:
        logger.warning("Failed to load cached run %s: %s", run_dir.name, exc)
        return None

    initial_score, final_score = _extract_f1_scores(run_dir)

    return CachedRunSummary(
        run_id=run_dir.name,
        timestamp=summary.get("run_timestamp", ""),
        llm_name=summary.get("llm_name", "unknown"),
        reflection_llm_name=summary.get("reflection_llm_name"),
        baseline_type=summary.get("baseline_type"),
        metric_type="f1_score",
        train_dataset=summary.get("train_dataset_name", "unknown"),
        max_rounds=summary.get("max_rounds", 0),
        initial_score=initial_score,
        final_score=final_score,
        improved=final_score > initial_score,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=CachedRunListResponse)
async def list_cached_runs() -> CachedRunListResponse:
    """List all pre-computed GEPA optimization runs."""
    runs_dir = _runs_dir()
    if not runs_dir.exists():
        return CachedRunListResponse(runs=[])

    runs: list[CachedRunSummary] = []
    for d in sorted(runs_dir.iterdir()):
        if not d.is_dir():
            continue
        s = _load_summary(d)
        if s is not None:
            runs.append(s)

    return CachedRunListResponse(runs=runs)


@router.get("/dataset-info/{dataset_name}")
async def get_dataset_info(dataset_name: str) -> dict:
    """List available scripts and error configs for a dataset."""
    repo_root = Path(__file__).resolve().parents[5]
    eidbench = repo_root / "benchmarks" / "EIDBench" / dataset_name

    scripts: list[str] = []
    scripts_dir = eidbench / "scripts" / "general"
    if scripts_dir.exists():
        scripts = sorted(p.stem for p in scripts_dir.glob("*.py"))

    error_configs: list[str] = []
    errors_dir = eidbench / "errors"
    if errors_dir.exists():
        for p in sorted(errors_dir.glob("general_task_*.yaml")):
            cid = p.stem.replace("general_task_", "")
            if cid != "0":  # skip placeholder
                error_configs.append(cid)

    return {"dataset": dataset_name, "scripts": scripts, "errorConfigs": error_configs}


@router.get("/{run_id}", response_model=CachedRunDetail)
async def get_cached_run(run_id: str) -> CachedRunDetail:
    """Load full detail (including instructions) for a specific cached run."""
    run_dir = _runs_dir() / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"Cached run not found: {run_id}")

    summary_path = run_dir / "summary.json"
    final_path = run_dir / "final_program.json"
    if not summary_path.exists() or not final_path.exists():
        raise HTTPException(status_code=404, detail=f"Incomplete cached run: {run_id}")

    try:
        summary = json.loads(summary_path.read_text())
        final = json.loads(final_path.read_text())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read cached run: {exc}")

    # Baseline instructions — prefer summary, fall back to round_-1_initial.json
    baseline_raw = summary.get("initial_program_instructions", {})
    if not baseline_raw:
        r0_path = run_dir / "round_-1_initial.json"
        if r0_path.exists():
            try:
                r0 = json.loads(r0_path.read_text())
                baseline_raw = r0.get("instructions", {})
            except Exception:
                pass
    baseline = _map_instructions(baseline_raw)

    # Optimized instructions from final_program
    optimized_raw = final.get("instructions", {})
    optimized = _map_instructions(optimized_raw)

    # F1 scores from test trajectories
    initial_score, final_score = _extract_f1_scores(run_dir)

    config = OptimizationConfig(
        execution_llm=summary.get("llm_name", "unknown"),
        proposer_llm=summary.get("reflection_llm_name"),
        max_rounds=summary.get("max_rounds", 1),
        train_scripts=summary.get("train_script_name_list", []),
        eval_scripts=summary.get("eval_script_name_list", []),
        test_scripts=summary.get("new_script_name_list", []),
        train_error_configs=summary.get("train_eval_label_list", []),
        test_error_configs=summary.get("cross_new_data_test_label_list", []),
    )

    return CachedRunDetail(
        run_id=run_id,
        timestamp=summary.get("run_timestamp", ""),
        llm_name=summary.get("llm_name", "unknown"),
        train_dataset=summary.get("train_dataset_name", "unknown"),
        initial_score=initial_score,
        final_score=final_score,
        baseline_instructions=baseline,
        optimized_instructions=optimized,
        config=config,
    )


@router.get("/{run_id}/error-config/{config_id}")
async def get_error_config(run_id: str, config_id: str) -> dict:
    """Return the error injection YAML for a specific config ID."""
    runs_dir = _runs_dir()
    run_dir = runs_dir / run_id
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    try:
        summary = json.loads(summary_path.read_text())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read run: {exc}")

    dataset = summary.get("train_dataset_name", "")
    # Resolve the EIDBench errors directory
    repo_root = Path(__file__).resolve().parents[5]
    errors_dir = repo_root / "benchmarks" / "EIDBench" / dataset / "errors"

    yaml_path = errors_dir / f"general_task_{config_id}.yaml"
    if not yaml_path.exists():
        raise HTTPException(status_code=404, detail=f"Error config not found: {config_id}")

    return {"configId": config_id, "dataset": dataset, "content": yaml_path.read_text()}


@router.post("/{run_id}/apply", status_code=204)
async def apply_cached_run(run_id: str) -> None:
    """Apply a cached run's optimized instructions as the active set."""
    run_dir = _runs_dir() / run_id
    final_path = run_dir / "final_program.json"
    if not final_path.exists():
        raise HTTPException(status_code=404, detail=f"Cached run not found: {run_id}")

    try:
        final = json.loads(final_path.read_text())
        raw_instructions = final.get("instructions", {})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read cached run: {exc}")

    # Map to demo keys and activate
    mapped = {_KEY_MAP.get(k, k): v for k, v in raw_instructions.items()}

    try:
        from prismadv.optimization.config import set_active_instructions
        set_active_instructions(mapped)
        logger.info("Applied cached run %s instructions", run_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to apply instructions: {exc}")

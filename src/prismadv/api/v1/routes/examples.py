"""Example data loading endpoint."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import tempfile

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from prismadv.api.v1 import dependencies
from prismadv.api.v1.storage import SessionStorage
from prismadv.profiling import ProfilerBackend, get_profiler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/examples", tags=["examples"])

# ─── EIDBench helpers ────────────────────────────────────────────────────────

def _get_eidbench_root() -> Path | None:
    """Return the EIDBench root directory.

    Checks EIDBENCH_PATH env var first; falls back to the bundled copy at
    <project_root>/benchmarks/EIDBench.
    """
    raw = os.environ.get("EIDBENCH_PATH", "")
    if raw:
        p = Path(raw).expanduser().resolve()
        if p.is_dir():
            return p

    # Bundled copy: src/prismadv/api/v1/routes/examples.py → ../../../../.. → project root
    bundled = Path(__file__).parents[5] / "benchmarks" / "EIDBench"
    return bundled if bundled.is_dir() else None


def _pick_csv(files_dir: Path) -> str | None:
    """Choose the best CSV file from a dataset's files/ directory.

    Prefers ``*_clean.csv`` if one exists, otherwise picks the first CSV found.
    """
    csvs = sorted(files_dir.glob("*.csv"))
    if not csvs:
        return None
    clean = [c for c in csvs if "_clean" in c.name]
    return (clean[0] if clean else csvs[0]).name


def _display_name(folder_name: str) -> str:
    """Convert a snake_case / mixed folder name to a human-readable title."""
    return folder_name.replace("_", " ").title()


def _strip_assertion_blocks(code: str) -> str:
    """Remove # ASSERTION_START ... # ASSERTION_END ground-truth blocks from code.

    These blocks are benchmark annotations and must not be shown to the LLM.
    """
    result = []
    inside = False
    for line in code.splitlines(keepends=True):
        stripped = line.strip()
        if stripped == "# ASSERTION_START":
            inside = True
            continue
        if stripped == "# ASSERTION_END":
            inside = False
            continue
        if not inside:
            result.append(line)
    return "".join(result)


# Short descriptions shown in the Load from EIDBench dialog
_DATASET_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "hr_analytics": {
        "description": "Employee attrition and HR analytics data. Predict whether employees will leave based on satisfaction scores, performance ratings, workload, and departmental factors.",
        "domain": "HR / Employee Attrition",
        "source": "Kaggle",
    },
    "imdb": {
        "description": "Top 1000 movies and TV shows from IMDb. Analyze ratings, genres, runtime, and box office gross across decades of film and television.",
        "domain": "Entertainment / Media",
        "source": "Kaggle",
    },
    "IPL_win_prediction": {
        "description": "Indian Premier League cricket match records. Predict match outcomes based on team statistics, venue, toss decisions, and in-match conditions.",
        "domain": "Sports Analytics",
        "source": "Kaggle",
    },
    "sleep_health": {
        "description": "Sleep health and lifestyle survey data. Explore relationships between sleep duration, quality, physical activity, stress levels, and health conditions.",
        "domain": "Health & Lifestyle",
        "source": "Kaggle",
    },
    "students": {
        "description": "Student academic performance from a Portuguese higher-education institution. Predict dropout risk and academic success from demographic, socioeconomic, and enrollment factors.",
        "domain": "Education",
        "source": "UCI ML Repository",
    },
}


class EIDBenchDataset(BaseModel):
    name: str
    displayName: str
    csvFile: str
    scripts: list[str]
    description: str = ""
    domain: str = ""
    source: str = ""


class EIDBenchListResponse(BaseModel):
    datasets: list[EIDBenchDataset]


class EIDBenchLoadRequest(BaseModel):
    dataset: str
    script: str


# ─── EIDBench endpoints ───────────────────────────────────────────────────────


@router.get("/eidbench", response_model=EIDBenchListResponse)
async def list_eidbench_datasets() -> EIDBenchListResponse:
    """Return available EIDBench datasets and their scripts.

    Requires the EIDBENCH_PATH environment variable to point at the EIDBench
    root directory (the folder that contains hr_analytics/, imdb/, etc.).
    """
    root = _get_eidbench_root()
    if root is None:
        raise HTTPException(
            status_code=503,
            detail="EIDBench is not configured. Set the EIDBENCH_PATH environment variable.",
        )

    datasets: list[EIDBenchDataset] = []
    for ds_dir in sorted(root.iterdir()):
        if not ds_dir.is_dir() or ds_dir.name.startswith("."):
            continue

        files_dir = ds_dir / "files"
        scripts_dir = ds_dir / "scripts" / "general"

        if not files_dir.is_dir() or not scripts_dir.is_dir():
            continue

        csv_file = _pick_csv(files_dir)
        if csv_file is None:
            continue

        scripts = sorted(p.name for p in scripts_dir.glob("*.py"))
        if not scripts:
            continue

        meta = _DATASET_DESCRIPTIONS.get(ds_dir.name, {})
        datasets.append(
            EIDBenchDataset(
                name=ds_dir.name,
                displayName=_display_name(ds_dir.name),
                csvFile=csv_file,
                scripts=scripts,
                description=meta.get("description", ""),
                domain=meta.get("domain", ""),
                source=meta.get("source", ""),
            )
        )

    return EIDBenchListResponse(datasets=datasets)


@router.post("/eidbench/load")
async def load_eidbench_data(
    request: EIDBenchLoadRequest,
    storage: SessionStorage = dependencies.Depends(dependencies.get_storage),
) -> dict[str, str]:
    """Load a specific EIDBench dataset + script into the current session."""
    root = _get_eidbench_root()
    if root is None:
        raise HTTPException(
            status_code=503,
            detail="EIDBench is not configured. Set the EIDBENCH_PATH environment variable.",
        )

    ds_dir = root / request.dataset
    if not ds_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Dataset '{request.dataset}' not found.")

    # Resolve CSV
    files_dir = ds_dir / "files"
    csv_name = _pick_csv(files_dir)
    if csv_name is None:
        raise HTTPException(status_code=404, detail=f"No CSV found for dataset '{request.dataset}'.")
    csv_path = files_dir / csv_name

    # Resolve script
    script_path = ds_dir / "scripts" / "general" / request.script
    if not script_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Script '{request.script}' not found in dataset '{request.dataset}'.",
        )

    task_code = _strip_assertion_blocks(script_path.read_text(encoding="utf-8"))
    csv_content = csv_path.read_text(encoding="utf-8")

    task_file_id = storage.store_file(
        name=request.script,
        content=task_code,
        metadata={"language": "python", "size": len(task_code)},
    )

    # Store CSV first to get an ID, then profile it for column metadata
    dataset_file_id = storage.store_file(
        name=csv_name,
        content=csv_content,
        metadata={"size": len(csv_content)},
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        profiler = get_profiler(ProfilerBackend.BUILTIN)
        profile_result = profiler.profile_csv(tmp_path, dataset_id=dataset_file_id, dataset_name=csv_name)
        columns_meta = [
            {
                "name": col.name,
                "type": col.type,
                "inferred_type": col.inferred_type,
                "nullable": col.nullable,
            }
            for col in profile_result.dataset.columns
        ]
        # Update the stored file's metadata with profiling results
        stored = storage.get_file(dataset_file_id)
        if stored:
            stored.metadata.update(
                {
                    "row_count": profile_result.dataset.row_count,
                    "column_count": len(columns_meta),
                    "columns": columns_meta,
                }
            )
    except Exception as e:
        logger.warning("Could not profile EIDBench dataset %s: %s", csv_name, e)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    logger.info(
        "Loaded EIDBench data: dataset=%s script=%s task=%s dataset_id=%s",
        request.dataset,
        request.script,
        task_file_id,
        dataset_file_id,
    )

    return {
        "task_file_id": task_file_id,
        "dataset_id": dataset_file_id,
        "message": f"Loaded {request.dataset}/{request.script}",
    }

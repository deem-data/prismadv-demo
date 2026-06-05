"""EIDBench training-data loader for the GEPA optimization module.

Loads (task_script, clean_csv, error_config, v_binary) tuples from the
pre-computed benchmark artefacts in:

  benchmarks/data_processed/{dataset}/general/{error_config_id}/
      output_validation/{task_name}/basic_metrics_evaluation.json
  benchmarks/EIDBench/{dataset}/scripts/general/{task_name}.py
  benchmarks/EIDBench/{dataset}/files/{*_clean.csv | *.csv}
  benchmarks/EIDBench/{dataset}/errors/general_task_{error_config_id}.yaml
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

@dataclass
class TrainingUnit:
    """One (task, data-batch) pair for GEPA optimization."""

    dataset: str
    task_name: str
    error_config_id: int

    # Task code with assertion blocks stripped
    task_script: str

    # Path to the clean CSV (used for constraint generation)
    clean_csv_path: Path

    # Error injection config parsed from YAML (empty list for clean units)
    error_config: list[dict[str, Any]]

    # v_binary: 0 = task fails on error-injected data, 1 = clean baseline
    v_binary: int


# ---------------------------------------------------------------------------
# Assertion-block stripping (mirrors routes/examples.py _strip_assertion_blocks)
# ---------------------------------------------------------------------------

def _strip_assertion_blocks(code: str) -> str:
    lines = code.splitlines()
    out: list[str] = []
    inside = False
    for line in lines:
        stripped = line.strip()
        if stripped == "# ASSERTION_START":
            inside = True
            continue
        if stripped == "# ASSERTION_END":
            inside = False
            continue
        if not inside:
            out.append(line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CSV picker (mirrors routes/examples.py _pick_csv)
# ---------------------------------------------------------------------------

def _pick_csv(files_dir: Path) -> Path | None:
    csvs = sorted(files_dir.glob("*.csv"))
    if not csvs:
        return None
    # Prefer *_clean.csv
    clean = [p for p in csvs if p.stem.endswith("_clean")]
    return clean[0] if clean else csvs[0]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class EIDBenchLoader:
    """Discover and load GEPA training units from the EIDBench benchmark."""

    def __init__(self, repo_root: Path | None = None):
        """
        Args:
            repo_root: Repository root. Defaults to the parent of this file's
                       package (i.e., the prismadv-demo directory).
        """
        if repo_root is None:
            # src/prismadv/optimization/training.py → go up 4 levels to repo root
            repo_root = Path(__file__).parent.parent.parent.parent
        self._root = repo_root
        self._eidbench = repo_root / "benchmarks" / "EIDBench"
        self._processed = repo_root / "benchmarks" / "data_processed"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_training_units(
        self,
        dataset: str,
        max_units: int = 60,
        include_clean: bool = True,
    ) -> list[TrainingUnit]:
        """Load training units for one EIDBench dataset.

        Args:
            dataset: Dataset folder name (e.g. "IPL_win_prediction")
            max_units: Maximum total units to return (split roughly evenly
                       between corrupted and clean if include_clean=True)
            include_clean: If True, also include clean-baseline units (v=1)

        Returns:
            List of TrainingUnit objects, all corrupted units first, then clean.
        """
        corrupted = self._load_corrupted_units(dataset)
        if include_clean:
            clean = self._load_clean_units(dataset, corrupted)
        else:
            clean = []

        # Interleave corrupted and clean then cap
        combined: list[TrainingUnit] = []
        ci, di = 0, 0
        while len(combined) < max_units and (ci < len(corrupted) or di < len(clean)):
            if ci < len(corrupted):
                combined.append(corrupted[ci]); ci += 1
            if di < len(clean) and len(combined) < max_units:
                combined.append(clean[di]); di += 1

        logger.info(
            "Loaded %d training units for %r (%d corrupted, %d clean)",
            len(combined), dataset, ci, di,
        )
        return combined

    def list_available_datasets(self) -> list[str]:
        """Return dataset names that have both EIDBench scripts and processed labels."""
        if not self._eidbench.exists():
            return []
        return [
            d.name
            for d in self._eidbench.iterdir()
            if d.is_dir() and (d / "scripts" / "general").exists()
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_corrupted_units(self, dataset: str) -> list[TrainingUnit]:
        """Load units where the task fails on the corrupted data (v=0)."""
        units: list[TrainingUnit] = []

        processed_dir = self._processed / dataset / "general"
        eidbench_dir = self._eidbench / dataset

        if not processed_dir.exists() or not eidbench_dir.exists():
            logger.warning("No processed data for dataset %r", dataset)
            return units

        clean_csv = _pick_csv(eidbench_dir / "files")
        if clean_csv is None:
            logger.warning("No CSV found in %s", eidbench_dir / "files")
            return units

        # Error configs 1–25 (index 0 is placeholder)
        for error_id in range(1, 26):
            error_dir = processed_dir / str(error_id)
            if not error_dir.exists():
                continue

            error_yaml_path = eidbench_dir / "errors" / f"general_task_{error_id}.yaml"
            if not error_yaml_path.exists():
                continue

            try:
                error_config = yaml.safe_load(error_yaml_path.read_text()) or []
            except Exception as exc:
                logger.warning("Failed to parse error config %s: %s", error_yaml_path, exc)
                continue

            validation_dir = error_dir / "output_validation"
            if not validation_dir.exists():
                continue

            for task_dir in validation_dir.iterdir():
                if not task_dir.is_dir():
                    continue
                task_name = task_dir.name
                label_file = task_dir / "basic_metrics_evaluation.json"
                if not label_file.exists():
                    continue

                try:
                    label = json.loads(label_file.read_text())
                except Exception:
                    continue

                # We want units where:
                # - clean data is safe (no false alarms on baseline)
                # - corrupted data causes task failure (informative signal)
                if not label.get("clean_data_is_safe", True):
                    continue
                if label.get("corrupted_data_is_safe", True):
                    continue

                script_path = eidbench_dir / "scripts" / "general" / f"{task_name}.py"
                if not script_path.exists():
                    continue

                task_script = _strip_assertion_blocks(script_path.read_text())

                units.append(TrainingUnit(
                    dataset=dataset,
                    task_name=task_name,
                    error_config_id=error_id,
                    task_script=task_script,
                    clean_csv_path=clean_csv,
                    error_config=error_config,
                    v_binary=0,
                ))

        return units

    def _load_clean_units(
        self,
        dataset: str,
        corrupted: list[TrainingUnit],
    ) -> list[TrainingUnit]:
        """Create clean-baseline units (v=1) for each unique task in corrupted."""
        seen_tasks: set[str] = set()
        clean_units: list[TrainingUnit] = []

        for unit in corrupted:
            if unit.task_name in seen_tasks:
                continue
            seen_tasks.add(unit.task_name)
            clean_units.append(TrainingUnit(
                dataset=unit.dataset,
                task_name=unit.task_name,
                error_config_id=0,
                task_script=unit.task_script,
                clean_csv_path=unit.clean_csv_path,
                error_config=[],
                v_binary=1,
            ))

        return clean_units

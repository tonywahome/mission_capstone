"""
Experiment tracking — capstone research proposal Section 3.7
("Reproducibility and Experiment Tracking").

The proposal commits to recording, for every model-training run: dataset
version, feature stack, hyperparameters, random seed, spatial-block split
IDs, evaluation metrics, and an output-map reference. This module is a
small, dependency-light (stdlib-only) logger that writes one structured
JSON record per run plus a flat CSV index, so a reviewer or auditor can
reconstruct exactly what produced a given model artifact without re-running
training.

Wired into backend/ml/train_biomass_model.py's main() — see that file for
the call site. This module does NOT alter training logic, hyperparameters,
random seeds, or data in any way; it is a pure logging side-effect invoked
once at the end of a run, after the model has already been fit and saved.

Usage:

    from services.experiment_tracker import log_run

    run_id = log_run(
        dataset_path="data/sentinel_gedi_training_v2.csv",
        dataset_version="v2",
        feature_stack=features,
        model_type="XGBoost",
        hyperparameters=model.get_params(),
        random_seed=42,
        spatial_block_ids=sorted(blocks.unique().tolist()),
        cv_folds=5,
        metrics={"r2": 0.71, "mae": 12.3, "rmse": 18.9, "bias": -0.4},
        output_model_path="models/biomass_model_v1.pkl",
    )

Records are append-only: each call creates a new, timestamped JSON file
under backend/ml/experiment_runs/ and appends one row to runs_index.csv.
Nothing is ever overwritten or deleted by this module.
"""
from __future__ import annotations

import csv
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

# Per-run JSON records and the flat CSV index live alongside the model
# artifacts they describe (backend/ml/models/), under backend/ml/.
RUNS_DIR = Path(__file__).resolve().parent.parent / "ml" / "experiment_runs"
RUNS_INDEX_CSV = RUNS_DIR / "runs_index.csv"

CSV_FIELDS = [
    "run_id", "timestamp", "model_type", "dataset_version", "n_features",
    "random_seed", "cv_folds", "n_spatial_blocks", "r2", "mae", "rmse",
    "bias", "output_model_path", "notes",
]


def _ensure_runs_dir() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def log_run(
    dataset_path: str,
    dataset_version: str,
    feature_stack: Sequence[str],
    model_type: str,
    hyperparameters: Dict[str, Any],
    random_seed: Optional[int],
    spatial_block_ids: Sequence[str],
    cv_folds: int,
    metrics: Dict[str, float],
    output_model_path: Optional[str] = None,
    output_map_reference: Optional[str] = None,
    notes: str = "",
) -> str:
    """
    Append one structured experiment-run record (Section 3.7). Returns the
    generated run_id.

    `output_map_reference` is for a future dashboard-generated biomass map
    artifact (Section 3.3.4) — the capstone's current training script does
    not yet produce one, so this is None until that feature exists; passing
    a path/identifier once it does requires no schema change here.
    """
    _ensure_runs_dir()

    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    record = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_path": dataset_path,
        "dataset_version": dataset_version,
        "feature_stack": list(feature_stack),
        "model_type": model_type,
        "hyperparameters": hyperparameters,
        "random_seed": random_seed,
        "spatial_block_ids": list(spatial_block_ids),
        "cv_folds": cv_folds,
        "metrics": metrics,
        "output_model_path": output_model_path,
        "output_map_reference": output_map_reference,
        "notes": notes,
    }

    record_path = RUNS_DIR / f"{run_id}.json"
    with open(record_path, "w") as fh:
        json.dump(record, fh, indent=2, default=str)

    _append_csv_index(record)

    logger.info(f"Experiment run logged: {run_id} -> {record_path}")
    return run_id


def _append_csv_index(record: Dict[str, Any]) -> None:
    """Append a flattened summary row to the CSV index, writing the header
    first if the file doesn't exist yet."""
    is_new = not RUNS_INDEX_CSV.exists()
    metrics = record.get("metrics") or {}
    row = {
        "run_id": record["run_id"],
        "timestamp": record["timestamp"],
        "model_type": record["model_type"],
        "dataset_version": record["dataset_version"],
        "n_features": len(record["feature_stack"]),
        "random_seed": record["random_seed"],
        "cv_folds": record["cv_folds"],
        "n_spatial_blocks": len(record["spatial_block_ids"]),
        "r2": metrics.get("r2"),
        "mae": metrics.get("mae"),
        "rmse": metrics.get("rmse"),
        "bias": metrics.get("bias"),
        "output_model_path": record.get("output_model_path"),
        "notes": record.get("notes", ""),
    }
    with open(RUNS_INDEX_CSV, "a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def list_runs() -> List[Dict[str, Any]]:
    """
    Read back all logged runs' full JSON records, oldest first. Intended
    for the dashboard's audit-trail / dMRV-traceability view (proposal
    Section 3.5) and for anyone reconstructing a model artifact's training
    provenance during the expert-review evaluation (Section 3.8).
    """
    if not RUNS_DIR.exists():
        return []
    records = []
    for path in sorted(RUNS_DIR.glob("*.json")):
        try:
            with open(path) as fh:
                records.append(json.load(fh))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Skipping unreadable experiment run record {path}: {e}")
    return records

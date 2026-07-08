"""
Dataset training endpoints — upload CSV, EDA, train models, leaderboard.
"""
import json
import logging
import uuid
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.core.config import settings
from backend.core.database import get_db
from backend.ml.training import DatasetTrainingPipeline
from backend.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/training", tags=["ML Training"])

# In-memory state (use Redis/DB in production)
_datasets: Dict[str, Dict] = {}
_training_jobs: Dict[str, Dict] = {}
_leaderboard: Dict[str, Any] = {}


class TrainRequest(BaseModel):
    dataset_id: str
    target_col: str
    drop_cols: Optional[List[str]] = None


class TrainingStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    leaderboard: Optional[Dict] = None
    best_model: Optional[str] = None
    error: Optional[str] = None


# ── Dataset Upload ────────────────────────────────────────────────────────────

@router.post("/upload-dataset")
async def upload_dataset(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".csv", ".xlsx"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Only CSV/XLSX accepted")

    content = await file.read()
    dataset_id = str(uuid.uuid4())[:8]
    save_path = settings.DATASET_DIR / f"{dataset_id}_{file.filename}"
    save_path.write_bytes(content)

    pipeline = DatasetTrainingPipeline(output_dir=settings.TRAINED_DIR)
    df = pipeline.load_dataset(str(save_path))
    analysis = pipeline.analyze_dataset(df)

    _datasets[dataset_id] = {
        "id": dataset_id,
        "filename": file.filename,
        "filepath": str(save_path),
        "analysis": analysis,
    }

    return {
        "dataset_id": dataset_id,
        "filename": file.filename,
        "rows": analysis["rows"],
        "columns": analysis["columns"],
        "column_names": analysis["column_names"],
        "missing_values": analysis["missing_values"],
        "category_counts": analysis["category_counts"],
    }


@router.get("/datasets")
async def list_datasets(current_user: User = Depends(get_current_user)):
    return list(_datasets.values())


@router.post("/analyze/{dataset_id}")
async def analyze_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
):
    if dataset_id not in _datasets:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
    ds = _datasets[dataset_id]
    pipeline = DatasetTrainingPipeline(output_dir=settings.TRAINED_DIR)
    df = pipeline.load_dataset(ds["filepath"])
    df = pipeline.clean_dataset(df)
    analysis = pipeline.analyze_dataset(df)
    ds["analysis"] = analysis
    return analysis


# ── Training ──────────────────────────────────────────────────────────────────

@router.post("/train", response_model=TrainingStatus)
async def start_training(
    body: TrainRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    if body.dataset_id not in _datasets:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")

    job_id = str(uuid.uuid4())[:8]
    _training_jobs[job_id] = {"status": "queued", "progress": 0}

    background_tasks.add_task(
        _run_training_job, job_id, body.dataset_id, body.target_col, body.drop_cols or []
    )

    return TrainingStatus(job_id=job_id, status="queued", progress=0)


async def _run_training_job(job_id: str, dataset_id: str, target_col: str, drop_cols: List[str]):
    """Background task: run the full training pipeline."""
    try:
        _training_jobs[job_id] = {"status": "running", "progress": 10}
        ds = _datasets[dataset_id]

        pipeline = DatasetTrainingPipeline(output_dir=settings.TRAINED_DIR)
        df = pipeline.load_dataset(ds["filepath"])
        _training_jobs[job_id]["progress"] = 20

        df = pipeline.clean_dataset(df)
        _training_jobs[job_id]["progress"] = 30

        X, y, feature_names = pipeline.prepare_features(df, target_col, drop_cols)
        _training_jobs[job_id]["progress"] = 50

        leaderboard = pipeline.train_all_models(X, y)
        _training_jobs[job_id]["progress"] = 85

        save_path = pipeline.save_best_model()
        _training_jobs[job_id]["progress"] = 95

        _leaderboard[job_id] = {
            "leaderboard": leaderboard,
            "best_model": pipeline.best_model_name,
            "feature_names": feature_names,
        }

        _training_jobs[job_id] = {
            "status": "completed",
            "progress": 100,
            "leaderboard": leaderboard,
            "best_model": pipeline.best_model_name,
        }
        logger.info("Training job %s completed. Best: %s", job_id, pipeline.best_model_name)

    except Exception as exc:
        logger.error("Training job %s failed: %s", job_id, exc)
        _training_jobs[job_id] = {"status": "failed", "progress": 0, "error": str(exc)}


@router.get("/status/{job_id}", response_model=TrainingStatus)
async def training_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    if job_id not in _training_jobs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Training job not found")
    j = _training_jobs[job_id]
    return TrainingStatus(
        job_id=job_id,
        status=j.get("status", "unknown"),
        progress=j.get("progress", 0),
        leaderboard=j.get("leaderboard"),
        best_model=j.get("best_model"),
        error=j.get("error"),
    )


@router.get("/leaderboard")
async def get_leaderboard(current_user: User = Depends(get_current_user)):
    if not _leaderboard:
        # Try loading from disk
        meta_path = settings.TRAINED_DIR / "model_meta.json"
        if meta_path.exists():
            data = json.loads(meta_path.read_text())
            return {
                "best_model": data.get("model_name"),
                "leaderboard": {data.get("model_name", "?"): data.get("metrics", {})},
            }
        return {"message": "No training runs found", "leaderboard": {}}

    # Return latest job's leaderboard
    latest = list(_leaderboard.values())[-1]
    return latest


@router.get("/feature-importance/{job_id}")
async def feature_importance(
    job_id: str,
    model_name: str = Query(...),
    current_user: User = Depends(get_current_user),
):
    data = _leaderboard.get(job_id)
    if not data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Training job not found or no results")
    lb = data.get("leaderboard", {})
    model_metrics = lb.get(model_name, {})
    return {
        "model": model_name,
        "feature_importance": model_metrics.get("feature_importance", {}),
    }

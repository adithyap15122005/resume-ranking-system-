"""
Production Model Registry — manages deployment status of ML models.
Always ensures exactly one production model is active at any time.
"""
import logging
import pickle
from pathlib import Path
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings

logger = logging.getLogger(__name__)


async def get_production_model(db: AsyncSession) -> Optional[dict]:
    """Return the current production model record as a dict, or None."""
    from backend.models.ml_model import MLModel

    result = await db.execute(
        select(MLModel).where(MLModel.deployment_status == "production").limit(1)
    )
    model = result.scalars().first()
    if model is None:
        return None
    return _model_to_dict(model)


async def set_production_model(model_id: str, db: AsyncSession) -> dict:
    """
    Atomically promote one model to production.
    Demotes the current production model to 'archived'.
    """
    from backend.models.ml_model import MLModel
    from datetime import datetime, timezone

    # Demote any current production models
    await db.execute(
        update(MLModel)
        .where(MLModel.deployment_status == "production")
        .values(deployment_status="archived")
    )

    # Promote the chosen model
    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalars().first()
    if model is None:
        raise ValueError(f"Model {model_id} not found")

    model.deployment_status = "production"
    model.deployed_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info("Model %s (%s) promoted to production", model.id, model.algorithm)
    return _model_to_dict(model)


async def set_experimental_model(model_id: str, db: AsyncSession) -> dict:
    """Mark a model as experimental (available to recruiters as alternative)."""
    from backend.models.ml_model import MLModel

    # Demote any existing experimental model
    await db.execute(
        update(MLModel)
        .where(MLModel.deployment_status == "experimental")
        .values(deployment_status="archived")
    )

    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalars().first()
    if model is None:
        raise ValueError(f"Model {model_id} not found")

    model.deployment_status = "experimental"
    await db.flush()
    return _model_to_dict(model)


def load_model_artifact(model_path: str):
    """Load a pickled sklearn model from disk. Returns None if not found."""
    path = Path(model_path)
    if not path.exists():
        logger.warning("Model artifact not found: %s", model_path)
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as exc:
        logger.error("Failed to load model artifact %s: %s", model_path, exc)
        return None


def _model_to_dict(model) -> dict:
    return {
        "id": model.id,
        "name": model.name,
        "version": model.version,
        "algorithm": model.algorithm,
        "status": model.status,
        "deployment_status": model.deployment_status,
        "accuracy": model.accuracy,
        "precision_score": model.precision_score,
        "recall_score": model.recall_score,
        "f1_score": model.f1_score,
        "roc_auc": model.roc_auc,
        "inference_time_ms": model.inference_time_ms,
        "training_time_s": model.training_time_s,
        "model_size_mb": model.model_size_mb,
        "dataset_id": model.dataset_id,
        "experiment_id": model.experiment_id,
        "feature_count": model.feature_count,
        "training_samples": model.training_samples,
        "target_column": model.target_column,
        "model_path": model.model_path,
        "hyperparameters": model.hyperparameters,
        "feature_importance": model.feature_importance,
        "confusion_matrix_data": model.confusion_matrix_data,
        "class_labels": model.class_labels,
        "feature_names": model.feature_names,
        "mlflow_run_id": model.mlflow_run_id,
        "created_at": model.created_at.isoformat() if model.created_at else None,
        "trained_at": model.trained_at.isoformat() if model.trained_at else None,
        "deployed_at": model.deployed_at.isoformat() if model.deployed_at else None,
        "organization_id": model.organization_id,
        "description": model.description,
    }

"""
Production Model Registry — manages deployment status of ML models.
Always ensures exactly one production model is active at any time.
"""
import json
import logging
from pathlib import Path
from typing import Optional

import joblib
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

    await db.execute(
        update(MLModel)
        .where(MLModel.deployment_status == "production")
        .values(deployment_status="archived")
    )

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
    """Mark a model as experimental (available as alternative)."""
    from backend.models.ml_model import MLModel

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


def load_full_artifact(artifact_path: str) -> Optional[dict]:
    """
    Load the full model bundle from an artifact directory (new format) or a
    legacy single .pkl file (old format).

    Returns a dict with keys:
        model          — trained sklearn/xgboost/lgbm classifier
        preprocessor   — fitted StandardScaler (None if legacy)
        label_encoder  — fitted LabelEncoder (None if missing)
        feature_names  — list[str] of feature column names
        feature_count  — int
    Returns None if the artifact cannot be loaded.
    """
    path = Path(artifact_path)

    # ── New directory bundle format ──────────────────────────────────────────
    if path.is_dir():
        model_file = path / "model.pkl"
        if not model_file.exists():
            logger.warning("model.pkl missing in artifact dir: %s", path)
            return None
        try:
            model = joblib.load(model_file)
            preprocessor = (
                joblib.load(path / "preprocessor.pkl")
                if (path / "preprocessor.pkl").exists() else None
            )
            label_encoder = (
                joblib.load(path / "label_encoder.pkl")
                if (path / "label_encoder.pkl").exists() else None
            )
            meta: dict = {}
            meta_file = path / "feature_metadata.json"
            if meta_file.exists():
                meta = json.loads(meta_file.read_text())
            return {
                "model": model,
                "preprocessor": preprocessor,
                "label_encoder": label_encoder,
                "feature_names": meta.get("feature_names", []),
                "feature_count": meta.get("feature_count", 0),
            }
        except Exception as exc:
            logger.error("Failed to load artifact bundle %s: %s", path, exc)
            return None

    # ── Legacy single .pkl format ────────────────────────────────────────────
    if path.exists() and path.suffix == ".pkl":
        try:
            data = joblib.load(str(path))
            feature_cols = data.get("feature_cols", [])
            return {
                "model": data.get("model"),
                "preprocessor": None,        # old format had no saved scaler
                "label_encoder": data.get("label_encoder"),
                "feature_names": feature_cols,
                "feature_count": len(feature_cols),
            }
        except Exception as exc:
            logger.error("Failed to load legacy artifact %s: %s", path, exc)
            return None

    logger.warning("Artifact not found at path: %s", artifact_path)
    return None


def load_model_artifact(model_path: str):
    """Legacy shim — use load_full_artifact() for new code."""
    result = load_full_artifact(model_path)
    return result.get("model") if result else None


def validate_feature_vector(features, artifact: dict) -> bool:
    """
    Check that the feature vector dimension matches the trained model.
    Logs a warning and returns False on mismatch so callers can fall back.
    """
    expected = artifact.get("feature_count") or len(artifact.get("feature_names") or [])
    if expected == 0:
        return True  # unknown — allow through
    actual = features.shape[-1] if hasattr(features, "shape") else len(features)
    if actual != expected:
        logger.warning(
            "Feature dim mismatch: model expects %d, got %d — fallback to traditional",
            expected, actual,
        )
        return False
    return True


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

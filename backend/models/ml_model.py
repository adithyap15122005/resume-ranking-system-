"""ML Model Registry — tracks trained models, deployment status, and metrics."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base

try:
    from sqlalchemy.dialects.sqlite import JSON
except ImportError:
    from sqlalchemy import JSON


class MLModel(Base):
    __tablename__ = "ml_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0.0")
    algorithm: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="trained")
    # production | experimental | archived
    deployment_status: Mapped[str] = mapped_column(String(50), default="experimental")

    # Performance metrics (all 0-1 or 0-100ms)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    precision_score: Mapped[float] = mapped_column(Float, default=0.0)
    recall_score: Mapped[float] = mapped_column(Float, default=0.0)
    f1_score: Mapped[float] = mapped_column(Float, default=0.0)
    roc_auc: Mapped[float] = mapped_column(Float, default=0.0)
    inference_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    training_time_s: Mapped[float] = mapped_column(Float, default=0.0)
    model_size_mb: Mapped[float] = mapped_column(Float, default=0.0)

    # Training lineage
    dataset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    experiment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    feature_count: Mapped[int] = mapped_column(Integer, default=0)
    training_samples: Mapped[int] = mapped_column(Integer, default=0)
    target_column: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Persisted artifact path
    model_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Rich JSON metadata
    hyperparameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    feature_importance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confusion_matrix_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    class_labels: Mapped[list | None] = mapped_column(JSON, nullable=True)
    feature_names: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # MLflow tracking (optional)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mlflow_experiment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Ownership
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

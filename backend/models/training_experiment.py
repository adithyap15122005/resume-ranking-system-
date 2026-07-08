"""Training Experiment — a multi-model training run tracking progress and results."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base

try:
    from sqlalchemy.dialects.sqlite import JSON
except ImportError:
    from sqlalchemy import JSON


class TrainingExperiment(Base):
    __tablename__ = "training_experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # queued | running | completed | failed
    status: Mapped[str] = mapped_column(String(50), default="queued")

    # Configuration
    target_column: Mapped[str] = mapped_column(String(200), nullable=False)
    feature_columns: Mapped[list | None] = mapped_column(JSON, nullable=True)
    algorithms: Mapped[list | None] = mapped_column(JSON, nullable=True)
    hyperparameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Results — populated as training completes
    model_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    best_model_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Live progress
    current_algorithm: Mapped[str | None] = mapped_column(String(100), nullable=True)
    algorithms_completed: Mapped[int] = mapped_column(Integer, default=0)
    algorithms_total: Mapped[int] = mapped_column(Integer, default=0)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional MLflow tracking
    mlflow_experiment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Ownership
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

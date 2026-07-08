"""Training Dataset — uploaded CSV/XLSX files and their analysis results."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base

try:
    from sqlalchemy.dialects.sqlite import JSON
except ImportError:
    from sqlalchemy import JSON


class TrainingDataset(Base):
    __tablename__ = "training_datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    # uploaded | analyzed | engineered | trained
    status: Mapped[str] = mapped_column(String(50), default="uploaded")

    # Basic shape stats
    rows: Mapped[int] = mapped_column(Integer, default=0)
    columns: Mapped[int] = mapped_column(Integer, default=0)
    missing_values: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    target_column: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Auto-detected schema and EDA results
    column_types: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    class_distribution: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    missing_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    correlation_matrix: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    feature_importance_eda: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    outliers_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    data_preview: Mapped[list | None] = mapped_column(JSON, nullable=True)  # first 20 rows as dicts
    column_stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # per-column stats

    # Feature engineering results
    engineered_feature_count: Mapped[int] = mapped_column(Integer, default=0)
    original_feature_count: Mapped[int] = mapped_column(Integer, default=0)
    engineering_steps: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    engineered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Ownership
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

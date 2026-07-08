"""Hiring Outcome — stores recruiter decisions for continuous learning loop."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class HiringOutcome(Base):
    __tablename__ = "hiring_outcomes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Links to other models
    resume_id: Mapped[str] = mapped_column(String(36), ForeignKey("resumes.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("job_descriptions.id"), nullable=False)
    ranking_result_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Recruiter decision
    interview_score: Mapped[float] = mapped_column(Float, default=0.0)
    # hired | rejected | no_show | pending
    hiring_decision: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    offer_extended: Mapped[bool] = mapped_column(Boolean, default=False)
    offer_accepted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Post-hire performance (filled weeks/months later)
    employee_performance: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    retention_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

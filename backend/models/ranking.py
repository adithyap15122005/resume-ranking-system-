"""Enhanced Ranking Result ORM model with pipeline and explainability."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class RankingResult(Base):
    __tablename__ = "ranking_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True, index=True
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── Score ─────────────────────────────────────────────────────────────────
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    semantic_score: Mapped[float] = mapped_column(Float, default=0.0)
    skill_score: Mapped[float] = mapped_column(Float, default=0.0)
    experience_score: Mapped[float] = mapped_column(Float, default=0.0)
    recommendation: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Skill Analysis ────────────────────────────────────────────────────────
    matched_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    missing_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extra_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ── Explainability (SHAP) ────────────────────────────────────────────────
    shap_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    skill_contributions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    experience_contribution: Mapped[float] = mapped_column(Float, default=0.0)
    education_contribution: Mapped[float] = mapped_column(Float, default=0.0)
    technical_score: Mapped[float] = mapped_column(Float, default=0.0)
    hiring_probability: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Computed Metrics ──────────────────────────────────────────────────────
    keyword_density: Mapped[float] = mapped_column(Float, default=0.0)
    experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Pipeline / Kanban ─────────────────────────────────────────────────────
    pipeline_stage: Mapped[str] = mapped_column(String(50), default="applied")
    is_shortlisted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_rejected: Mapped[bool] = mapped_column(Boolean, default=False)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Interview ─────────────────────────────────────────────────────────────
    interview_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_interview_questions: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Offer ─────────────────────────────────────────────────────────────────
    offer_extended: Mapped[bool] = mapped_column(Boolean, default=False)
    offer_accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # ── Recruiter ─────────────────────────────────────────────────────────────
    recruiter_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    ranked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    job: Mapped["JobDescription"] = relationship("JobDescription", back_populates="rankings")  # noqa: F821
    resume: Mapped["Resume"] = relationship("Resume", back_populates="rankings")  # noqa: F821

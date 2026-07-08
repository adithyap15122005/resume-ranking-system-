"""Enhanced Resume ORM model with AI intelligence fields."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    # ── Identity ──────────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True, index=True
    )
    uploaded_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )

    # ── File ──────────────────────────────────────────────────────────────────
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    filepath: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    file_size_kb: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "parsing", "parsed", "failed", name="resume_status"),
        default="parsed",
        nullable=False,
    )

    # ── Contact ───────────────────────────────────────────────────────────────
    candidate_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── Parsed Content ────────────────────────────────────────────────────────
    skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    education: Mapped[list | None] = mapped_column(JSON, nullable=True)
    experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    projects: Mapped[list | None] = mapped_column(JSON, nullable=True)
    certifications: Mapped[list | None] = mapped_column(JSON, nullable=True)
    languages: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tools: Mapped[list | None] = mapped_column(JSON, nullable=True)
    achievements: Mapped[list | None] = mapped_column(JSON, nullable=True)
    publications: Mapped[list | None] = mapped_column(JSON, nullable=True)
    hackathons: Mapped[list | None] = mapped_column(JSON, nullable=True)
    open_source: Mapped[list | None] = mapped_column(JSON, nullable=True)
    soft_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ── Text ──────────────────────────────────────────────────────────────────
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cleaned_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Computed Metrics ──────────────────────────────────────────────────────
    experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Embeddings ────────────────────────────────────────────────────────────
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ── AI Intelligence ───────────────────────────────────────────────────────
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[list | None] = mapped_column(JSON, nullable=True)
    weaknesses: Mapped[list | None] = mapped_column(JSON, nullable=True)
    career_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    technical_score: Mapped[float] = mapped_column(Float, default=0.0)
    leadership_score: Mapped[float] = mapped_column(Float, default=0.0)
    communication_score: Mapped[float] = mapped_column(Float, default=0.0)
    job_readiness: Mapped[float] = mapped_column(Float, default=0.0)
    culture_fit: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    predicted_salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Recruiter Actions ─────────────────────────────────────────────────────
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    rankings: Mapped[list["RankingResult"]] = relationship(  # noqa: F821
        "RankingResult", back_populates="resume", cascade="all, delete-orphan"
    )

"""Enhanced Job Description ORM model."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True, index=True
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )

    # ── Job Details ───────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    employment_type: Mapped[str] = mapped_column(
        Enum("full_time", "part_time", "contract", "internship", name="employment_type"),
        default="full_time",
        nullable=False,
    )
    experience_level: Mapped[str] = mapped_column(
        Enum("entry", "mid", "senior", "lead", "executive", name="experience_level"),
        default="mid",
        nullable=False,
    )
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("draft", "active", "paused", "closed", name="job_status"),
        default="active",
        nullable=False,
    )

    # ── Content ───────────────────────────────────────────────────────────────
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filepath: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Skills ────────────────────────────────────────────────────────────────
    required_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    preferred_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    responsibilities: Mapped[list | None] = mapped_column(JSON, nullable=True)
    qualifications: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ── Requirements ──────────────────────────────────────────────────────────
    education_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    experience_requirement: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Pipeline ──────────────────────────────────────────────────────────────
    pipeline_stages: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ── Embeddings ────────────────────────────────────────────────────────────
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    rankings: Mapped[list["RankingResult"]] = relationship(  # noqa: F821
        "RankingResult", back_populates="job", cascade="all, delete-orphan"
    )

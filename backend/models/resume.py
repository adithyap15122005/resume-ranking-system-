from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    file_hash = Column(String(64), unique=True, nullable=False, index=True)

    # Parsed fields
    candidate_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    skills = Column(JSON, default=list)
    education = Column(JSON, default=list)
    experience = Column(Text)
    projects = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    languages = Column(JSON, default=list)
    tools = Column(JSON, default=list)

    # Derived metrics
    raw_text = Column(Text)
    cleaned_text = Column(Text)
    experience_years = Column(Float, default=0.0)
    completeness_score = Column(Float, default=0.0)

    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    rankings = relationship("RankingResult", back_populates="resume", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "filepath": self.filepath,
            "candidate_name": self.candidate_name,
            "email": self.email,
            "phone": self.phone,
            "skills": self.skills or [],
            "education": self.education or [],
            "experience": self.experience,
            "projects": self.projects or [],
            "certifications": self.certifications or [],
            "languages": self.languages or [],
            "tools": self.tools or [],
            "raw_text": self.raw_text,
            "cleaned_text": self.cleaned_text,
            "experience_years": self.experience_years,
            "completeness_score": self.completeness_score,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }

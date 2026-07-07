from sqlalchemy import Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255))
    filepath = Column(String(500))

    raw_text = Column(Text, nullable=False)
    cleaned_text = Column(Text)

    required_skills = Column(JSON, default=list)
    preferred_skills = Column(JSON, default=list)
    education_requirement = Column(String(255))
    experience_requirement = Column(String(255))

    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    rankings = relationship("RankingResult", back_populates="job", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "filename": self.filename,
            "raw_text": self.raw_text,
            "cleaned_text": self.cleaned_text,
            "required_skills": self.required_skills or [],
            "preferred_skills": self.preferred_skills or [],
            "education_requirement": self.education_requirement,
            "experience_requirement": self.experience_requirement,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }

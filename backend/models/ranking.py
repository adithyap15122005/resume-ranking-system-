from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class RankingResult(Base):
    __tablename__ = "ranking_results"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)

    rank = Column(Integer, nullable=False)
    similarity_score = Column(Float, nullable=False)
    matched_skills = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    extra_skills = Column(JSON, default=list)
    recommendation = Column(String(50))
    quality_score = Column(Float, default=0.0)
    keyword_density = Column(Float, default=0.0)
    experience_years = Column(Float, default=0.0)

    ranked_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    job = relationship("JobDescription", back_populates="rankings")
    resume = relationship("Resume", back_populates="rankings")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "resume_id": self.resume_id,
            "rank": self.rank,
            "similarity_score": self.similarity_score,
            "matched_skills": self.matched_skills or [],
            "missing_skills": self.missing_skills or [],
            "extra_skills": self.extra_skills or [],
            "recommendation": self.recommendation,
            "quality_score": self.quality_score,
            "keyword_density": self.keyword_density,
            "experience_years": self.experience_years,
            "ranked_at": self.ranked_at.isoformat() if self.ranked_at else None,
            "candidate_name": self.resume.candidate_name if self.resume else None,
            "filename": self.resume.filename if self.resume else None,
        }

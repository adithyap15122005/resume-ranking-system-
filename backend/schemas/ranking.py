from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class RankingEntryResponse(BaseModel):
    rank: int
    resume_id: int
    candidate_name: Optional[str] = None
    filename: str
    similarity_score: float
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    extra_skills: List[str] = []
    recommendation: str
    quality_score: float = 0.0
    keyword_density: float = 0.0
    experience_years: float = 0.0

    model_config = {"from_attributes": True}


class RankingResponse(BaseModel):
    job_id: int
    job_title: str
    total_resumes: int
    results: List[RankingEntryResponse]
    ranked_at: Optional[datetime] = None


class RankingHistoryItem(BaseModel):
    job_id: int
    job_title: str
    total_resumes: int
    top_candidate: Optional[str] = None
    top_score: Optional[float] = None
    ranked_at: Optional[datetime] = None

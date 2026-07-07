from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str
    raw_text: str
    filename: Optional[str] = None
    filepath: Optional[str] = None
    cleaned_text: str = ""
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    education_requirement: Optional[str] = None
    experience_requirement: Optional[str] = None


class JobResponse(BaseModel):
    id: int
    title: str
    filename: Optional[str] = None
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    education_requirement: Optional[str] = None
    experience_requirement: Optional[str] = None
    uploaded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

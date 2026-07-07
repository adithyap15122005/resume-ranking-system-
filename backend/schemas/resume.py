from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ParsedResumeData(BaseModel):
    """Raw output from ResumeParser.parse()"""
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    experience: Optional[str] = None
    projects: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    raw_text: str = ""
    experience_years: float = 0.0
    completeness_score: float = 0.0


class ResumeCreate(ParsedResumeData):
    filename: str
    filepath: str
    file_hash: str
    cleaned_text: str = ""


class ResumeResponse(BaseModel):
    id: int
    filename: str
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = []
    education: List[str] = []
    experience: Optional[str] = None
    projects: List[str] = []
    certifications: List[str] = []
    languages: List[str] = []
    tools: List[str] = []
    experience_years: float = 0.0
    completeness_score: float = 0.0
    uploaded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ResumeList(BaseModel):
    resumes: List[ResumeResponse]
    total: int

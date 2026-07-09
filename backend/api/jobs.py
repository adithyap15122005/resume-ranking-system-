"""
Job description management and ranking pipeline endpoints.
"""
import logging
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.core.database import get_db
from backend.ml.embeddings import embedding_service
from backend.ml.ranking_engine import ranking_engine
from backend.models.job import JobDescription
from backend.models.ranking import RankingResult
from backend.models.resume import Resume
from backend.models.user import User
from backend.utils.resume_parser import ResumeParser
from backend.utils.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

parser = ResumeParser()
cleaner = TextCleaner()


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateJobRequest(BaseModel):
    title: str
    description: str
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: str = "full_time"
    experience_level: str = "mid"
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    experience_requirement: Optional[str] = None
    education_requirement: Optional[str] = None
    responsibilities: List[str] = []
    qualifications: List[str] = []


class UpdateJobRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None


class JobOut(BaseModel):
    id: str
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: str = "full_time"
    experience_level: str = "mid"
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    status: str = "active"
    description: Optional[str] = None
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    responsibilities: List[str] = []
    qualifications: List[str] = []
    experience_requirement: Optional[str] = None
    education_requirement: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    candidate_count: int = 0

    model_config = {"from_attributes": True}


class RankingOut(BaseModel):
    id: str
    resume_id: str
    job_id: str
    rank: int
    # similarity_score is 0–100; component scores are 0–1
    similarity_score: float
    semantic_score: float = 0.0
    skill_score: float = 0.0
    experience_score: float = 0.0
    recommendation: Optional[str] = None
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    extra_skills: List[str] = []
    shap_values: Optional[Dict[str, Any]] = None
    skill_contributions: Optional[Dict[str, float]] = None
    experience_contribution: float = 0.0
    technical_score: float = 0.0
    hiring_probability: float = 0.0
    keyword_density: float = 0.0
    experience_years: float = 0.0
    pipeline_stage: str = "applied"
    is_shortlisted: bool = False
    recruiter_notes: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_skills: List[str] = []
    filename: Optional[str] = None
    ranked_at: datetime

    model_config = {"from_attributes": True}


class UpdatePipelineRequest(BaseModel):
    stage: str
    recruiter_notes: Optional[str] = None


class MovePipelineRequest(BaseModel):
    pipeline_stage: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _job_to_out(j: JobDescription, candidate_count: int = 0) -> JobOut:
    return JobOut(
        id=j.id,
        title=j.title,
        department=j.department,
        location=j.location,
        employment_type=j.employment_type or "full_time",
        experience_level=j.experience_level or "mid",
        salary_min=j.salary_min,
        salary_max=j.salary_max,
        status=j.status or "active",
        description=j.description or j.raw_text[:500] if j.raw_text else None,
        required_skills=j.required_skills or [],
        preferred_skills=j.preferred_skills or [],
        responsibilities=j.responsibilities or [],
        qualifications=j.qualifications or [],
        experience_requirement=j.experience_requirement,
        education_requirement=j.education_requirement,
        created_at=j.created_at,
        updated_at=j.updated_at,
        candidate_count=candidate_count,
    )


def _ranking_out(rrow: "RankingResult", resume: "Resume | None") -> "RankingOut":  # noqa: F821
    return RankingOut(
        id=rrow.id,
        resume_id=rrow.resume_id,
        job_id=rrow.job_id,
        rank=rrow.rank,
        similarity_score=rrow.similarity_score or 0.0,
        semantic_score=rrow.semantic_score or 0.0,
        skill_score=rrow.skill_score or 0.0,
        experience_score=rrow.experience_score or 0.0,
        recommendation=rrow.recommendation,
        matched_skills=rrow.matched_skills or [],
        missing_skills=rrow.missing_skills or [],
        extra_skills=rrow.extra_skills or [],
        shap_values=rrow.shap_values,
        skill_contributions=rrow.skill_contributions,
        experience_contribution=rrow.experience_contribution or 0.0,
        technical_score=rrow.technical_score or 0.0,
        hiring_probability=rrow.hiring_probability or 0.0,
        keyword_density=rrow.keyword_density or 0.0,
        experience_years=rrow.experience_years or 0.0,
        pipeline_stage=rrow.pipeline_stage,
        is_shortlisted=rrow.is_shortlisted,
        recruiter_notes=rrow.recruiter_notes,
        candidate_name=resume.candidate_name if resume else None,
        candidate_email=resume.email if resume else None,
        candidate_skills=resume.skills or [] if resume else [],
        filename=resume.filename if resume else None,
        ranked_at=rrow.ranked_at,
    )


async def _get_job_or_404(job_id: str, db: AsyncSession, user: User) -> JobDescription:
    res = await db.execute(select(JobDescription).where(JobDescription.id == job_id))
    j = res.scalar_one_or_none()
    if not j:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if user.organization_id and j.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    return j


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("/", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: CreateJobRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raw_text = body.description

    # Auto-extract skills if none provided
    req_skills = body.required_skills
    if not req_skills:
        parsed = parser.parse_text(raw_text)
        req_skills = parsed.get("skills", [])

    cleaned = cleaner.clean(raw_text)

    # Embed the job description
    try:
        emb = embedding_service.encode_single(cleaned or raw_text).tolist()
    except Exception:
        emb = None

    job = JobDescription(
        title=body.title,
        description=body.description,
        raw_text=raw_text,
        cleaned_text=cleaned,
        department=body.department,
        location=body.location,
        employment_type=body.employment_type,
        experience_level=body.experience_level,
        salary_min=body.salary_min,
        salary_max=body.salary_max,
        required_skills=req_skills,
        preferred_skills=body.preferred_skills,
        responsibilities=body.responsibilities,
        qualifications=body.qualifications,
        experience_requirement=body.experience_requirement,
        education_requirement=body.education_requirement,
        embedding=emb,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        status="active",
        pipeline_stages=[
            "applied", "screening", "shortlisted",
            "interview", "technical", "hr_round", "offer", "hired", "rejected"
        ],
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return _job_to_out(job)


@router.get("/", response_model=List[JobOut])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    q = select(JobDescription)
    if current_user.organization_id:
        q = q.where(JobDescription.organization_id == current_user.organization_id)
    if status_filter:
        q = q.where(JobDescription.status == status_filter)
    q = q.order_by(JobDescription.created_at.desc())
    res = await db.execute(q)
    jobs = res.scalars().all()

    # Count rankings per job
    result = []
    for j in jobs:
        cnt_res = await db.execute(
            select(func.count()).where(RankingResult.job_id == j.id)
        )
        cnt = cnt_res.scalar_one()
        result.append(_job_to_out(j, candidate_count=cnt))
    return result


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    j = await _get_job_or_404(job_id, db, current_user)
    cnt_res = await db.execute(select(func.count()).where(RankingResult.job_id == j.id))
    return _job_to_out(j, candidate_count=cnt_res.scalar_one())


@router.put("/{job_id}", response_model=JobOut)
async def update_job(
    job_id: str,
    body: UpdateJobRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    j = await _get_job_or_404(job_id, db, current_user)
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(j, field, val)
    j.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(j)
    return _job_to_out(j)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    j = await _get_job_or_404(job_id, db, current_user)
    await db.delete(j)
    await db.commit()


# ── Ranking Pipeline ──────────────────────────────────────────────────────────

@router.post("/{job_id}/rank", response_model=List[RankingOut])
async def run_ranking(
    job_id: str,
    min_score: float = Query(0.0, ge=0, le=100),
    ranking_mode: str = Query("hybrid"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await _get_job_or_404(job_id, db, current_user)

    # Load production ML model artifact (if any)
    from backend.ml.model_registry import get_production_model, load_full_artifact
    ml_artifact = None
    prod_model = await get_production_model(db)
    if prod_model and prod_model.get("model_path"):
        ml_artifact = load_full_artifact(prod_model["model_path"])
        if ml_artifact is None and ranking_mode in ("ml", "hybrid"):
            logger.warning("Production model artifact missing; falling back to traditional")
            ranking_mode = "traditional"
    elif ranking_mode in ("ml", "hybrid"):
        ranking_mode = "traditional"  # no model deployed yet

    # Fetch all resumes for org
    q = select(Resume)
    if current_user.organization_id:
        q = q.where(Resume.organization_id == current_user.organization_id)
    res = await db.execute(q)
    resumes = res.scalars().all()

    if not resumes:
        return []

    import numpy as np

    # Build embeddings
    job_emb = np.array(job.embedding, dtype="float32") if job.embedding else None
    resume_embeddings = [
        (r.id, np.array(r.embedding, dtype="float32") if r.embedding else None)
        for r in resumes
    ]
    resume_data = {
        r.id: {
            "skills": r.skills or [],
            "experience_years": r.experience_years or 0.0,
            "experience_requirement": job.experience_requirement or "",
            "cleaned_text": r.cleaned_text or "",
            "raw_text": r.raw_text or "",
            "completeness_score": r.completeness_score or 0.0,
            # Extended fields for feature engineering
            "projects": r.projects or [],
            "certifications": r.certifications or [],
            "languages": r.languages or [],
            "soft_skills": r.soft_skills or [],
            "portfolio_url": r.portfolio_url,
            "github_url": r.github_url,
            "education": r.education or [],
        }
        for r in resumes
    }

    job_dict = {
        "required_skills": job.required_skills or [],
        "preferred_skills": job.preferred_skills or [],
        "experience_requirement": job.experience_requirement or "",
        "education_requirement": job.education_requirement or "",
        "cleaned_text": job.cleaned_text or "",
        "description": job.description or "",
    }

    raw_results = ranking_engine.rank_candidates(
        job_embedding=job_emb,
        resume_embeddings=resume_embeddings,
        job_skills_required=job.required_skills or [],
        job_skills_preferred=job.preferred_skills or [],
        resume_data=resume_data,
        job_text=job.cleaned_text or job.raw_text or "",
        ranking_mode=ranking_mode,
        ml_artifact=ml_artifact,
        job_dict=job_dict,
    )

    # Filter by min score
    raw_results = [r for r in raw_results if r.similarity_score >= min_score]

    # Delete old rankings for this job
    old = await db.execute(select(RankingResult).where(RankingResult.job_id == job_id))
    for old_r in old.scalars().all():
        await db.delete(old_r)

    # Save new rankings
    resume_map = {r.id: r for r in resumes}
    saved: List[RankingResult] = []
    for rr in raw_results:
        resume = resume_map.get(rr.resume_id)
        rrow = RankingResult(
            job_id=job_id,
            resume_id=rr.resume_id,
            organization_id=current_user.organization_id,
            rank=rr.rank,
            similarity_score=rr.similarity_score,
            semantic_score=rr.semantic_score,
            skill_score=rr.skill_score,
            experience_score=rr.experience_score,
            recommendation=rr.recommendation,
            matched_skills=rr.matched_skills,
            missing_skills=rr.missing_skills,
            extra_skills=rr.extra_skills,
            shap_values=rr.shap_values,
            skill_contributions=rr.skill_contributions,
            experience_contribution=rr.experience_contribution,
            technical_score=rr.technical_score,
            hiring_probability=rr.hiring_probability,
            keyword_density=rr.keyword_density,
            experience_years=rr.experience_years,
            quality_score=rr.quality_score,
            pipeline_stage="applied",
        )
        db.add(rrow)
        saved.append((rrow, resume))

    await db.flush()
    await db.commit()

    out = []
    for rrow, resume in saved:
        await db.refresh(rrow)
        out.append(_ranking_out(rrow, resume))
    return out


@router.get("/{job_id}/rankings", response_model=List[RankingOut])
async def get_rankings(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_job_or_404(job_id, db, current_user)
    res = await db.execute(
        select(RankingResult).where(RankingResult.job_id == job_id).order_by(RankingResult.rank)
    )
    rankings = res.scalars().all()

    out = []
    for rrow in rankings:
        resume_res = await db.execute(select(Resume).where(Resume.id == rrow.resume_id))
        resume = resume_res.scalar_one_or_none()
        out.append(_ranking_out(rrow, resume))
    return out


@router.put("/{job_id}/pipeline/{resume_id}", response_model=RankingOut)
async def move_pipeline(
    job_id: str,
    resume_id: str,
    body: MovePipelineRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(RankingResult).where(
            RankingResult.job_id == job_id,
            RankingResult.resume_id == resume_id,
        )
    )
    rrow = res.scalar_one_or_none()
    if not rrow:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ranking not found")

    rrow.pipeline_stage = body.pipeline_stage
    if body.pipeline_stage == "hired":
        rrow.offer_extended = True
    elif body.pipeline_stage == "rejected":
        rrow.is_rejected = True
    elif body.pipeline_stage in ("shortlisted", "interview"):
        rrow.is_shortlisted = True

    rrow.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rrow)

    resume_res = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = resume_res.scalar_one_or_none()
    return _ranking_out(rrow, resume)


@router.get("/{job_id}/analytics")
async def job_analytics(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_job_or_404(job_id, db, current_user)
    res = await db.execute(
        select(RankingResult).where(RankingResult.job_id == job_id)
    )
    rankings = res.scalars().all()
    if not rankings:
        return {"message": "No rankings yet"}

    scores = [r.similarity_score for r in rankings]
    stages: Dict[str, int] = {}
    for r in rankings:
        stages[r.pipeline_stage] = stages.get(r.pipeline_stage, 0) + 1

    all_missing: Dict[str, int] = {}
    all_matched: Dict[str, int] = {}
    for r in rankings:
        for s in (r.missing_skills or []):
            all_missing[s] = all_missing.get(s, 0) + 1
        for s in (r.matched_skills or []):
            all_matched[s] = all_matched.get(s, 0) + 1

    return {
        "total_candidates": len(rankings),
        "avg_score": round(sum(scores) / len(scores), 2),
        "top_score": round(max(scores), 2),
        "score_distribution": {
            "excellent": sum(1 for s in scores if s >= 90),
            "strong": sum(1 for s in scores if 75 <= s < 90),
            "suitable": sum(1 for s in scores if 55 <= s < 75),
            "average": sum(1 for s in scores if 35 <= s < 55),
            "not_recommended": sum(1 for s in scores if s < 35),
        },
        "pipeline_stages": stages,
        "top_missing_skills": sorted(all_missing.items(), key=lambda x: x[1], reverse=True)[:10],
        "top_matched_skills": sorted(all_matched.items(), key=lambda x: x[1], reverse=True)[:10],
    }

"""
Analytics endpoints — dashboard stats, hiring funnel, skill demand, trends.
"""
import logging
from typing import Annotated, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.core.database import get_db
from backend.models.job import JobDescription
from backend.models.ranking import RankingResult
from backend.models.resume import Resume
from backend.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/dashboard")
async def dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    org_id = current_user.organization_id

    # Counts
    resume_q = select(func.count(Resume.id))
    job_q = select(func.count(JobDescription.id))
    ranking_q = select(func.count(RankingResult.id))

    if org_id:
        resume_q = resume_q.where(Resume.organization_id == org_id)
        job_q = job_q.where(JobDescription.organization_id == org_id)
        ranking_q = ranking_q.where(RankingResult.organization_id == org_id)

    total_resumes = (await db.execute(resume_q)).scalar_one()
    total_jobs = (await db.execute(job_q)).scalar_one()
    total_rankings = (await db.execute(ranking_q)).scalar_one()

    # Avg score
    score_q = select(func.avg(RankingResult.similarity_score))
    if org_id:
        score_q = score_q.where(RankingResult.organization_id == org_id)
    avg_score = (await db.execute(score_q)).scalar_one() or 0.0

    # Pipeline stages
    pipeline_q = select(RankingResult.pipeline_stage, func.count(RankingResult.id))
    if org_id:
        pipeline_q = pipeline_q.where(RankingResult.organization_id == org_id)
    pipeline_q = pipeline_q.group_by(RankingResult.pipeline_stage)
    pipeline_res = await db.execute(pipeline_q)
    pipeline_stages = {row[0]: row[1] for row in pipeline_res.all()}

    # Top skills demand
    q = select(Resume)
    if org_id:
        q = q.where(Resume.organization_id == org_id)
    resumes_res = await db.execute(q)
    resumes = resumes_res.scalars().all()

    skill_freq: Dict[str, int] = {}
    for r in resumes:
        for s in (r.skills or []):
            s_clean = s.lower().strip()
            skill_freq[s_clean] = skill_freq.get(s_clean, 0) + 1

    top_skills = sorted(skill_freq.items(), key=lambda x: x[1], reverse=True)[:15]

    # Score distribution
    rankings_q = select(RankingResult.similarity_score)
    if org_id:
        rankings_q = rankings_q.where(RankingResult.organization_id == org_id)
    all_scores_res = await db.execute(rankings_q)
    all_scores = [row[0] for row in all_scores_res.all() if row[0] is not None]

    return {
        "total_resumes": total_resumes,
        "total_jobs": total_jobs,
        "total_rankings": total_rankings,
        "avg_match_score": round(float(avg_score), 2),
        "pipeline_stages": pipeline_stages,
        "top_skills": [{"skill": s, "count": c} for s, c in top_skills],
        "score_distribution": {
            "excellent": sum(1 for s in all_scores if s >= 90),
            "strong": sum(1 for s in all_scores if 75 <= s < 90),
            "suitable": sum(1 for s in all_scores if 55 <= s < 75),
            "average": sum(1 for s in all_scores if 35 <= s < 55),
            "not_recommended": sum(1 for s in all_scores if s < 35),
        },
        "shortlisted_count": pipeline_stages.get("shortlisted", 0) + pipeline_stages.get("interview", 0),
        "hired_count": pipeline_stages.get("hired", 0),
        "offer_extended": pipeline_stages.get("offer", 0),
    }


@router.get("/hiring-funnel")
async def hiring_funnel(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    org_id = current_user.organization_id
    stages = [
        "applied", "screening", "shortlisted",
        "interview", "technical", "hr_round", "offer", "hired"
    ]
    funnel = {}
    for stage in stages:
        q = select(func.count(RankingResult.id)).where(RankingResult.pipeline_stage == stage)
        if org_id:
            q = q.where(RankingResult.organization_id == org_id)
        count = (await db.execute(q)).scalar_one()
        funnel[stage] = count

    return {"funnel": [{"stage": k, "count": v} for k, v in funnel.items()]}


@router.get("/skill-demand")
async def skill_demand(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    org_id = current_user.organization_id
    q = select(JobDescription)
    if org_id:
        q = q.where(JobDescription.organization_id == org_id)
    jobs_res = await db.execute(q)
    jobs = jobs_res.scalars().all()

    skill_freq: Dict[str, int] = {}
    for j in jobs:
        for s in (j.required_skills or []):
            s_clean = s.lower().strip()
            skill_freq[s_clean] = skill_freq.get(s_clean, 0) + 1

    top = sorted(skill_freq.items(), key=lambda x: x[1], reverse=True)[:20]
    return {"skills": [{"skill": s, "demand": c} for s, c in top]}


@router.get("/candidate-distribution")
async def candidate_distribution(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    org_id = current_user.organization_id
    q = select(RankingResult.similarity_score)
    if org_id:
        q = q.where(RankingResult.organization_id == org_id)
    res = await db.execute(q)
    scores = [row[0] for row in res.all() if row[0] is not None]

    buckets = list(range(0, 110, 10))
    histogram = [0] * (len(buckets) - 1)
    for s in scores:
        for i in range(len(buckets) - 1):
            if buckets[i] <= s < buckets[i + 1]:
                histogram[i] += 1
                break

    return {
        "distribution": [
            {"range": f"{buckets[i]}-{buckets[i+1]}", "count": histogram[i]}
            for i in range(len(histogram))
        ],
        "total": len(scores),
        "mean": round(sum(scores) / len(scores), 2) if scores else 0,
    }


@router.get("/model-performance")
async def model_performance():
    """Return ML model metrics from last training run."""
    from pathlib import Path
    import json
    meta_path = Path("trained/model_meta.json")
    if not meta_path.exists():
        return {"message": "No model trained yet", "metrics": {}}
    data = json.loads(meta_path.read_text())
    return {"model": data.get("model_name"), "metrics": data.get("metrics", {})}

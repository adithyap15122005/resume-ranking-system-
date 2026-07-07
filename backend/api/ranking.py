"""
Ranking endpoints.

GET  /rank           — run ranking for a job against all stored resumes
GET  /results        — retrieve stored ranking results for a job
GET  /history        — summary of all ranking sessions
GET  /evaluate       — classification metrics (requires Kaggle dataset labels)
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.job import JobDescription
from backend.models.ranking import RankingResult
from backend.models.resume import Resume
from backend.schemas.ranking import RankingEntryResponse, RankingHistoryItem, RankingResponse
from backend.utils.ranking_engine import RankingEngine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Ranking"])

_engine = RankingEngine()


# ── Rank endpoint ─────────────────────────────────────────────────────────────

@router.get("/rank", response_model=RankingResponse)
def rank_resumes(
    job_id: int = Query(..., description="ID of the job description to rank against"),
    engine: str = Query("tfidf", description="Similarity engine: 'tfidf' | 'sbert'"),
    save_results: bool = Query(True, description="Persist ranking results to DB"),
    db: Session = Depends(get_db),
):
    """
    Run the ranking pipeline.
    Fetches the job description and all resumes from DB, computes scores,
    optionally persists results, and returns the ranked list.
    """
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    resumes = db.query(Resume).all()
    if not resumes:
        raise HTTPException(status_code=404, detail="No resumes found. Upload resumes first.")

    # Build engine (allow dynamic engine selection per request)
    from backend.utils.similarity import get_similarity_engine
    ranking_engine = RankingEngine(similarity_engine=get_similarity_engine(engine))

    resume_dicts = [r.to_dict() for r in resumes]
    job_dict = job.to_dict()

    ranked = ranking_engine.rank(job_dict, resume_dicts)

    if save_results:
        # Delete old results for this job before saving new ones
        db.query(RankingResult).filter(RankingResult.job_id == job_id).delete()
        for entry in ranked:
            result = RankingResult(
                job_id=job_id,
                resume_id=entry.resume_id,
                rank=entry.rank,
                similarity_score=entry.similarity_score,
                matched_skills=entry.matched_skills,
                missing_skills=entry.missing_skills,
                extra_skills=entry.extra_skills,
                recommendation=entry.recommendation,
                quality_score=entry.quality_score,
                keyword_density=entry.keyword_density,
                experience_years=entry.experience_years,
            )
            db.add(result)
        db.commit()
        logger.info("Saved %d ranking results for job_id=%d.", len(ranked), job_id)

    return RankingResponse(
        job_id=job_id,
        job_title=job.title,
        total_resumes=len(ranked),
        results=[
            RankingEntryResponse(
                rank=e.rank,
                resume_id=e.resume_id,
                candidate_name=e.candidate_name,
                filename=e.filename,
                similarity_score=e.similarity_score,
                matched_skills=e.matched_skills,
                missing_skills=e.missing_skills,
                extra_skills=e.extra_skills,
                recommendation=e.recommendation,
                quality_score=e.quality_score,
                keyword_density=e.keyword_density,
                experience_years=e.experience_years,
            )
            for e in ranked
        ],
    )


# ── Results endpoint ──────────────────────────────────────────────────────────

@router.get("/results", response_model=RankingResponse)
def get_results(
    job_id: int = Query(..., description="Job ID to retrieve stored results for"),
    db: Session = Depends(get_db),
):
    """Return previously stored ranking results for a job."""
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    results = (
        db.query(RankingResult)
        .filter(RankingResult.job_id == job_id)
        .order_by(RankingResult.rank)
        .all()
    )
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"No ranking results for job {job_id}. Run /rank first.",
        )

    return RankingResponse(
        job_id=job_id,
        job_title=job.title,
        total_resumes=len(results),
        results=[
            RankingEntryResponse(
                rank=r.rank,
                resume_id=r.resume_id,
                candidate_name=r.resume.candidate_name if r.resume else None,
                filename=r.resume.filename if r.resume else "",
                similarity_score=r.similarity_score,
                matched_skills=r.matched_skills or [],
                missing_skills=r.missing_skills or [],
                extra_skills=r.extra_skills or [],
                recommendation=r.recommendation or "",
                quality_score=r.quality_score or 0.0,
                keyword_density=r.keyword_density or 0.0,
                experience_years=r.experience_years or 0.0,
            )
            for r in results
        ],
        ranked_at=results[0].ranked_at if results else None,
    )


# ── History endpoint ──────────────────────────────────────────────────────────

@router.get("/history", response_model=List[RankingHistoryItem])
def ranking_history(db: Session = Depends(get_db)):
    """Return a summary of all jobs that have been ranked."""
    jobs = db.query(JobDescription).all()
    history: List[RankingHistoryItem] = []

    for job in jobs:
        results = (
            db.query(RankingResult)
            .filter(RankingResult.job_id == job.id)
            .order_by(RankingResult.rank)
            .all()
        )
        top = results[0] if results else None
        history.append(
            RankingHistoryItem(
                job_id=job.id,
                job_title=job.title,
                total_resumes=len(results),
                top_candidate=top.resume.candidate_name if top and top.resume else None,
                top_score=top.similarity_score if top else None,
                ranked_at=top.ranked_at if top else job.uploaded_at,
            )
        )

    return history


# ── Evaluate endpoint ─────────────────────────────────────────────────────────

@router.get("/evaluate")
def evaluate(
    job_id: int = Query(...),
    category: Optional[str] = Query(
        None,
        description="Expected category label (from Kaggle dataset). "
        "Resumes whose filename contains this string are treated as relevant.",
    ),
    db: Session = Depends(get_db),
):
    """
    Compute classification metrics for a ranking run.

    Since we use the Kaggle dataset (Category column), this endpoint
    treats resumes matching the supplied category as relevant (label=1)
    and all others as irrelevant (label=0).

    This converts unsupervised ranking into a supervised evaluation.
    """
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")

    results = (
        db.query(RankingResult)
        .filter(RankingResult.job_id == job_id)
        .order_by(RankingResult.rank)
        .all()
    )
    if not results:
        raise HTTPException(status_code=404, detail="Run /rank first.")

    ranking_engine = RankingEngine()
    entries = []
    labels = []

    from backend.utils.ranking_engine import RankingEntry

    for r in results:
        entry = RankingEntry(
            rank=r.rank,
            resume_id=r.resume_id,
            candidate_name=r.resume.candidate_name if r.resume else "Unknown",
            filename=r.resume.filename if r.resume else "",
            similarity_score=r.similarity_score,
            matched_skills=r.matched_skills or [],
            missing_skills=r.missing_skills or [],
            extra_skills=r.extra_skills or [],
            recommendation=r.recommendation or "",
            quality_score=r.quality_score or 0.0,
            keyword_density=r.keyword_density or 0.0,
            experience_years=r.experience_years or 0.0,
        )
        entries.append(entry)

        if category:
            filename_lower = (r.resume.filename if r.resume else "").lower()
            label = 1 if category.lower().replace(" ", "_") in filename_lower else 0
        else:
            label = 1 if r.rank <= max(1, len(results) // 4) else 0

        labels.append(label)

    metrics = ranking_engine.compute_metrics(entries, labels)
    return {"job_id": job_id, "job_title": job.title, "metrics": metrics}

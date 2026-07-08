"""
Resume management endpoints — upload, list, search, intelligence, pipeline.
"""
import hashlib
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.core.config import settings
from backend.core.database import get_db
from backend.ml.ai_intelligence import intelligence_engine
from backend.ml.embeddings import embedding_service
from backend.models.resume import Resume
from backend.models.user import User
from backend.utils.resume_parser import ResumeParser
from backend.utils.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/resumes", tags=["Resumes"])

parser = ResumeParser()
cleaner = TextCleaner()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ResumeOut(BaseModel):
    id: str
    filename: str
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: List[str] = []
    education: List[Any] = []
    experience: Optional[str] = None
    projects: List[Any] = []
    certifications: List[Any] = []
    languages: List[Any] = []
    tools: List[Any] = []
    experience_years: float = 0.0
    completeness_score: float = 0.0
    technical_score: float = 0.0
    leadership_score: float = 0.0
    communication_score: float = 0.0
    job_readiness: float = 0.0
    culture_fit: float = 0.0
    ai_summary: Optional[str] = None
    strengths: List[str] = []
    weaknesses: List[str] = []
    career_path: Optional[str] = None
    is_pinned: bool = False
    notes: Optional[str] = None
    tags: List[str] = []
    status: str = "parsed"
    uploaded_at: datetime
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None

    model_config = {"from_attributes": True}


class UpdateNotesRequest(BaseModel):
    notes: str


class PaginatedResumes(BaseModel):
    items: List[ResumeOut]
    total: int
    page: int
    page_size: int
    pages: int


def _coerce(val, default):
    return val if val is not None else default


def _resume_to_out(r: Resume) -> ResumeOut:
    return ResumeOut(
        id=r.id,
        filename=r.filename,
        candidate_name=r.candidate_name,
        email=r.email,
        phone=r.phone,
        skills=_coerce(r.skills, []),
        education=_coerce(r.education, []),
        experience=r.experience,
        projects=_coerce(r.projects, []),
        certifications=_coerce(r.certifications, []),
        languages=_coerce(r.languages, []),
        tools=_coerce(r.tools, []),
        experience_years=r.experience_years or 0.0,
        completeness_score=r.completeness_score or 0.0,
        technical_score=r.technical_score or 0.0,
        leadership_score=r.leadership_score or 0.0,
        communication_score=r.communication_score or 0.0,
        job_readiness=r.job_readiness or 0.0,
        culture_fit=r.culture_fit or 0.0,
        ai_summary=r.ai_summary,
        strengths=_coerce(r.strengths, []),
        weaknesses=_coerce(r.weaknesses, []),
        career_path=r.career_path,
        is_pinned=r.is_pinned or False,
        notes=r.notes,
        tags=_coerce(r.tags, []),
        status=r.status or "parsed",
        uploaded_at=r.uploaded_at,
        linkedin_url=r.linkedin_url,
        github_url=r.github_url,
    )


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=List[ResumeOut], status_code=status.HTTP_201_CREATED)
async def upload_resumes(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = []
    settings.RESUME_DIR.mkdir(parents=True, exist_ok=True)

    for file in files:
        suffix = Path(file.filename).suffix.lower()
        if suffix not in settings.ALLOWED_RESUME_EXTENSIONS:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Unsupported file type: {suffix}. Allowed: {settings.ALLOWED_RESUME_EXTENSIONS}",
            )

        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()

        # Duplicate check
        existing = await db.execute(select(Resume).where(Resume.file_hash == file_hash))
        if existing.scalar_one_or_none():
            logger.info("Duplicate resume skipped: %s", file.filename)
            continue

        # Save file
        save_path = settings.RESUME_DIR / f"{file_hash}{suffix}"
        save_path.write_bytes(content)

        # Parse
        try:
            parsed = parser.parse(str(save_path))
        except Exception as exc:
            logger.error("Parse error for %s: %s", file.filename, exc)
            parsed = {}

        cleaned = cleaner.clean(parsed.get("raw_text", ""))

        # AI intelligence
        intel = intelligence_engine.generate_full_intelligence(
            {**parsed, "completeness_score": parsed.get("completeness_score", 0)}
        )

        # SBERT embedding
        emb_text = cleaned or parsed.get("raw_text", "")
        try:
            emb = embedding_service.encode_single(emb_text).tolist() if emb_text else None
        except Exception:
            emb = None

        resume = Resume(
            filename=file.filename,
            filepath=str(save_path),
            file_hash=file_hash,
            file_size_kb=round(len(content) / 1024, 2),
            organization_id=current_user.organization_id,
            uploaded_by=current_user.id,
            status="parsed",
            candidate_name=parsed.get("candidate_name"),
            email=parsed.get("email"),
            phone=parsed.get("phone"),
            skills=parsed.get("skills", []),
            education=parsed.get("education", []),
            experience=parsed.get("experience"),
            projects=parsed.get("projects", []),
            certifications=parsed.get("certifications", []),
            languages=parsed.get("languages", []),
            tools=parsed.get("tools", []),
            raw_text=parsed.get("raw_text"),
            cleaned_text=cleaned,
            experience_years=parsed.get("experience_years", 0.0),
            completeness_score=parsed.get("completeness_score", 0.0),
            embedding=emb,
            parsed_at=datetime.now(timezone.utc),
            # AI intelligence
            ai_summary=intel.get("ai_summary"),
            strengths=intel.get("strengths", []),
            weaknesses=intel.get("weaknesses", []),
            career_path=intel.get("career_path"),
            technical_score=intel.get("technical_score", 0.0),
            leadership_score=intel.get("leadership_score", 0.0),
            communication_score=intel.get("communication_score", 0.0),
            job_readiness=intel.get("job_readiness", 0.0),
            culture_fit=intel.get("culture_fit", 0.0),
            confidence_score=intel.get("confidence_score", 0.0),
            predicted_salary_min=intel.get("predicted_salary_min"),
            predicted_salary_max=intel.get("predicted_salary_max"),
        )
        db.add(resume)

        # Add to FAISS
        if emb:
            import numpy as np
            embedding_service.add_to_index(np.array(emb, dtype="float32"), resume.id)

        await db.flush()
        results.append(_resume_to_out(resume))

    await db.commit()
    return results


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=PaginatedResumes)
async def list_resumes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    pinned_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Resume)
    if current_user.organization_id:
        q = q.where(Resume.organization_id == current_user.organization_id)
    if pinned_only:
        q = q.where(Resume.is_pinned == True)  # noqa: E712

    # Count
    count_q = select(func.count()).select_from(q.subquery())
    total_res = await db.execute(count_q)
    total = total_res.scalar_one()

    q = q.order_by(Resume.uploaded_at.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    res = await db.execute(q)
    items = res.scalars().all()

    # Client-side search filter (simple, no FTS)
    if search:
        search_lower = search.lower()
        items = [
            r for r in items
            if search_lower in (r.candidate_name or "").lower()
            or search_lower in (r.email or "").lower()
            or any(search_lower in s.lower() for s in (r.skills or []))
        ]

    return PaginatedResumes(
        items=[_resume_to_out(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),
    )


# ── Single ────────────────────────────────────────────────────────────────────

@router.get("/{resume_id}", response_model=ResumeOut)
async def get_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = await _get_or_404(resume_id, db, current_user)
    return _resume_to_out(r)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = await _get_or_404(resume_id, db, current_user)
    try:
        Path(r.filepath).unlink(missing_ok=True)
    except Exception:
        pass
    await db.delete(r)
    await db.commit()


@router.put("/{resume_id}/pin", response_model=ResumeOut)
async def toggle_pin(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = await _get_or_404(resume_id, db, current_user)
    r.is_pinned = not r.is_pinned
    await db.commit()
    await db.refresh(r)
    return _resume_to_out(r)


@router.put("/{resume_id}/notes", response_model=ResumeOut)
async def update_notes(
    resume_id: str,
    body: UpdateNotesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = await _get_or_404(resume_id, db, current_user)
    r.notes = body.notes
    await db.commit()
    await db.refresh(r)
    return _resume_to_out(r)


@router.get("/{resume_id}/intelligence")
async def get_intelligence(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    r = await _get_or_404(resume_id, db, current_user)
    return {
        "technical_score": r.technical_score,
        "leadership_score": r.leadership_score,
        "communication_score": r.communication_score,
        "job_readiness": r.job_readiness,
        "culture_fit": r.culture_fit,
        "confidence_score": r.confidence_score,
        "strengths": r.strengths or [],
        "weaknesses": r.weaknesses or [],
        "career_path": r.career_path,
        "ai_summary": r.ai_summary,
        "predicted_salary_min": r.predicted_salary_min,
        "predicted_salary_max": r.predicted_salary_max,
        "interview_questions": intelligence_engine.generate_interview_questions(
            r.skills or [], r.experience_years or 0
        ),
    }


# ── Semantic Search ───────────────────────────────────────────────────────────

@router.get("/search/semantic")
async def semantic_search(
    q: str = Query(..., min_length=3),
    top_k: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query_emb = embedding_service.encode_single(q)
    hits = embedding_service.search(query_emb, top_k=top_k)

    if not hits:
        return {"results": [], "query": q}

    ids = [h[0] for h in hits]
    scores = {h[0]: h[1] for h in hits}

    res = await db.execute(select(Resume).where(Resume.id.in_(ids)))
    resumes = res.scalars().all()

    results = []
    for r in resumes:
        out = _resume_to_out(r)
        results.append({
            "resume": out.model_dump(),
            "score": round(float(scores.get(r.id, 0)) * 100, 2),
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return {"results": results, "query": q}


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_or_404(resume_id: str, db: AsyncSession, user: User) -> Resume:
    res = await db.execute(select(Resume).where(Resume.id == resume_id))
    r = res.scalar_one_or_none()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    if user.organization_id and r.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    return r

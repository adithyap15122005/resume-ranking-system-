"""
Upload endpoints.

POST /upload-resume   — accept one or many resume files
POST /upload-job      — accept job description file or plain text body
DELETE /delete/{id}   — remove a resume record and file
GET  /resumes         — list all stored resumes
GET  /jobs            — list all stored job descriptions
"""
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.job import JobDescription
from backend.models.resume import Resume
from backend.schemas.job import JobCreate, JobResponse
from backend.schemas.resume import ResumeResponse
from backend.utils.resume_parser import ResumeParser
from backend.utils.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Upload"])

_parser = ResumeParser()
_cleaner = TextCleaner()

ALLOWED = {".pdf", ".docx", ".txt"}
MAX_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_file(upload: UploadFile, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (upload.filename or "upload.bin")
    # Avoid overwriting — append a counter
    counter = 1
    stem, suffix = dest.stem, dest.suffix
    while dest.exists():
        dest = dest_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    with dest.open("wb") as fh:
        shutil.copyfileobj(upload.file, fh)
    return dest


def _validate_file(upload: UploadFile) -> None:
    ext = Path(upload.filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED)}",
        )


# ── Resume endpoints ──────────────────────────────────────────────────────────

@router.post("/upload-resume", response_model=List[ResumeResponse], status_code=status.HTTP_201_CREATED)
async def upload_resumes(
    files: List[UploadFile] = File(..., description="One or more resume files (PDF/DOCX/TXT)"),
    db: Session = Depends(get_db),
):
    """
    Upload one or more resume files.
    Parses each file, cleans text, and stores results in the database.
    Duplicate detection is based on file hash — re-uploading the same file returns the existing record.
    """
    responses: List[ResumeResponse] = []

    for upload in files:
        _validate_file(upload)
        saved_path = _save_file(upload, settings.RESUME_DIR)

        try:
            parsed = _parser.parse(str(saved_path))
        except Exception as exc:
            saved_path.unlink(missing_ok=True)
            logger.error("Failed to parse '%s': %s", upload.filename, exc)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not parse '{upload.filename}': {exc}",
            )

        # Duplicate check
        existing = db.query(Resume).filter(Resume.file_hash == parsed["file_hash"]).first()
        if existing:
            logger.info("Duplicate resume detected: '%s' matches id=%d", upload.filename, existing.id)
            saved_path.unlink(missing_ok=True)  # remove redundant file
            responses.append(ResumeResponse.model_validate(existing))
            continue

        cleaned = _cleaner.clean(parsed["raw_text"])

        resume = Resume(
            filename=parsed["filename"],
            filepath=str(saved_path),
            file_hash=parsed["file_hash"],
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
            raw_text=parsed.get("raw_text", ""),
            cleaned_text=cleaned,
            experience_years=parsed.get("experience_years", 0.0),
            completeness_score=parsed.get("completeness_score", 0.0),
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        responses.append(ResumeResponse.model_validate(resume))
        logger.info("Resume stored: id=%d name='%s'", resume.id, resume.candidate_name)

    return responses


@router.get("/resumes", response_model=List[ResumeResponse])
def list_resumes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Return all stored resumes with pagination."""
    resumes = db.query(Resume).offset(skip).limit(limit).all()
    return [ResumeResponse.model_validate(r) for r in resumes]


@router.get("/resumes/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: int, db: Session = Depends(get_db)):
    """Return a single resume by ID."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail=f"Resume {resume_id} not found.")
    return ResumeResponse.model_validate(resume)


@router.delete("/delete/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    """Delete a resume record and its file."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail=f"Resume {resume_id} not found.")

    path = Path(resume.filepath)
    if path.exists():
        path.unlink()

    db.delete(resume)
    db.commit()
    logger.info("Resume id=%d deleted.", resume_id)


# ── Job description endpoints ─────────────────────────────────────────────────

@router.post("/upload-job", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def upload_job(
    title: str = Form(..., description="Job title (e.g. 'Senior Data Scientist')"),
    text: Optional[str] = Form(None, description="Paste job description text directly"),
    file: Optional[UploadFile] = File(None, description="Job description file (PDF/DOCX/TXT)"),
    db: Session = Depends(get_db),
):
    """
    Upload a job description.
    Accepts either a file upload OR pasted text (text takes precedence if both provided).
    """
    raw_text = ""
    filename = None
    filepath = None

    if text and text.strip():
        raw_text = text.strip()
    elif file:
        _validate_file(file)
        saved_path = _save_file(file, settings.JOB_DIR)
        filename = file.filename
        filepath = str(saved_path)
        try:
            parsed = _parser.parse(str(saved_path))
            raw_text = parsed.get("raw_text", "")
        except Exception as exc:
            saved_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not read job file: {exc}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'text' or a 'file'.",
        )

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job description text is empty after parsing.",
        )

    # Extract skills from JD using parser
    jd_parsed = _parser.parse_text(raw_text, filename or "job_description.txt")
    cleaned = _cleaner.clean(raw_text)

    job = JobDescription(
        title=title,
        filename=filename,
        filepath=filepath,
        raw_text=raw_text,
        cleaned_text=cleaned,
        required_skills=jd_parsed.get("skills", []),
        preferred_skills=[],
        education_requirement=None,
        experience_requirement=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("Job description stored: id=%d title='%s'", job.id, job.title)
    return JobResponse.model_validate(job)


@router.get("/jobs", response_model=List[JobResponse])
def list_jobs(db: Session = Depends(get_db)):
    """Return all stored job descriptions."""
    jobs = db.query(JobDescription).all()
    return [JobResponse.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Return a single job description."""
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    return JobResponse.model_validate(job)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """Delete a job description and all its ranking results."""
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    if job.filepath:
        path = Path(job.filepath)
        if path.exists():
            path.unlink()
    db.delete(job)
    db.commit()


# ── Sample data endpoint ──────────────────────────────────────────────────────

@router.post("/generate-sample", tags=["Upload"])
def generate_sample_data(db: Session = Depends(get_db)):
    """Generate 20 synthetic resumes and 5 job descriptions for demo purposes."""
    try:
        from data.sample_generator import generate_all
        result = generate_all(db, force=False)
        return {"resumes": result.get("resumes", 0), "jobs": result.get("jobs", 0)}
    except Exception as exc:
        logger.error("Sample generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

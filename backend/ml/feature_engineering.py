"""
Feature Engineering — canonical 16-feature vector for resume-vs-job scoring.

Used identically at training time (to build X from a hiring dataset) and
at inference time (to score live resumes against a job description).
Never fit any stateful transformer here — this module is pure extraction.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ── Canonical feature contract ────────────────────────────────────────────────

FEATURE_NAMES: List[str] = [
    "tfidf_similarity",           # TF-IDF cosine sim between resume & job text (0-1)
    "sbert_similarity",           # SBERT embedding cosine sim (0-1)
    "skill_match_required",       # required skills covered by resume (0-1)
    "skill_match_preferred",      # preferred skills covered by resume (0-1)
    "experience_match",           # years-of-experience match score (0-1)
    "education_score",            # education level match (0-1)
    "ats_score",                  # resume completeness / 100 (0-1)
    "projects_count_norm",        # min(projects, 10) / 10 (0-1)
    "certifications_count_norm",  # min(certs, 5) / 5 (0-1)
    "languages_count_norm",       # min(languages, 5) / 5 (0-1)
    "soft_skills_count_norm",     # min(soft_skills, 10) / 10 (0-1)
    "has_portfolio",              # 1 if portfolio_url present else 0
    "has_github",                 # 1 if github_url present else 0
    "years_experience_norm",      # min(years, 15) / 15 (0-1)
    "skills_count_norm",          # min(total skills, 30) / 30 (0-1)
    "keyword_density",            # job-keyword coverage in resume text (0-1)
]

VERSION = "1.0"

# Education levels (highest-first so substring matching hits the right tier)
_EDUCATION_LEVELS: List[Tuple[str, float]] = [
    ("phd", 1.0), ("doctorate", 1.0),
    ("master", 0.8), ("mba", 0.8), ("msc", 0.8), ("m.s", 0.8),
    ("bachelor", 0.6), ("b.s", 0.6), ("b.e", 0.6), ("btech", 0.6),
    ("associate", 0.4), ("diploma", 0.3),
    ("high school", 0.2), ("secondary", 0.2),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_val(v: Any, default: float = 0.0) -> float:
    """Coerce any value to a finite float in [0, 1]."""
    try:
        f = float(v) if v is not None else default
        if f != f or f == float("inf") or f == float("-inf"):
            return default
        return max(0.0, min(1.0, f))
    except (TypeError, ValueError):
        return default


def _parse_required_years(requirement_text: str) -> float:
    """Extract minimum years from text like '3-5 years' or '5+ years'."""
    if not requirement_text:
        return 0.0
    text = requirement_text.lower()
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*year", text)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+)\+?\s*year", text)
    if m:
        return float(m.group(1))
    return 0.0


def _education_score(resume_education: List[Any], job_requirement: str) -> float:
    """
    Returns 0.5 if no requirement stated (neutral), otherwise matches the
    highest education level found in the resume against the job requirement.
    """
    if not job_requirement:
        return 0.5  # no requirement = neutral, don't penalise

    req_lower = job_requirement.lower()
    required_level = 0.0
    for keyword, level in _EDUCATION_LEVELS:
        if keyword in req_lower:
            required_level = level
            break

    if required_level == 0.0:
        return 0.5  # couldn't parse requirement

    # Find the highest education level in the resume
    resume_text = " ".join(str(e) for e in (resume_education or [])).lower()
    candidate_level = 0.0
    for keyword, level in _EDUCATION_LEVELS:
        if keyword in resume_text:
            candidate_level = max(candidate_level, level)

    if candidate_level == 0.0:
        return 0.2  # no education info found

    if candidate_level >= required_level:
        return 1.0
    # Partial credit for close match
    return max(0.0, 1.0 - (required_level - candidate_level))


# ── Main extractor ────────────────────────────────────────────────────────────

class ResumeFeatureExtractor:
    """
    Stateless extractor that computes the canonical FEATURE_NAMES vector from
    a resume dict + job dict pair plus optional pre-computed embeddings.

    dict schemas mirror the fields available on the Resume and JobDescription
    SQLAlchemy models (see backend/models/resume.py and backend/models/job.py).
    """

    FEATURE_NAMES = FEATURE_NAMES
    VERSION = VERSION

    # ── Single extraction ─────────────────────────────────────────────────────

    def extract_single(
        self,
        resume_dict: Dict[str, Any],
        job_dict: Dict[str, Any],
        resume_emb: Optional[np.ndarray] = None,
        job_emb: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Returns a 1-D float32 array of shape (16,) with values in [0, 1].
        All missing/invalid inputs default to 0.0 (0.5 for education).
        """
        resume_text = str(resume_dict.get("cleaned_text") or resume_dict.get("raw_text") or "")
        job_text = str(job_dict.get("cleaned_text") or job_dict.get("description") or "")

        tfidf_sim = self._tfidf_sim(job_text, resume_text)
        sbert_sim = self._sbert_sim(resume_emb, job_emb, fallback=tfidf_sim)

        required_skills = [s.lower().strip() for s in (job_dict.get("required_skills") or []) if s]
        preferred_skills = [s.lower().strip() for s in (job_dict.get("preferred_skills") or []) if s]
        candidate_skills = {s.lower().strip() for s in (resume_dict.get("skills") or []) if s}

        req_set = set(required_skills)
        pref_set = set(preferred_skills)
        skill_match_req = (
            len(candidate_skills & req_set) / len(req_set) if req_set else 1.0
        )
        skill_match_pref = (
            len(candidate_skills & pref_set) / len(pref_set) if pref_set else 0.0
        )

        exp_years = float(resume_dict.get("experience_years") or 0.0)
        exp_req = str(job_dict.get("experience_requirement") or "")
        experience_match = self._experience_match(exp_years, exp_req)

        edu_score = _education_score(
            resume_dict.get("education") or [],
            job_dict.get("education_requirement") or "",
        )

        ats = _safe_val(resume_dict.get("completeness_score", 0.0)) / 1.0  # already 0-100; normalize
        if ats > 1.0:
            ats = ats / 100.0

        projects = resume_dict.get("projects") or []
        certs = resume_dict.get("certifications") or []
        langs = resume_dict.get("languages") or []
        soft = resume_dict.get("soft_skills") or []

        has_portfolio = 1.0 if resume_dict.get("portfolio_url") else 0.0
        has_github = 1.0 if resume_dict.get("github_url") else 0.0

        kd = self._keyword_density(resume_text, job_text)

        features = np.array([
            _safe_val(tfidf_sim),
            _safe_val(sbert_sim),
            _safe_val(skill_match_req),
            _safe_val(skill_match_pref),
            _safe_val(experience_match),
            _safe_val(edu_score),
            _safe_val(ats),
            _safe_val(min(len(projects), 10) / 10.0),
            _safe_val(min(len(certs), 5) / 5.0),
            _safe_val(min(len(langs), 5) / 5.0),
            _safe_val(min(len(soft), 10) / 10.0),
            _safe_val(has_portfolio),
            _safe_val(has_github),
            _safe_val(min(exp_years, 15.0) / 15.0),
            _safe_val(min(len(resume_dict.get("skills") or []), 30) / 30.0),
            _safe_val(kd),
        ], dtype=np.float32)

        return features

    # ── Batch extraction ──────────────────────────────────────────────────────

    def extract_batch(
        self,
        resumes: List[Dict[str, Any]],
        job: Dict[str, Any],
        resume_embs: Optional[List[Optional[np.ndarray]]] = None,
        job_emb: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Returns a 2-D float32 array of shape (N, 16).
        resume_embs must match len(resumes) if provided.
        """
        if resume_embs is None:
            resume_embs = [None] * len(resumes)

        rows = [
            self.extract_single(r, job, emb, job_emb)
            for r, emb in zip(resumes, resume_embs)
        ]
        return np.vstack(rows).astype(np.float32) if rows else np.empty((0, 16), dtype=np.float32)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _tfidf_sim(self, job_text: str, resume_text: str) -> float:
        if not job_text or not resume_text:
            return 0.0
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            vec = TfidfVectorizer(max_features=8000, ngram_range=(1, 2), sublinear_tf=True)
            tfidf = vec.fit_transform([job_text, resume_text])
            sim = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
            return max(0.0, min(1.0, sim))
        except Exception:
            return 0.0

    def _sbert_sim(
        self,
        resume_emb: Optional[np.ndarray],
        job_emb: Optional[np.ndarray],
        fallback: float = 0.0,
    ) -> float:
        if resume_emb is None or job_emb is None:
            return fallback
        try:
            sim = float(np.dot(
                job_emb.astype(np.float64),
                resume_emb.astype(np.float64),
            ))
            return max(0.0, min(1.0, sim))
        except Exception:
            return fallback

    def _experience_match(self, candidate_years: float, requirement_text: str) -> float:
        required = _parse_required_years(requirement_text)
        if required <= 0:
            return 1.0  # no requirement
        if candidate_years >= required:
            return 1.0
        if required == 0:
            return 1.0
        ratio = candidate_years / required
        # Graduated penalty: 80% experience → 0.85 score
        return max(0.0, min(1.0, 0.5 + ratio * 0.5))

    def _keyword_density(self, resume_text: str, job_text: str) -> float:
        if not job_text or not resume_text:
            return 0.0
        job_words = set(re.sub(r"[^\w\s]", " ", job_text.lower()).split())
        resume_words = set(re.sub(r"[^\w\s]", " ", resume_text.lower()).split())
        if not job_words:
            return 0.0
        overlap = len(resume_words & job_words)
        return min(1.0, overlap / len(job_words))

"""
Feature Engineering V3.0 — Production ATS-Style Candidate-Job Pair Features

Major redesign to answer: "How suitable is THIS candidate for THIS specific job?"
Not: "How good is this resume?"

Key changes:
- Role matching: Cloud Engineer vs Data Scientist = 15% similarity
- Domain-aware skill matching: Cloud skills don't boost Data Science jobs
- Hard constraints: Missing required skills = reject/penalty
- Pairwise features: Every score depends on BOTH resume AND job
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.ml.role_matcher import RoleMatcher
from backend.ml.skill_ontology import SkillOntology

logger = logging.getLogger(__name__)

# ── Canonical feature contract V3.0 ───────────────────────────────────────────

FEATURE_NAMES: List[str] = [
    # ── Core candidate-job matching [0-9] ────────────────────────────────────
    "role_similarity",              # Role matcher score (Cloud Eng vs ML Eng = 0.20)
    "domain_match_score",           # Skill ontology domain overlap
    "required_skill_match_ratio",   # Required skills matched / total required
    "preferred_skill_match_ratio",  # Preferred skills matched / total preferred
    "required_skill_coverage",      # Count of required skills matched (normalized)
    "missing_required_penalty",     # 1.0 if missing required skills, else 0.0
    "domain_mismatch_flag",         # 1.0 if top candidate domain not in job domains
    "experience_match_score",       # Years match (0=deficit, 0.5=exact, 1.0=surplus)
    "experience_gap",               # |required - candidate| / 15 (normalized)
    "seniority_alignment",          # Job seniority level vs candidate years tier

    # ── Text similarity [10-14] ──────────────────────────────────────────────
    "tfidf_similarity",             # Resume-job TF-IDF cosine
    "sbert_similarity",             # SBERT embedding cosine (or tfidf fallback)
    "bigram_similarity",            # Bigram TF-IDF
    "job_title_match",              # Job title words found in resume
    "keyword_density",              # Job keywords present in resume

    # ── Skill depth analysis [15-20] ─────────────────────────────────────────
    "technical_depth",              # Total unique skills candidate has
    "technical_breadth",            # Number of distinct domains covered
    "skill_domain_overlap_count",   # Count of overlapping domains
    "extra_relevant_skills",        # Non-required job-relevant skills candidate has
    "tech_skills_ratio",            # Fraction of skills that are technical
    "skills_per_experience_year",   # Skill accumulation rate

    # ── Education & credentials [21-24] ──────────────────────────────────────
    "education_level_score",        # PhD=1.0, Master=0.8, Bachelor=0.6, etc.
    "education_requirement_met",    # 1.0 if meets job requirement
    "has_relevant_degree",          # Degree field matches job domain
    "certifications_normalized",    # min(cert_count, 5) / 5

    # ── Experience quality [25-29] ───────────────────────────────────────────
    "years_experience_normalized",  # min(years, 20) / 20
    "has_leadership_signals",       # Led/managed/mentored keywords
    "has_quantified_achievements",  # Numbers/metrics in resume
    "career_progression",           # Senior/Lead/Principal growth terms
    "multiple_companies",           # Worked at 2+ companies

    # ── Resume quality [30-34] ───────────────────────────────────────────────
    "ats_completeness",             # Resume completeness score / 100
    "has_contact_info",             # Email + phone present
    "has_professional_links",       # GitHub/LinkedIn/Portfolio
    "has_projects",                 # Projects section exists
    "section_completeness",         # Major sections present / 6

    # ── Advanced matching [35-39] ────────────────────────────────────────────
    "job_coverage_ratio",           # Fraction of job sentences covered by resume
    "functional_area_match",        # Engineering/Data/Product alignment
    "industry_match",               # Industry keyword overlap
    "soft_skill_overlap",           # Communication/Leadership/Teamwork match
    "location_match",               # If location data available (placeholder)
]

VERSION = "3.0"

# Singleton instances
_role_matcher = None
_skill_ontology = None


def get_role_matcher() -> RoleMatcher:
    """Lazy-load role matcher singleton."""
    global _role_matcher
    if _role_matcher is None:
        _role_matcher = RoleMatcher()
    return _role_matcher


def get_skill_ontology() -> SkillOntology:
    """Lazy-load skill ontology singleton."""
    global _skill_ontology
    if _skill_ontology is None:
        _skill_ontology = SkillOntology()
    return _skill_ontology


# ── Helper functions ──────────────────────────────────────────────────────────

def _safe_val(v: Any, default: float = 0.0) -> float:
    """Coerce value to finite float in [0, 1]."""
    try:
        f = float(v) if v is not None else default
        if not math.isfinite(f):
            return default
        return max(0.0, min(1.0, f))
    except (TypeError, ValueError):
        return default


def _safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division with default."""
    if denominator == 0:
        return default
    return numerator / denominator


def _parse_required_years(text: str) -> float:
    """Extract minimum years from '3-5 years' or '5+ years'."""
    if not text:
        return 0.0
    m = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*year', text.lower())
    if m:
        return float(m.group(1))
    m = re.search(r'(\d+)\+?\s*year', text.lower())
    if m:
        return float(m.group(1))
    return 0.0


def _compute_tfidf_similarity(text1: str, text2: str, ngram_range: Tuple[int, int] = (1, 1)) -> float:
    """Compute TF-IDF cosine similarity."""
    if not text1 or not text2:
        return 0.0
    try:
        vectorizer = TfidfVectorizer(ngram_range=ngram_range, max_features=500, stop_words='english')
        tfidf = vectorizer.fit_transform([text1, text2])
        sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return float(sim)
    except Exception:
        return 0.0


def _education_level_score(education_list: List[str]) -> float:
    """Convert education to normalized score."""
    if not education_list:
        return 0.0

    education_text = " ".join(education_list).lower()

    levels = [
        ("phd", 1.0), ("ph.d", 1.0), ("doctorate", 1.0),
        ("master", 0.8), ("mba", 0.8), ("m.s", 0.8), ("msc", 0.8),
        ("bachelor", 0.6), ("b.s", 0.6), ("b.tech", 0.6), ("btech", 0.6),
        ("associate", 0.4), ("diploma", 0.3),
        ("high school", 0.2),
    ]

    for keyword, score in levels:
        if keyword in education_text:
            return score

    return 0.0


def _has_keyword(text: str, keywords: List[str]) -> bool:
    """Check if any keyword exists in text."""
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


# ── Main Extractor ────────────────────────────────────────────────────────────

class ResumeFeatureExtractor:
    """
    Extract 40 pairwise features for candidate-job pairs.

    This is the production ATS approach: every feature measures fit between
    THIS candidate and THIS specific job.
    """

    def __init__(self):
        self.role_matcher = get_role_matcher()
        self.skill_ontology = get_skill_ontology()
        logger.info("ResumeFeatureExtractor V3.0 initialized (40 features)")

    def extract_single(
        self,
        resume: Dict[str, Any],
        job: Dict[str, Any],
        resume_emb: Optional[np.ndarray] = None,
        job_emb: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Extract feature vector for ONE candidate-job pair.

        Args:
            resume: Parsed resume dict with keys:
                - cleaned_text: str
                - skills: List[str]
                - experience_years: float
                - education: List[str]
                - certifications: List[str]
                - projects: List[str]
                - companies: List[str]
                - job_titles: List[str]
                - completeness_score: float (0-100)
                - portfolio_url: str
                - github_url: str
            job: Job dict with keys:
                - title: str
                - description: str
                - cleaned_text: str
                - required_skills: List[str]
                - preferred_skills: List[str]
                - experience_requirement: str
                - education_requirement: str
            resume_emb: Optional pre-computed SBERT embedding
            job_emb: Optional pre-computed SBERT embedding

        Returns:
            np.ndarray of shape (40,) with all features
        """
        features = []

        resume_text = resume.get("cleaned_text", "") or resume.get("raw_text", "")
        job_text = job.get("cleaned_text", "") or job.get("description", "")

        candidate_skills = resume.get("skills", [])
        required_skills = job.get("required_skills", [])
        preferred_skills = job.get("preferred_skills", [])
        candidate_years = float(resume.get("experience_years", 0))
        required_years = _parse_required_years(job.get("experience_requirement", ""))

        # ── [0-9] Core candidate-job matching ────────────────────────────────

        # Role matching
        role_analysis = self.role_matcher.analyze_role_match(resume_text, job_text)
        role_similarity = role_analysis["role_similarity"]
        features.append(role_similarity)

        # Domain matching
        domain_analysis = self.skill_ontology.compute_domain_match(
            candidate_skills, required_skills, preferred_skills
        )
        domain_match_score = domain_analysis["domain_match_score"]
        is_domain_mismatch = float(domain_analysis["is_domain_mismatch"])
        features.append(domain_match_score)

        # Skill matching
        skill_match = self.skill_ontology.compute_skill_match(
            candidate_skills, required_skills, preferred_skills
        )
        required_ratio = skill_match["required_match_ratio"]
        preferred_ratio = skill_match["preferred_match_ratio"]
        required_count = skill_match["required_match_count"]
        missing_required = float(len(skill_match["missing_required"]) > 0)

        features.append(required_ratio)
        features.append(preferred_ratio)
        features.append(min(required_count / 10.0, 1.0))  # Normalized count
        features.append(missing_required)
        features.append(is_domain_mismatch)

        # Experience matching
        if required_years == 0:
            exp_match = 0.5  # Neutral
            exp_gap = 0.0
        else:
            diff = candidate_years - required_years
            if diff >= 0:
                exp_match = min(0.5 + (diff / 10.0) * 0.5, 1.0)  # Surplus is good
            else:
                exp_match = max(0.5 + (diff / required_years) * 0.5, 0.0)  # Deficit is bad
            exp_gap = min(abs(diff) / 15.0, 1.0)

        features.append(exp_match)
        features.append(exp_gap)

        # Seniority alignment
        job_seniority = self._detect_seniority_level(job_text)
        candidate_seniority = self._years_to_seniority(candidate_years)
        seniority_diff = abs(job_seniority - candidate_seniority)
        seniority_alignment = 1.0 - min(seniority_diff, 1.0)
        features.append(seniority_alignment)

        # ── [10-14] Text similarity ──────────────────────────────────────────

        tfidf_sim = _compute_tfidf_similarity(resume_text, job_text, ngram_range=(1, 1))
        features.append(tfidf_sim)

        # SBERT similarity
        if resume_emb is not None and job_emb is not None:
            sbert_sim = float(cosine_similarity(resume_emb.reshape(1, -1), job_emb.reshape(1, -1))[0][0])
        else:
            sbert_sim = tfidf_sim  # Fallback
        features.append(_safe_val(sbert_sim))

        bigram_sim = _compute_tfidf_similarity(resume_text, job_text, ngram_range=(2, 2))
        features.append(bigram_sim)

        job_title = job.get("title", "")
        job_title_words = set(job_title.lower().split())
        resume_lower = resume_text.lower()
        title_match = sum(1 for w in job_title_words if w in resume_lower) / max(len(job_title_words), 1)
        features.append(title_match)

        # Keyword density
        job_words = set(job_text.lower().split())
        resume_words = set(resume_text.lower().split())
        common_words = job_words & resume_words
        keyword_density = len(common_words) / max(len(job_words), 1)
        features.append(min(keyword_density * 5, 1.0))  # Scale up

        # ── [15-20] Skill depth ──────────────────────────────────────────────

        technical_depth = min(len(candidate_skills) / 30.0, 1.0)
        features.append(technical_depth)

        breadth = self.skill_ontology.compute_technical_breadth(candidate_skills)
        features.append(breadth)

        domain_overlap_count = len(domain_analysis["domain_overlap"])
        features.append(min(domain_overlap_count / 3.0, 1.0))

        extra_skills = skill_match["extra_skills"]
        # Filter extras to only job-relevant domains
        job_domains = set(domain_analysis["job_required_domains"].keys())
        relevant_extras = [s for s in extra_skills if self.skill_ontology.get_skill_domain(s) in job_domains]
        features.append(min(len(relevant_extras) / 10.0, 1.0))

        tech_ratio = sum(1 for s in candidate_skills if self.skill_ontology.get_skill_domain(s) != "Other") / max(len(candidate_skills), 1)
        features.append(tech_ratio)

        skills_per_year = len(candidate_skills) / max(candidate_years, 1.0)
        features.append(min(skills_per_year / 5.0, 1.0))

        # ── [21-24] Education ────────────────────────────────────────────────

        education_list = resume.get("education", [])
        edu_score = _education_level_score(education_list)
        features.append(edu_score)

        edu_requirement = job.get("education_requirement", "").lower()
        if not edu_requirement or "any" in edu_requirement:
            edu_met = 1.0
        elif "phd" in edu_requirement or "doctorate" in edu_requirement:
            edu_met = 1.0 if edu_score >= 1.0 else 0.5
        elif "master" in edu_requirement:
            edu_met = 1.0 if edu_score >= 0.8 else 0.6
        elif "bachelor" in edu_requirement:
            edu_met = 1.0 if edu_score >= 0.6 else 0.4
        else:
            edu_met = 0.7  # Neutral
        features.append(edu_met)

        # Relevant degree (domain match)
        edu_text = " ".join(education_list).lower()
        relevant_degree = 1.0 if any(d in edu_text for d in ["computer", "engineering", "science", "technology", "data", "math"]) else 0.0
        features.append(relevant_degree)

        cert_count = len(resume.get("certifications", []))
        features.append(min(cert_count / 5.0, 1.0))

        # ── [25-29] Experience quality ───────────────────────────────────────

        features.append(min(candidate_years / 20.0, 1.0))

        leadership_keywords = ["led", "managed", "supervised", "mentored", "director", "manager", "head", "vp"]
        has_leadership = float(_has_keyword(resume_text, leadership_keywords))
        features.append(has_leadership)

        has_numbers = float(bool(re.search(r'\d+%|\$\d+|\d+[KMB]|\d+x', resume_text)))
        features.append(has_numbers)

        career_growth_keywords = ["senior", "lead", "principal", "promoted", "advancement"]
        career_progression = float(_has_keyword(resume_text, career_growth_keywords))
        features.append(career_progression)

        companies = resume.get("companies", [])
        multiple_companies = 1.0 if len(companies) >= 2 else 0.0
        features.append(multiple_companies)

        # ── [30-34] Resume quality ───────────────────────────────────────────

        completeness = resume.get("completeness_score", 50.0)
        features.append(completeness / 100.0)

        has_email = float(bool(resume.get("email")))
        has_phone = float(bool(resume.get("phone")))
        has_contact = (has_email + has_phone) / 2.0
        features.append(has_contact)

        has_github = float(bool(resume.get("github_url")))
        has_portfolio = float(bool(resume.get("portfolio_url")))
        professional_links = (has_github + has_portfolio) / 2.0
        features.append(professional_links)

        has_projects = float(len(resume.get("projects", [])) > 0)
        features.append(has_projects)

        # Section completeness (6 major sections)
        sections = [
            bool(resume.get("email")),
            bool(candidate_skills),
            bool(education_list),
            bool(candidate_years > 0),
            bool(resume.get("projects")),
            bool(resume.get("certifications")),
        ]
        section_completeness = sum(sections) / 6.0
        features.append(section_completeness)

        # ── [35-39] Advanced matching ────────────────────────────────────────

        # Job coverage ratio
        job_sentences = [s.strip() for s in job_text.split('.') if len(s.strip()) > 10]
        resume_words_set = set(resume_text.lower().split())
        covered = sum(1 for sent in job_sentences if any(w in resume_words_set for w in sent.lower().split()))
        job_coverage = _safe_divide(covered, len(job_sentences), 0.0)
        features.append(job_coverage)

        # Functional area match
        functional_areas = {
            "engineering": ["engineer", "developer", "software", "backend", "frontend"],
            "data": ["data", "analyst", "scientist", "ml", "machine learning"],
            "product": ["product", "manager", "pm", "owner"],
        }
        job_area = None
        for area, keywords in functional_areas.items():
            if any(kw in job_text.lower() for kw in keywords):
                job_area = area
                break

        if job_area and any(kw in resume_text.lower() for kw in functional_areas.get(job_area, [])):
            functional_match = 1.0
        else:
            functional_match = 0.3
        features.append(functional_match)

        # Industry match (placeholder)
        features.append(0.5)

        # Soft skill overlap
        soft_skills = ["communication", "teamwork", "leadership", "analytical", "problem solving"]
        job_soft = sum(1 for s in soft_skills if s in job_text.lower())
        resume_soft = sum(1 for s in soft_skills if s in resume_text.lower())
        soft_overlap = min(resume_soft, job_soft) / max(job_soft, 1)
        features.append(soft_overlap)

        # Location match (placeholder — not implemented yet)
        features.append(0.5)

        return np.array(features, dtype=np.float32)

    def _detect_seniority_level(self, text: str) -> float:
        """Detect job seniority level from text."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["senior", "sr.", "lead", "principal", "staff"]):
            return 0.8
        elif any(kw in text_lower for kw in ["junior", "jr.", "entry", "associate"]):
            return 0.2
        else:
            return 0.5  # Mid-level

    def _years_to_seniority(self, years: float) -> float:
        """Convert years of experience to seniority tier."""
        if years < 2:
            return 0.0  # Entry
        elif years < 5:
            return 0.33  # Mid
        elif years < 10:
            return 0.67  # Senior
        else:
            return 1.0  # Principal/Staff

    def extract_batch(
        self,
        resumes: List[Dict[str, Any]],
        jobs: List[Dict[str, Any]],
    ) -> np.ndarray:
        """Extract features for multiple candidate-job pairs."""
        features_list = []
        for resume, job in zip(resumes, jobs):
            features_list.append(self.extract_single(resume, job))
        return np.array(features_list, dtype=np.float32)

    def extract_from_dataframe_row(self, row: Dict[str, Any]) -> np.ndarray:
        """
        Extract features from CSV training data row.

        Expected columns:
        - resume_text, job_title, job_description
        - skills, required_skills, preferred_skills
        - experience_years, experience_requirement
        - education, education_requirement
        - projects, certifications, etc.
        """
        def parse_list(val, sep=","):
            if isinstance(val, list):
                return [str(v).strip() for v in val if v]
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return []
            return [s.strip() for s in str(val).split(sep) if s.strip()]

        def safe_float(val, default=0.0):
            try:
                f = float(val)
                return default if not math.isfinite(f) else f
            except:
                return default

        resume = {
            "cleaned_text": str(row.get("resume_text") or ""),
            "skills": parse_list(row.get("skills")),
            "experience_years": safe_float(row.get("experience_years"), 0.0),
            "education": parse_list(row.get("education")),
            "certifications": parse_list(row.get("certifications")),
            "projects": parse_list(row.get("projects")),
            "companies": parse_list(row.get("companies")),
            "job_titles": parse_list(row.get("job_titles")),
            "completeness_score": safe_float(row.get("ats_score"), 50.0),
            "portfolio_url": str(row.get("portfolio_url") or ""),
            "github_url": str(row.get("github_url") or ""),
            "email": str(row.get("email") or ""),
            "phone": str(row.get("phone") or ""),
        }

        job = {
            "title": str(row.get("job_title") or ""),
            "description": str(row.get("job_description") or ""),
            "cleaned_text": str(row.get("job_description") or ""),
            "required_skills": parse_list(row.get("required_skills")),
            "preferred_skills": parse_list(row.get("preferred_skills")),
            "experience_requirement": str(row.get("experience_requirement") or ""),
            "education_requirement": str(row.get("education_requirement") or ""),
        }

        return self.extract_single(resume, job)

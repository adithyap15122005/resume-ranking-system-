"""
Feature Engineering — canonical 51-feature vector for resume-vs-job scoring.

Used identically at training time (from CSV via extract_from_dataframe_row)
and at inference time (from live DB objects via extract_single).
Never fit any stateful transformer here — this module is pure extraction.
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ── Canonical feature contract ────────────────────────────────────────────────

FEATURE_NAMES: List[str] = [
    # ── Original 16 — positions 0-15 unchanged ───────────────────────────────
    "tfidf_similarity",           # TF-IDF cosine sim between resume & job text
    "sbert_similarity",           # SBERT embedding cosine sim (falls back to tfidf)
    "skill_match_required",       # required skills covered by resume (0-1)
    "skill_match_preferred",      # preferred skills covered by resume (0-1)
    "experience_match",           # years-of-experience match score (0-1)
    "education_score",            # education level match vs job requirement (0-1)
    "ats_score",                  # resume completeness / 100 (0-1)
    "projects_count_norm",        # min(projects, 10) / 10
    "certifications_count_norm",  # min(certs, 5) / 5
    "languages_count_norm",       # min(languages, 5) / 5
    "soft_skills_count_norm",     # min(soft_skills, 10) / 10
    "has_portfolio",              # 1 if portfolio_url present
    "has_github",                 # 1 if github_url present
    "years_experience_norm",      # min(years, 15) / 15
    "skills_count_norm",          # min(total skills, 30) / 30
    "keyword_density",            # job-keyword unigram coverage in resume
    # ── Text similarity additions [16-21] ─────────────────────────────────────
    "bigram_similarity",          # bigram TF-IDF cosine sim
    "title_match_score",          # fraction of job title words found in resume
    "job_coverage_ratio",         # fraction of job sentences with ≥1 resume word hit
    "tech_term_match",            # technical keyword set overlap
    "resume_length_norm",         # min(word_count, 1000) / 1000
    "vocabulary_richness",        # unique words / total words
    # ── Experience quality [22-26] ────────────────────────────────────────────
    "experience_surplus_norm",    # over-qualification (candidate > required)
    "experience_deficit_norm",    # under-qualification (required > candidate)
    "seniority_level",            # tier: entry/mid/senior/exec 0/0.33/0.67/1.0
    "leadership_score",           # management/leadership keywords in resume
    "quantification_score",       # presence of numbers/metrics (%, $, K, M)
    # ── Skills depth [27-31] ──────────────────────────────────────────────────
    "skill_gap_required",         # 1 - skill_match_required
    "skill_gap_preferred",        # 1 - skill_match_preferred
    "raw_skill_overlap_norm",     # raw matching required-skill count / 20
    "tech_skills_ratio",          # fraction of skills that are technical
    "skills_per_year_norm",       # skills_count / max(years, 1) / 5 clamped
    # ── Education & credentials [32-35] ───────────────────────────────────────
    "candidate_education_level",  # absolute level (phd=1.0, master=0.8, bachelor=0.6)
    "has_relevant_degree",        # 1 if degree field overlaps job domain
    "certifications_per_year_norm", # certs / max(years, 1) / 2 clamped
    "total_credentials_norm",     # (certs_norm + edu_level) / 2
    # ── Resume quality signals [36-41] ───────────────────────────────────────
    "has_summary",                # 1 if summary/objective section detected
    "has_work_experience_section",# 1 if work experience section detected
    "has_education_section",      # 1 if education section detected
    "section_completeness",       # detected major sections / 6
    "achievement_density",        # achievement verbs per 100 words
    "contact_completeness",       # email + phone + linkedin presence 0-1
    # ── Career trajectory [42-46] ────────────────────────────────────────────
    "career_growth_score",        # seniority-advancement terms in resume
    "multi_company_indicator",    # presence of multiple employer contexts
    "industry_match_score",       # domain/industry keyword overlap
    "soft_skill_overlap",         # soft-skill terms in job found in resume
    "professional_presence",      # portfolio + github + linkedin signals
    # ── Domain & role fit [47-50] ────────────────────────────────────────────
    "functional_area_match",      # functional area alignment (eng/data/product)
    "description_keyword_density",# long-tail job description keyword match
    "role_seniority_match",       # job seniority words match candidate years tier
    "job_title_word_count_norm",  # min(job title words, 10) / 10
]

VERSION = "2.0"

# Education levels (longest-first to hit highest tier on substring match)
_EDUCATION_LEVELS: List[Tuple[str, float]] = [
    ("phd", 1.0), ("ph.d", 1.0), ("doctorate", 1.0),
    ("master", 0.8), ("mba", 0.8), ("msc", 0.8), ("m.s", 0.8), ("m.eng", 0.8),
    ("bachelor", 0.6), ("b.s", 0.6), ("b.e", 0.6), ("btech", 0.6), ("b.tech", 0.6),
    ("b.a", 0.6), ("undergraduate", 0.6),
    ("associate", 0.4), ("diploma", 0.3),
    ("high school", 0.2), ("secondary", 0.2), ("ged", 0.2),
]

_TECH_KEYWORDS = frozenset([
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
    "rust", "scala", "kotlin", "swift", "r", "matlab", "sql", "nosql",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "cassandra",
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible",
    "react", "angular", "vue", "node", "django", "flask", "fastapi", "spring",
    "tensorflow", "pytorch", "scikit", "pandas", "spark", "hadoop", "kafka",
    "git", "linux", "bash", "rest", "graphql", "grpc", "microservices",
    "machine learning", "deep learning", "nlp", "computer vision", "mlops",
    "data engineering", "devops", "ci/cd", "agile", "scrum",
])

_SOFT_SKILL_KEYWORDS = frozenset([
    "communication", "teamwork", "leadership", "problem solving", "analytical",
    "creative", "adaptable", "organized", "detail oriented", "proactive",
    "collaborative", "motivated", "flexible", "empathy", "negotiation",
    "presentation", "mentoring", "time management", "critical thinking",
    "interpersonal", "written", "verbal", "conflict resolution",
])

_LEADERSHIP_KEYWORDS = frozenset([
    "led", "managed", "supervised", "mentored", "coached", "directed",
    "oversaw", "owned", "drove", "spearheaded", "headed", "established",
    "founded", "hired", "director", "manager", "vp", "vice president",
    "head of", "chief", "president", "principal", "staff engineer", "architect",
])

_ACHIEVEMENT_VERBS = frozenset([
    "increased", "decreased", "reduced", "improved", "optimized", "accelerated",
    "delivered", "built", "launched", "deployed", "scaled", "automated",
    "streamlined", "saved", "generated", "achieved", "exceeded", "grew",
    "developed", "designed", "implemented", "migrated", "refactored",
    "cut", "boosted", "doubled", "tripled", "eliminated", "transformed",
])

_CAREER_GROWTH_TERMS = frozenset([
    "senior", "lead", "principal", "staff", "director", "manager",
    "architect", "head", "chief", "vp", "promoted", "promotion",
    "advancement", "leadership role", "technical lead", "tech lead",
])

_SECTION_PATTERNS = [
    re.compile(r"\b(summary|objective|profile|about me)\b", re.I),
    re.compile(r"\b(experience|employment|work history|career|positions held)\b", re.I),
    re.compile(r"\b(education|academic|qualifications|degrees)\b", re.I),
    re.compile(r"\b(skills|technologies|competencies|expertise|tech stack)\b", re.I),
    re.compile(r"\b(projects|portfolio|achievements|accomplishments)\b", re.I),
    re.compile(r"\b(certifications?|certificates?|licenses?)\b", re.I),
]

_CONTACT_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}"),
    re.compile(r"(\+?\d[\d\s\-().]{7,}\d)"),
    re.compile(r"linkedin\.com/in/", re.I),
]

_FUNCTIONAL_AREAS = {
    "engineering":  ["engineer", "developer", "programming", "software", "backend", "frontend", "devops"],
    "data":         ["data scientist", "data analyst", "machine learning", "ml engineer", "analytics", "bi"],
    "product":      ["product manager", "product owner", "roadmap", "stakeholder", "user story"],
    "design":       ["ux", "ui", "designer", "figma", "sketch", "wireframe", "user research"],
    "finance":      ["finance", "accounting", "cpa", "financial analyst", "budget", "forecasting"],
    "hr":           ["human resources", "recruiter", "talent acquisition", "hrbp", "people ops"],
    "marketing":    ["marketing", "seo", "campaign", "brand", "content", "growth", "demand gen"],
    "sales":        ["sales", "account executive", "business development", "revenue", "quota"],
}

_INDUSTRY_KEYWORDS = {
    "tech":     ["saas", "startup", "platform", "api", "cloud", "b2b", "b2c", "enterprise software"],
    "finance":  ["fintech", "banking", "trading", "investment", "payments", "crypto", "defi"],
    "health":   ["healthcare", "hospital", "clinical", "medical", "pharma", "biotech", "patient"],
    "ecommerce":["ecommerce", "retail", "marketplace", "supply chain", "logistics", "fulfillment"],
    "media":    ["media", "streaming", "content", "publishing", "advertising", "social media"],
    "education":["edtech", "learning", "curriculum", "student", "university", "k-12", "online course"],
}


# ── Module-level helpers ──────────────────────────────────────────────────────

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
    """0.5 if no requirement (neutral), else match highest resume level to job level."""
    if not job_requirement:
        return 0.5
    req_lower = job_requirement.lower()
    required_level = 0.0
    for keyword, level in _EDUCATION_LEVELS:
        if keyword in req_lower:
            required_level = level
            break
    if required_level == 0.0:
        return 0.5
    resume_text = " ".join(str(e) for e in (resume_education or [])).lower()
    candidate_level = 0.0
    for keyword, level in _EDUCATION_LEVELS:
        if keyword in resume_text:
            candidate_level = max(candidate_level, level)
    if candidate_level == 0.0:
        return 0.2
    if candidate_level >= required_level:
        return 1.0
    return max(0.0, 1.0 - (required_level - candidate_level))


def _candidate_edu_level(education_list: List[Any]) -> float:
    """Absolute education level of the candidate (0 if unknown)."""
    text = " ".join(str(e) for e in (education_list or [])).lower()
    for keyword, level in _EDUCATION_LEVELS:
        if keyword in text:
            return level
    return 0.0


# ── Main extractor ────────────────────────────────────────────────────────────

class ResumeFeatureExtractor:
    """
    Stateless extractor that computes the canonical FEATURE_NAMES vector.
    Call extract_single() at inference, extract_from_dataframe_row() at training.
    """

    FEATURE_NAMES = FEATURE_NAMES
    VERSION = VERSION

    # ── Public API ────────────────────────────────────────────────────────────

    def extract_single(
        self,
        resume_dict: Dict[str, Any],
        job_dict: Dict[str, Any],
        resume_emb: Optional[np.ndarray] = None,
        job_emb: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Returns a 1-D float32 array of shape (51,) with all values in [0, 1].
        Missing/invalid inputs default to 0.0 (0.5 for education_score).
        """
        resume_text = str(resume_dict.get("cleaned_text") or resume_dict.get("raw_text") or "")
        job_text = str(job_dict.get("cleaned_text") or job_dict.get("description") or "")
        job_title = str(job_dict.get("title") or "")

        # Core text similarity
        tfidf_sim = self._tfidf_sim(job_text, resume_text)
        sbert_sim = self._sbert_sim(resume_emb, job_emb, fallback=tfidf_sim)

        # Skills
        required_skills = [s.lower().strip() for s in (job_dict.get("required_skills") or []) if s]
        preferred_skills = [s.lower().strip() for s in (job_dict.get("preferred_skills") or []) if s]
        candidate_skills = {s.lower().strip() for s in (resume_dict.get("skills") or []) if s}
        req_set = set(required_skills)
        pref_set = set(preferred_skills)
        # 0.5 neutral when no skills specified (not 1.0 — that inflates wrong-role scores)
        skill_match_req = len(candidate_skills & req_set) / len(req_set) if req_set else 0.5
        skill_match_pref = len(candidate_skills & pref_set) / len(pref_set) if pref_set else 0.0

        # Experience
        exp_years = float(resume_dict.get("experience_years") or 0.0)
        exp_req_text = str(job_dict.get("experience_requirement") or "")
        experience_match = self._experience_match(exp_years, exp_req_text)

        # Education
        education_list = resume_dict.get("education") or []
        edu_score = _education_score(education_list, job_dict.get("education_requirement") or "")

        # ATS
        ats_raw = _safe_val(resume_dict.get("completeness_score", 0.0))
        ats = ats_raw / 100.0 if ats_raw > 1.0 else ats_raw

        # Counts
        projects = resume_dict.get("projects") or []
        certs = resume_dict.get("certifications") or []
        langs = resume_dict.get("languages") or []
        soft = resume_dict.get("soft_skills") or []
        has_portfolio = 1.0 if resume_dict.get("portfolio_url") else 0.0
        has_github = 1.0 if resume_dict.get("github_url") else 0.0
        kd = self._keyword_density(resume_text, job_text)

        # Text similarity additions
        bigram_sim = self._bigram_similarity(job_text, resume_text)
        title_match = self._title_match_score(job_title, resume_text)
        job_coverage = self._job_coverage_ratio(job_text, resume_text)
        tech_match = self._tech_term_match(job_text, resume_text)
        resume_len = _safe_val(min(len(resume_text.split()), 1000) / 1000.0)
        vocab_rich = self._vocabulary_richness(resume_text)

        # Experience quality
        req_years = _parse_required_years(exp_req_text)
        exp_surplus = _safe_val(min(max(0.0, exp_years - req_years), 15.0) / 15.0)
        exp_deficit = _safe_val(min(max(0.0, req_years - exp_years), 15.0) / 15.0)
        seniority = self._seniority_level(exp_years)
        leadership = self._leadership_score(resume_text)
        quantification = self._quantification_score(resume_text)

        # Skills depth
        skill_gap_req = _safe_val(1.0 - skill_match_req)
        skill_gap_pref = _safe_val(1.0 - skill_match_pref)
        raw_overlap = _safe_val(min(len(candidate_skills & req_set), 20) / 20.0)
        tech_ratio = self._tech_skills_ratio(list(candidate_skills))
        skills_per_yr = _safe_val(min(len(candidate_skills) / max(exp_years, 1.0) / 5.0, 1.0))

        # Education & credentials
        cand_edu_level = _safe_val(_candidate_edu_level(education_list))
        has_rel_degree = self._has_relevant_degree(education_list, job_text)
        certs_per_yr = _safe_val(min(len(certs) / max(exp_years, 1.0) / 2.0, 1.0))
        total_creds = _safe_val((min(len(certs) / 5.0, 1.0) + cand_edu_level) / 2.0)

        # Resume quality signals
        has_summ = self._has_section(resume_text, _SECTION_PATTERNS[0])
        has_work = self._has_section(resume_text, _SECTION_PATTERNS[1])
        has_edu_sec = self._has_section(resume_text, _SECTION_PATTERNS[2])
        sec_complete = _safe_val(
            sum(1.0 for p in _SECTION_PATTERNS if p.search(resume_text)) / len(_SECTION_PATTERNS)
        )
        achievement_d = self._achievement_density(resume_text)
        contact_comp = self._contact_completeness(resume_text)

        # Career trajectory
        career_growth = self._career_growth_score(resume_text)
        multi_co = self._multi_company_indicator(resume_text)
        industry_match = self._industry_match_score(job_text, resume_text)
        soft_overlap = self._soft_skill_overlap(job_text, resume_text)
        prof_presence = _safe_val(
            (has_portfolio + has_github + (1.0 if "linkedin" in resume_text.lower() else 0.0)) / 3.0
        )

        # Domain & role fit
        func_area = self._functional_area_match(job_text, resume_text)
        desc_kd = self._description_keyword_density(job_text, resume_text)
        role_sen_match = self._role_seniority_match(job_text, exp_years)
        title_wc_norm = _safe_val(min(len(job_title.split()), 10) / 10.0)

        features = np.array([
            # Original 16
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
            # Text similarity additions
            _safe_val(bigram_sim),
            _safe_val(title_match),
            _safe_val(job_coverage),
            _safe_val(tech_match),
            resume_len,
            vocab_rich,
            # Experience quality
            exp_surplus,
            exp_deficit,
            _safe_val(seniority),
            _safe_val(leadership),
            _safe_val(quantification),
            # Skills depth
            skill_gap_req,
            skill_gap_pref,
            raw_overlap,
            _safe_val(tech_ratio),
            skills_per_yr,
            # Education & credentials
            cand_edu_level,
            _safe_val(has_rel_degree),
            certs_per_yr,
            _safe_val(total_creds),
            # Resume quality signals
            _safe_val(has_summ),
            _safe_val(has_work),
            _safe_val(has_edu_sec),
            sec_complete,
            achievement_d,
            contact_comp,
            # Career trajectory
            _safe_val(career_growth),
            _safe_val(multi_co),
            _safe_val(industry_match),
            _safe_val(soft_overlap),
            _safe_val(prof_presence),
            # Domain & role fit
            _safe_val(func_area),
            _safe_val(desc_kd),
            _safe_val(role_sen_match),
            title_wc_norm,
        ], dtype=np.float32)

        return features

    def extract_batch(
        self,
        resumes: List[Dict[str, Any]],
        job: Dict[str, Any],
        resume_embs: Optional[List[Optional[np.ndarray]]] = None,
        job_emb: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Returns a 2-D float32 array of shape (N, 51)."""
        if resume_embs is None:
            resume_embs = [None] * len(resumes)
        rows = [self.extract_single(r, job, emb, job_emb) for r, emb in zip(resumes, resume_embs)]
        n = len(FEATURE_NAMES)
        return np.vstack(rows).astype(np.float32) if rows else np.empty((0, n), dtype=np.float32)

    def extract_from_dataframe_row(self, row: Dict[str, Any]) -> np.ndarray:
        """
        Extract features from a CSV training row: one candidate × one job.

        Expected CSV columns:
          Job:       job_title, job_description, required_skills, preferred_skills,
                     experience_requirement, education_requirement
          Candidate: resume_text, skills, experience_years, education, certifications,
                     projects, ats_score, portfolio_url, github_url, soft_skills, languages
        """
        def parse_list(val: Any, sep: str = ",") -> List[str]:
            if isinstance(val, list):
                return [str(v).strip() for v in val if v]
            if val is None or (isinstance(val, float) and math.isnan(val)):
                return []
            return [s.strip() for s in str(val).split(sep) if s.strip()]

        def safe_float(val: Any, default: float = 0.0) -> float:
            try:
                f = float(val)
                return default if (f != f) else f
            except (TypeError, ValueError):
                return default

        resume_dict: Dict[str, Any] = {
            "cleaned_text":       str(row.get("resume_text") or ""),
            "raw_text":           str(row.get("resume_text") or ""),
            "skills":             parse_list(row.get("skills")),
            "experience_years":   safe_float(row.get("experience_years"), 0.0),
            "education":          parse_list(row.get("education")),
            "certifications":     parse_list(row.get("certifications")),
            "projects":           parse_list(row.get("projects")),
            "completeness_score": safe_float(row.get("ats_score"), 50.0),
            "portfolio_url":      str(row.get("portfolio_url") or ""),
            "github_url":         str(row.get("github_url") or ""),
            "soft_skills":        parse_list(row.get("soft_skills")),
            "languages":          parse_list(row.get("languages")),
        }
        job_dict: Dict[str, Any] = {
            "title":                  str(row.get("job_title") or ""),
            "description":            str(row.get("job_description") or ""),
            "cleaned_text":           str(row.get("job_description") or ""),
            "required_skills":        parse_list(row.get("required_skills")),
            "preferred_skills":       parse_list(row.get("preferred_skills")),
            "experience_requirement": str(row.get("experience_requirement") or ""),
            "education_requirement":  str(row.get("education_requirement") or ""),
        }
        return self.extract_single(resume_dict, job_dict, resume_emb=None, job_emb=None)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _tfidf_sim(self, job_text: str, resume_text: str) -> float:
        if not job_text or not resume_text:
            return 0.0
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            vec = TfidfVectorizer(max_features=8000, ngram_range=(1, 2), sublinear_tf=True)
            tfidf = vec.fit_transform([job_text, resume_text])
            return float(max(0.0, min(1.0, cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])))
        except Exception:
            return 0.0

    def _bigram_similarity(self, job_text: str, resume_text: str) -> float:
        if not job_text or not resume_text:
            return 0.0
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            vec = TfidfVectorizer(max_features=4000, ngram_range=(2, 2), sublinear_tf=True)
            tfidf = vec.fit_transform([job_text, resume_text])
            return float(max(0.0, min(1.0, cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])))
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
            sim = float(np.dot(job_emb.astype(np.float64), resume_emb.astype(np.float64)))
            return max(0.0, min(1.0, sim))
        except Exception:
            return fallback

    def _experience_match(self, candidate_years: float, requirement_text: str) -> float:
        required = _parse_required_years(requirement_text)
        if required <= 0:
            return 1.0
        if candidate_years >= required:
            return 1.0
        return max(0.0, min(1.0, 0.5 + (candidate_years / required) * 0.5))

    def _keyword_density(self, resume_text: str, job_text: str) -> float:
        if not job_text or not resume_text:
            return 0.0
        job_words = set(re.sub(r"[^\w\s]", " ", job_text.lower()).split())
        resume_words = set(re.sub(r"[^\w\s]", " ", resume_text.lower()).split())
        if not job_words:
            return 0.0
        return min(1.0, len(resume_words & job_words) / len(job_words))

    def _title_match_score(self, job_title: str, resume_text: str) -> float:
        if not job_title or not resume_text:
            return 0.0
        stopwords = {"and", "or", "the", "a", "of", "for", "in", "at", "to"}
        title_words = set(re.sub(r"[^\w\s]", " ", job_title.lower()).split()) - stopwords
        if not title_words:
            return 0.0
        resume_lower = resume_text.lower()
        hits = sum(1 for w in title_words if w in resume_lower)
        return min(1.0, hits / len(title_words))

    def _job_coverage_ratio(self, job_text: str, resume_text: str) -> float:
        if not job_text or not resume_text:
            return 0.0
        sentences = [s.strip() for s in re.split(r"[.!?\n]", job_text) if len(s.strip()) > 10]
        if not sentences:
            return 0.0
        resume_words = set(re.sub(r"[^\w\s]", " ", resume_text.lower()).split())
        hits = 0
        for sent in sentences:
            sent_words = set(re.sub(r"[^\w\s]", " ", sent.lower()).split())
            if sent_words & resume_words:
                hits += 1
        return min(1.0, hits / len(sentences))

    def _tech_term_match(self, job_text: str, resume_text: str) -> float:
        if not job_text or not resume_text:
            return 0.0
        job_lower = job_text.lower()
        resume_lower = resume_text.lower()
        job_techs = {t for t in _TECH_KEYWORDS if t in job_lower}
        if not job_techs:
            return 0.0
        hits = sum(1 for t in job_techs if t in resume_lower)
        return min(1.0, hits / len(job_techs))

    def _vocabulary_richness(self, text: str) -> float:
        if not text:
            return 0.0
        words = text.lower().split()
        if not words:
            return 0.0
        return min(1.0, len(set(words)) / len(words))

    def _seniority_level(self, years: float) -> float:
        if years < 3:
            return 0.0
        if years < 6:
            return 0.33
        if years < 10:
            return 0.67
        return 1.0

    def _leadership_score(self, text: str) -> float:
        if not text:
            return 0.0
        text_lower = text.lower()
        hits = sum(1 for kw in _LEADERSHIP_KEYWORDS if kw in text_lower)
        return min(1.0, hits / 10.0)

    def _quantification_score(self, text: str) -> float:
        if not text:
            return 0.0
        words = text.split()
        if not words:
            return 0.0
        pattern = re.compile(r"\d+[%$kmb]|\$\d+|\d+x\b|[\d]+\s*(percent|million|billion|k\b)", re.I)
        hits = len(pattern.findall(text))
        return min(1.0, hits / max(len(words) / 20.0, 1.0))

    def _tech_skills_ratio(self, skills: List[str]) -> float:
        if not skills:
            return 0.0
        hits = sum(1 for s in skills if any(t in s.lower() for t in _TECH_KEYWORDS))
        return min(1.0, hits / len(skills))

    def _has_relevant_degree(self, education_list: List[Any], job_text: str) -> float:
        if not education_list or not job_text:
            return 0.0
        edu_text = " ".join(str(e) for e in education_list).lower()
        job_lower = job_text.lower()
        degree_fields = [
            "computer science", "software engineering", "information technology",
            "data science", "mathematics", "statistics", "electrical engineering",
            "mechanical engineering", "business", "finance", "marketing", "economics",
            "biology", "chemistry", "physics", "psychology", "communications",
        ]
        for field in degree_fields:
            if field in edu_text and any(w in job_lower for w in field.split()):
                return 1.0
        return 0.0

    def _has_section(self, text: str, pattern: re.Pattern) -> float:
        return 1.0 if pattern.search(text) else 0.0

    def _achievement_density(self, text: str) -> float:
        if not text:
            return 0.0
        words = text.lower().split()
        if not words:
            return 0.0
        hits = sum(1 for w in words if w.rstrip(".,;:") in _ACHIEVEMENT_VERBS)
        return min(1.0, hits / max(len(words) / 100.0, 1.0))

    def _contact_completeness(self, text: str) -> float:
        signals = sum(1 for p in _CONTACT_PATTERNS if p.search(text))
        return min(1.0, signals / len(_CONTACT_PATTERNS))

    def _career_growth_score(self, text: str) -> float:
        if not text:
            return 0.0
        text_lower = text.lower()
        hits = sum(1 for kw in _CAREER_GROWTH_TERMS if kw in text_lower)
        return min(1.0, hits / 5.0)

    def _multi_company_indicator(self, text: str) -> float:
        year_ranges = re.findall(r"\b(19|20)\d{2}\s*[-–]\s*(19|20)\d{2}\b", text)
        at_company = re.findall(r"\bat\s+[A-Z][a-zA-Z]", text)
        total = len(year_ranges) + len(at_company)
        return min(1.0, max(0.0, total - 1) / 5.0)

    def _industry_match_score(self, job_text: str, resume_text: str) -> float:
        if not job_text or not resume_text:
            return 0.0
        job_lower = job_text.lower()
        resume_lower = resume_text.lower()
        best = 0.0
        for _sector, keywords in _INDUSTRY_KEYWORDS.items():
            job_hits = sum(1 for kw in keywords if kw in job_lower)
            if job_hits == 0:
                continue
            resume_hits = sum(1 for kw in keywords if kw in resume_lower)
            score = resume_hits / job_hits
            if score > best:
                best = score
        return min(1.0, best)

    def _soft_skill_overlap(self, job_text: str, resume_text: str) -> float:
        if not job_text or not resume_text:
            return 0.0
        job_lower = job_text.lower()
        resume_lower = resume_text.lower()
        job_soft = {kw for kw in _SOFT_SKILL_KEYWORDS if kw in job_lower}
        if not job_soft:
            return 0.0
        hits = sum(1 for kw in job_soft if kw in resume_lower)
        return min(1.0, hits / len(job_soft))

    def _functional_area_match(self, job_text: str, resume_text: str) -> float:
        if not job_text or not resume_text:
            return 0.0
        job_lower = job_text.lower()
        resume_lower = resume_text.lower()
        best = 0.0
        for _area, keywords in _FUNCTIONAL_AREAS.items():
            job_hits = sum(1 for kw in keywords if kw in job_lower)
            if job_hits == 0:
                continue
            score = min(1.0, sum(1 for kw in keywords if kw in resume_lower) / max(job_hits, 1))
            if score > best:
                best = score
        return best

    def _description_keyword_density(self, job_text: str, resume_text: str) -> float:
        """Long-tail match using only words ≥6 chars for specificity."""
        if not job_text or not resume_text:
            return 0.0
        job_words = {w for w in re.sub(r"[^\w\s]", " ", job_text.lower()).split() if len(w) >= 6}
        resume_words = set(re.sub(r"[^\w\s]", " ", resume_text.lower()).split())
        if not job_words:
            return 0.0
        return min(1.0, len(resume_words & job_words) / len(job_words))

    def _role_seniority_match(self, job_text: str, candidate_years: float) -> float:
        """Does the job's seniority expectation match the candidate's tier?"""
        if not job_text:
            return 0.5
        job_lower = job_text.lower()
        if any(kw in job_lower for kw in ["junior", "entry level", "intern", "graduate", "0-2"]):
            expected_tier = 0.0
        elif any(kw in job_lower for kw in ["senior", "lead", "principal", "staff", "7+", "8+"]):
            expected_tier = 0.67
        elif any(kw in job_lower for kw in ["director", "vp", "head of", "chief", "10+"]):
            expected_tier = 1.0
        else:
            expected_tier = 0.33
        diff = abs(self._seniority_level(candidate_years) - expected_tier)
        return max(0.0, 1.0 - diff)

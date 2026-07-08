"""
AI Candidate Intelligence Engine.
Generates scores, insights, strengths/weaknesses, career paths,
interview questions, and AI summaries for each candidate.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CandidateIntelligenceEngine:
    LEADERSHIP_KW = [
        "led", "managed", "supervised", "mentored", "directed", "coordinated",
        "founded", "established", "built team", "team lead", "principal",
        "head of", "vp", "director", "chief", "senior engineer", "architect",
    ]
    COMMUNICATION_KW = [
        "presented", "communicated", "collaborated", "documented", "published",
        "conference", "workshop", "stakeholder", "client-facing", "cross-functional",
        "blog", "wrote", "authored",
    ]
    ACHIEVEMENT_KW = [
        "increased", "decreased", "improved", "reduced", "saved", "generated",
        "delivered", "achieved", "exceeded", "launched", "deployed", "optimized",
        "%", "million", "thousand", "award",
    ]
    POSITIVE_CULTURE_KW = [
        "team", "collaboration", "agile", "scrum", "open source", "community",
        "volunteer", "mentor", "learning", "innovation", "passion", "growth",
    ]

    # ── Scores ────────────────────────────────────────────────────────────────

    def compute_leadership_score(self, text: str, experience_years: float = 0.0) -> float:
        text_l = text.lower()
        hits = sum(1 for kw in self.LEADERSHIP_KW if kw in text_l)
        kw_score = min(hits / 5, 1.0) * 50
        exp_score = min(experience_years / 10, 1.0) * 30
        return round(min(20.0 + kw_score + exp_score, 100.0), 1)

    def compute_communication_score(
        self,
        text: str,
        skills: Optional[List[str]] = None,
    ) -> float:
        text_l = text.lower()
        hits = sum(1 for kw in self.COMMUNICATION_KW if kw in text_l)
        skill_bonus = 0.0
        if skills:
            comm_skills = {"communication", "presentation", "writing", "public speaking"}
            matched = sum(1 for s in skills if s.lower() in comm_skills)
            skill_bonus = min(matched * 5, 10.0)
        return round(min(40.0 + min(hits / 5, 1.0) * 50 + skill_bonus, 100.0), 1)

    def compute_technical_score(
        self,
        skills: List[str],
        experience_years: float = 0.0,
        projects: Optional[List[str]] = None,
        certifications: Optional[List[str]] = None,
    ) -> float:
        breadth = min(len(skills) / 20, 1.0) * 50
        exp_bonus = min(experience_years / 10, 1.0) * 20
        proj_bonus = min(len(projects or []) / 5, 1.0) * 15
        cert_bonus = min(len(certifications or []) / 3, 1.0) * 15
        return round(min(breadth + exp_bonus + proj_bonus + cert_bonus, 100.0), 1)

    def compute_job_readiness(
        self,
        completeness: Optional[float] = None,
        experience_years: float = 0.0,
        skills_count: Optional[int] = None,
        *,
        skills: Optional[List[str]] = None,
        completeness_score: Optional[float] = None,
        certifications: Optional[List[str]] = None,
    ) -> float:
        """
        Flexible signature — accepts both positional call
        ``compute_job_readiness(completeness, exp, skills_count)``
        and keyword call
        ``compute_job_readiness(skills=[...], experience_years=X, completeness_score=Y, certifications=[...])``.
        """
        actual_completeness = (
            completeness_score if completeness is None else completeness
        ) or 0.0
        if skills_count is not None:
            actual_count = skills_count
        elif skills is not None:
            actual_count = len(skills)
        else:
            actual_count = 0

        cert_bonus = min(len(certifications or []) / 3, 1.0) * 10

        return round(
            min(
                actual_completeness * 0.35
                + min(experience_years / 5, 1.0) * 100 * 0.30
                + min(actual_count / 10, 1.0) * 100 * 0.25
                + cert_bonus,
                100.0,
            ),
            1,
        )

    def compute_culture_fit(self, text: str) -> float:
        text_l = text.lower()
        hits = sum(1 for kw in self.POSITIVE_CULTURE_KW if kw in text_l)
        return round(min(hits / len(self.POSITIVE_CULTURE_KW) * 100, 100.0), 1)

    def compute_confidence_score(self, completeness: float) -> float:
        return round(min(completeness, 95.0), 1)

    # ── Strengths / Weaknesses ────────────────────────────────────────────────

    def identify_strengths(
        self, resume_data: Dict[str, Any], job_skills: Optional[List[str]] = None
    ) -> List[str]:
        strengths = []
        skills = resume_data.get("skills") or []
        exp = resume_data.get("experience_years", 0)
        text = (resume_data.get("raw_text") or "").lower()

        if len(skills) >= 15:
            strengths.append(f"Broad technical skill set — {len(skills)} skills identified")
        if exp >= 5:
            strengths.append(f"Experienced professional with {exp:.0f}+ years")
        projects = resume_data.get("projects") or []
        if projects:
            strengths.append(f"Proven project delivery — {len(projects)} projects documented")
        certs = resume_data.get("certifications") or []
        if certs:
            strengths.append(f"Industry certified — {len(certs)} certification(s)")
        if any(kw in text for kw in ("tensorflow", "pytorch", "machine learning", "deep learning", "bert")):
            strengths.append("Demonstrated AI/ML expertise")
        if any(kw in text for kw in ("aws", "azure", "gcp", "cloud")):
            strengths.append("Cloud-native experience")
        edu = resume_data.get("education") or []
        if edu:
            strengths.append("Strong educational background")
        if job_skills:
            matched = [s for s in job_skills if s.lower() in {sk.lower() for sk in skills}]
            if len(matched) >= len(job_skills) * 0.7:
                strengths.append(f"Excellent skill alignment — {len(matched)}/{len(job_skills)} required skills")
        return strengths[:5]

    def identify_weaknesses(
        self, resume_data: Dict[str, Any], job_skills: Optional[List[str]] = None
    ) -> List[str]:
        weaknesses = []
        skills = {s.lower() for s in (resume_data.get("skills") or [])}
        exp = resume_data.get("experience_years", 0)
        completeness = resume_data.get("completeness_score", 0)

        if exp < 1:
            weaknesses.append("Limited professional experience")
        if not resume_data.get("certifications"):
            weaknesses.append("No industry certifications listed")
        if job_skills:
            missing = [s for s in job_skills if s.lower() not in skills][:3]
            if missing:
                weaknesses.append(f"Missing key skills: {', '.join(missing)}")
        if not resume_data.get("projects"):
            weaknesses.append("No projects portfolio documented")
        if completeness < 60:
            weaknesses.append("Resume completeness is low — key sections may be missing")
        return weaknesses[:4]

    # ── Career Path ───────────────────────────────────────────────────────────

    def suggest_career_path(
        self,
        skills: List[str],
        experience_years: float,
        education: Optional[List[str]] = None,
    ) -> str:
        sk = {s.lower() for s in skills}
        if any(s in sk for s in ("pytorch", "tensorflow", "bert", "llm", "transformer")):
            if experience_years >= 5:
                return "ML Tech Lead → Principal AI Scientist → VP of AI"
            return "ML Engineer → Senior ML Engineer → ML Research Lead"
        if any(s in sk for s in ("react", "next.js", "vue", "angular", "typescript")):
            return "Frontend Developer → Senior Frontend Engineer → Frontend Architect"
        if any(s in sk for s in ("kubernetes", "terraform", "ansible", "devops", "sre")):
            return "DevOps Engineer → Senior DevOps → Platform Engineer → Head of Infrastructure"
        if any(s in sk for s in ("fastapi", "django", "spring boot", "node.js", "go")):
            return "Software Engineer → Senior SWE → Staff Engineer → Engineering Manager"
        if any(s in sk for s in ("spark", "kafka", "airflow", "snowflake", "databricks")):
            return "Data Engineer → Senior Data Engineer → Data Platform Lead → Head of Data"
        # Hint from education
        if education:
            edu_lower = " ".join(education).lower()
            if any(w in edu_lower for w in ("data science", "statistics", "analytics")):
                return "Data Analyst → Senior Analyst → Data Science Lead → Chief Data Officer"
            if any(w in edu_lower for w in ("mba", "management")):
                return "Technical Lead → Engineering Manager → VP Engineering → CTO"
        return "Individual Contributor → Senior IC → Tech Lead → Engineering Director"

    # ── Interview Questions ───────────────────────────────────────────────────

    def _questions_by_category(
        self, skills: List[str], experience_years: float, role_title: str = ""
    ) -> Dict[str, List[str]]:
        sk_lower = [s.lower() for s in skills[:8]]
        technical: List[str] = []

        skill_questions = {
            "python": [
                "Explain Python's GIL and how it affects multi-threading.",
                "What are generators, decorators, and context managers? Give examples.",
            ],
            "react": [
                "Explain React's reconciliation algorithm and when to use useMemo vs useCallback.",
                "How do you handle complex state management — Redux vs Zustand vs Context?",
            ],
            "next.js": [
                "Explain SSR vs SSG vs ISR in Next.js and when to choose each.",
                "How do you optimize Core Web Vitals in a Next.js app?",
            ],
            "aws": [
                "Design a highly available microservices architecture on AWS.",
                "How do you implement zero-downtime blue/green deployments?",
            ],
            "machine learning": [
                "Explain bias-variance tradeoff and how to diagnose each.",
                "How do you detect and handle data drift in production ML models?",
            ],
            "pytorch": [
                "Walk through implementing a custom PyTorch training loop with mixed precision.",
                "How do you debug gradient issues in deep neural networks?",
            ],
            "kubernetes": [
                "Explain Kubernetes pod scheduling — resource requests, limits, affinity.",
                "How do you implement horizontal pod autoscaling and cluster autoscaling?",
            ],
            "sql": [
                "Explain query optimization — indexes, query plans, and common anti-patterns.",
                "How do you design a schema for a multi-tenant SaaS application?",
            ],
            "docker": [
                "Explain Docker layer caching and best practices for minimal image size.",
                "How do you implement secrets management in containerized applications?",
            ],
            "system design": [
                "Design a distributed rate limiter for a public API.",
                "Walk me through designing a scalable notification system.",
            ],
        }

        for skill in sk_lower:
            for key, qs in skill_questions.items():
                if key in skill and len(technical) < 5:
                    technical.extend(qs)

        if not technical:
            technical = [
                "Walk me through the most complex technical system you've designed.",
                "How do you approach debugging a production issue at 3am?",
                "Describe your approach to code review — what do you look for?",
            ]

        return {
            "technical": technical[:5],
            "behavioral": [
                "Tell me about a time you disagreed with a technical decision. What did you do?",
                "Describe a project that failed. What did you learn?",
                "How do you prioritize when you have multiple urgent tasks?",
                "Tell me about the most challenging team dynamic you've navigated.",
                "What's your process for ramping up on an unfamiliar codebase?",
            ],
            "system_design": [
                "Design a URL shortener that handles 100M requests/day.",
                "Design a real-time collaborative document editor (like Google Docs).",
                "Design the data pipeline for an ML feature store at scale.",
            ],
        }

    def generate_interview_questions(
        self,
        skills: List[str],
        experience_years: float,
        role_title: str = "",
    ) -> List[str]:
        """Returns a flat list of interview questions (technical first, then behavioral, then system design)."""
        by_cat = self._questions_by_category(skills, experience_years, role_title)
        flat: List[str] = []
        flat.extend(by_cat.get("technical", []))
        flat.extend(by_cat.get("behavioral", []))
        flat.extend(by_cat.get("system_design", []))
        return flat

    # ── AI Summary ────────────────────────────────────────────────────────────

    def _generate_summary(self, resume_data: Dict[str, Any]) -> str:
        name = resume_data.get("candidate_name") or "The candidate"
        skills = (resume_data.get("skills") or [])[:5]
        exp = resume_data.get("experience_years", 0)
        projects = len(resume_data.get("projects") or [])
        certs = len(resume_data.get("certifications") or [])
        completeness = resume_data.get("completeness_score", 0)
        top_skills = ", ".join(skills) if skills else "various technologies"

        return (
            f"{name} is a professional with {exp:.0f}+ years of experience, "
            f"specializing in {top_skills}. "
            f"Their resume shows {completeness:.0f}% completeness with {projects} documented "
            f"projects and {certs} certification(s). "
            f"Based on their profile, they appear to be a {self.suggest_career_path(skills, exp).split('→')[0].strip()}."
        )

    # ── Full Intelligence Report ──────────────────────────────────────────────

    def generate_full_intelligence(
        self,
        resume_data: Dict[str, Any],
        job_skills: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        text = resume_data.get("raw_text") or ""
        skills = resume_data.get("skills") or []
        exp = resume_data.get("experience_years", 0.0)
        completeness = resume_data.get("completeness_score", 0.0)
        projects = resume_data.get("projects") or []
        certifications = resume_data.get("certifications") or []

        return {
            "technical_score": self.compute_technical_score(skills, exp, projects, certifications),
            "leadership_score": self.compute_leadership_score(text, exp),
            "communication_score": self.compute_communication_score(text),
            "job_readiness": self.compute_job_readiness(completeness, exp, len(skills)),
            "culture_fit": self.compute_culture_fit(text),
            "confidence_score": self.compute_confidence_score(completeness),
            "strengths": self.identify_strengths(resume_data, job_skills),
            "weaknesses": self.identify_weaknesses(resume_data, job_skills),
            "career_path": self.suggest_career_path(skills, exp),
            "interview_questions": self.generate_interview_questions(skills, exp),
            "ai_summary": self._generate_summary(resume_data),
            "predicted_salary_min": max(40000, int(exp * 8000 + len(skills) * 500)),
            "predicted_salary_max": max(60000, int(exp * 12000 + len(skills) * 800)),
        }


intelligence_engine = CandidateIntelligenceEngine()

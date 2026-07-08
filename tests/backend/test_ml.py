"""
Unit tests for the ML pipeline — ranking engine, embeddings, AI intelligence.
These are pure-Python tests with no HTTP/DB dependencies.
"""
import numpy as np
import pytest

from backend.ml.ai_intelligence import CandidateIntelligenceEngine
from backend.ml.ranking_engine import AdvancedRankingEngine


# ── Ranking Engine ─────────────────────────────────────────────────────────────

class TestRankingEngine:
    def setup_method(self):
        self.engine = AdvancedRankingEngine()

    def test_skill_score_all_matched(self):
        score = self.engine.compute_skill_score(
            candidate_skills=["python", "fastapi", "docker"],
            required_skills=["python", "fastapi", "docker"],
            preferred_skills=[],
        )
        assert score == pytest.approx(1.0, rel=0.01)

    def test_skill_score_none_matched(self):
        score = self.engine.compute_skill_score(
            candidate_skills=["java", "spring"],
            required_skills=["python", "fastapi"],
            preferred_skills=[],
        )
        assert score == pytest.approx(0.0, rel=0.01)

    def test_skill_score_partial(self):
        score = self.engine.compute_skill_score(
            candidate_skills=["python", "django"],
            required_skills=["python", "fastapi", "postgresql"],
            preferred_skills=["docker"],
        )
        assert 0.0 < score < 1.0

    def test_skill_score_no_required(self):
        # When there are no required skills every candidate scores 1.0
        score = self.engine.compute_skill_score(
            candidate_skills=["python"],
            required_skills=[],
            preferred_skills=["docker"],
        )
        assert score == 1.0

    def test_experience_score_exact(self):
        score = self.engine.compute_experience_score(
            candidate_years=5.0,
            requirement_text="5 years of experience",
        )
        assert score >= 0.9

    def test_experience_score_exceeds(self):
        score = self.engine.compute_experience_score(
            candidate_years=8.0,
            requirement_text="3 years",
        )
        assert score >= 0.9

    def test_experience_score_insufficient(self):
        score = self.engine.compute_experience_score(
            candidate_years=1.0,
            requirement_text="5+ years",
        )
        assert score < 0.5

    def test_experience_score_no_requirement(self):
        # No stated requirement: credit up to 10 years linearly
        score = self.engine.compute_experience_score(candidate_years=10.0)
        assert score == pytest.approx(1.0, abs=0.01)
        score_zero = self.engine.compute_experience_score(candidate_years=0.0)
        assert score_zero == 0.0

    def test_rank_candidates_ordering(self):
        job_emb = np.random.randn(384).astype("float32")
        job_emb /= np.linalg.norm(job_emb)

        good_emb = job_emb + np.random.randn(384).astype("float32") * 0.1
        good_emb /= np.linalg.norm(good_emb)

        bad_emb = np.random.randn(384).astype("float32")
        bad_emb /= np.linalg.norm(bad_emb)

        results = self.engine.rank_candidates(
            job_embedding=job_emb,
            resume_embeddings=[("good_id", good_emb), ("bad_id", bad_emb)],
            job_skills_required=["python", "fastapi"],
            job_skills_preferred=[],
            resume_data={
                "good_id": {
                    "skills": ["python", "fastapi", "docker"],
                    "experience_years": 5.0,
                    "experience_requirement": "3 years",
                    "cleaned_text": "python fastapi microservices backend engineer",
                    "raw_text": "python fastapi microservices backend engineer",
                    "completeness_score": 85.0,
                },
                "bad_id": {
                    "skills": ["java"],
                    "experience_years": 0.5,
                    "experience_requirement": "3 years",
                    "cleaned_text": "java spring boot",
                    "raw_text": "java spring boot",
                    "completeness_score": 40.0,
                },
            },
            job_text="python fastapi postgresql docker backend",
        )
        assert len(results) == 2
        assert results[0].rank == 1
        assert results[1].rank == 2
        assert results[0].similarity_score >= results[1].similarity_score

    def test_rank_candidates_exposes_component_scores(self):
        job_emb = np.random.randn(384).astype("float32")
        job_emb /= np.linalg.norm(job_emb)
        results = self.engine.rank_candidates(
            job_embedding=job_emb,
            resume_embeddings=[("r1", job_emb.copy())],
            job_skills_required=["python"],
            job_skills_preferred=[],
            resume_data={"r1": {
                "skills": ["python"],
                "experience_years": 3.0,
                "experience_requirement": "2 years",
                "cleaned_text": "python developer",
                "raw_text": "python developer",
                "completeness_score": 70.0,
            }},
            job_text="python developer backend",
        )
        r = results[0]
        # All component scores must be 0–1 and composite must be 0–100
        assert 0.0 <= r.semantic_score <= 1.0, f"semantic_score out of range: {r.semantic_score}"
        assert 0.0 <= r.skill_score <= 1.0, f"skill_score out of range: {r.skill_score}"
        assert 0.0 <= r.experience_score <= 1.0, f"experience_score out of range: {r.experience_score}"
        assert 0.0 <= r.similarity_score <= 100.0, f"similarity_score out of range: {r.similarity_score}"
        assert 0.0 <= r.hiring_probability <= 1.0

    def test_rank_candidates_no_nan(self):
        """Component scores must never be NaN."""
        results = self.engine.rank_candidates(
            job_embedding=None,
            resume_embeddings=[("r1", None)],
            job_skills_required=[],
            job_skills_preferred=[],
            resume_data={"r1": {
                "skills": [],
                "experience_years": 0.0,
                "experience_requirement": "",
                "cleaned_text": "",
                "raw_text": "",
                "completeness_score": 0.0,
            }},
            job_text="",
        )
        r = results[0]
        for attr in ("similarity_score", "semantic_score", "skill_score", "experience_score"):
            v = getattr(r, attr)
            assert v == v, f"{attr} is NaN"          # NaN != NaN
            assert v != float("inf"), f"{attr} is inf"

    def test_shap_contributions_sum(self):
        shap = self.engine.compute_shap_contributions(
            semantic_score=0.8,
            skill_score=0.6,
            experience_score=0.7,
            skill_details={"python": 0.9, "docker": 0.5},
        )
        assert "semantic_match" in shap
        assert "skill_match" in shap
        assert "experience" in shap
        total = shap["semantic_match"] + shap["skill_match"] + shap["experience"]
        assert total == pytest.approx(100.0, abs=0.5)

    def test_shap_zero_scores(self):
        shap = self.engine.compute_shap_contributions(0.0, 0.0, 0.0)
        # Falls back to default weights
        assert shap["semantic_match"] == pytest.approx(50.0)
        assert shap["skill_match"] == pytest.approx(30.0)
        assert shap["experience"] == pytest.approx(20.0)

    def test_get_recommendation_excellent(self):
        # similarity_score is 0–100
        rec = self.engine.get_recommendation(92.0)
        assert "excellent" in rec.lower() or "strong" in rec.lower()

    def test_get_recommendation_weak(self):
        rec = self.engine.get_recommendation(20.0)
        assert "not recommended" in rec.lower()

    def test_get_recommendation_thresholds(self):
        assert "Excellent" in self.engine.get_recommendation(90.0)
        assert "Strong" in self.engine.get_recommendation(75.0)
        assert "Suitable" in self.engine.get_recommendation(60.0)
        assert "Average" in self.engine.get_recommendation(40.0)
        assert "Not Recommended" in self.engine.get_recommendation(10.0)

    def test_rank_candidates_no_embeddings(self):
        """Falls back to TF-IDF when embeddings are None."""
        results = self.engine.rank_candidates(
            job_embedding=None,
            resume_embeddings=[("r1", None), ("r2", None)],
            job_skills_required=["python"],
            job_skills_preferred=[],
            resume_data={
                "r1": {
                    "skills": ["python", "fastapi"],
                    "experience_years": 3.0,
                    "experience_requirement": "2 years",
                    "cleaned_text": "python fastapi backend",
                    "raw_text": "python fastapi backend",
                    "completeness_score": 75.0,
                },
                "r2": {
                    "skills": ["javascript"],
                    "experience_years": 1.0,
                    "experience_requirement": "2 years",
                    "cleaned_text": "javascript frontend",
                    "raw_text": "javascript frontend",
                    "completeness_score": 50.0,
                },
            },
            job_text="python fastapi backend developer",
        )
        assert len(results) == 2
        assert all(r.similarity_score >= 0 for r in results)


# ── AI Intelligence ────────────────────────────────────────────────────────────

class TestCandidateIntelligenceEngine:
    def setup_method(self):
        self.engine = CandidateIntelligenceEngine()

    def _make_parsed(self, **overrides):
        base = {
            "raw_text": "Experienced Python developer with 5 years of experience. Led a team of 4 engineers.",
            "skills": ["python", "fastapi", "docker", "kubernetes"],
            "experience_years": 5.0,
            "experience": "5 years at Acme Corp as backend engineer",
            "education": ["B.Tech Computer Science, IIT Delhi 2018"],
            "completeness_score": 80.0,
            "certifications": ["AWS Certified Solutions Architect"],
            "projects": ["Built microservices platform handling 1M requests/day"],
        }
        base.update(overrides)
        return base

    # ── compute_technical_score ──────────────────────────────────────────────

    def test_technical_score_range(self):
        score = self.engine.compute_technical_score(
            skills=["python", "docker", "kubernetes", "postgresql", "fastapi"],
            experience_years=5.0,
            projects=["microservices platform"],
            certifications=["AWS"],
        )
        assert 0.0 <= score <= 100.0

    def test_technical_score_empty(self):
        score = self.engine.compute_technical_score(skills=[])
        assert 0.0 <= score <= 100.0

    def test_technical_score_more_skills_higher(self):
        low = self.engine.compute_technical_score(skills=["python"])
        high = self.engine.compute_technical_score(
            skills=["python", "fastapi", "docker", "k8s", "sql", "redis",
                    "aws", "terraform", "go", "rust"],
            experience_years=8.0,
            certifications=["AWS", "GCP"],
        )
        assert high > low

    # ── compute_leadership_score ─────────────────────────────────────────────

    def test_leadership_score_keywords(self):
        score = self.engine.compute_leadership_score(
            "Led a team of 10 engineers, managed delivery, mentored juniors. Owned the product roadmap."
        )
        assert score > 40.0

    def test_leadership_score_with_experience(self):
        score = self.engine.compute_leadership_score(
            "Led a team of 10 engineers, managed delivery, mentored juniors. Owned the product roadmap.",
            experience_years=8.0,
        )
        assert score > 50.0

    def test_leadership_score_low(self):
        score = self.engine.compute_leadership_score("junior developer, learning python")
        assert score < 70.0

    def test_leadership_score_range(self):
        score = self.engine.compute_leadership_score("some text", experience_years=3.0)
        assert 0.0 <= score <= 100.0

    # ── compute_communication_score ──────────────────────────────────────────

    def test_communication_score(self):
        score = self.engine.compute_communication_score(
            "Presented quarterly reviews to C-suite. Wrote technical documentation and team updates.",
            skills=["communication", "presentation"],
        )
        assert 0.0 <= score <= 100.0

    def test_communication_score_no_skills(self):
        score = self.engine.compute_communication_score(
            "Communicated effectively with stakeholders."
        )
        assert 0.0 <= score <= 100.0

    # ── compute_job_readiness ────────────────────────────────────────────────

    def test_job_readiness_high_keyword(self):
        score = self.engine.compute_job_readiness(
            skills=["python", "fastapi", "docker"],
            experience_years=5.0,
            completeness_score=90.0,
            certifications=["AWS"],
        )
        assert score > 60.0

    def test_job_readiness_low_keyword(self):
        score = self.engine.compute_job_readiness(
            skills=[],
            experience_years=0.0,
            completeness_score=20.0,
            certifications=[],
        )
        assert score < 50.0

    def test_job_readiness_positional(self):
        # Positional call: compute_job_readiness(completeness, exp, skills_count)
        score = self.engine.compute_job_readiness(80.0, 4.0, 8)
        assert 0.0 <= score <= 100.0

    # ── identify_strengths / weaknesses ─────────────────────────────────────

    def test_strengths_not_empty(self):
        strengths = self.engine.identify_strengths(self._make_parsed())
        assert len(strengths) > 0

    def test_weaknesses_freshgrad(self):
        weaknesses = self.engine.identify_weaknesses(
            self._make_parsed(
                skills=[],
                experience_years=0.0,
                education=[],
                certifications=[],
                completeness_score=20.0,
            )
        )
        assert len(weaknesses) > 0

    # ── suggest_career_path ──────────────────────────────────────────────────

    def test_career_path_suggestion(self):
        path = self.engine.suggest_career_path(
            skills=["python", "machine learning", "tensorflow", "nlp"],
            experience_years=3.0,
            education=["M.Sc Data Science"],
        )
        assert path is not None
        assert len(path) > 10

    def test_career_path_no_education(self):
        path = self.engine.suggest_career_path(
            skills=["react", "typescript"],
            experience_years=2.0,
        )
        assert "Frontend" in path

    def test_career_path_devops(self):
        path = self.engine.suggest_career_path(
            skills=["kubernetes", "terraform", "devops"],
            experience_years=4.0,
        )
        assert "DevOps" in path or "Infrastructure" in path

    # ── generate_interview_questions ─────────────────────────────────────────

    def test_generate_interview_questions(self):
        questions = self.engine.generate_interview_questions(
            skills=["python", "system design", "docker"],
            experience_years=4.0,
        )
        assert len(questions) >= 3
        assert all(isinstance(q, str) for q in questions)

    def test_interview_questions_fallback(self):
        # Unknown skills → generic fallback questions
        questions = self.engine.generate_interview_questions(
            skills=["cobol", "fortran"],
            experience_years=1.0,
        )
        assert len(questions) >= 3
        assert all(isinstance(q, str) for q in questions)

    # ── generate_full_intelligence ───────────────────────────────────────────

    def test_generate_full_intelligence(self):
        result = self.engine.generate_full_intelligence(self._make_parsed())
        required_keys = [
            "technical_score", "leadership_score", "communication_score",
            "job_readiness", "culture_fit", "strengths", "weaknesses",
            "career_path", "ai_summary",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"
        assert 0.0 <= result["technical_score"] <= 100.0
        assert isinstance(result["strengths"], list)
        assert isinstance(result["weaknesses"], list)
        assert isinstance(result["interview_questions"], list)
        assert all(isinstance(q, str) for q in result["interview_questions"])

"""
RankingEngine: Orchestrates the complete resume ranking pipeline.

Pipeline
--------
1. Receive job description dict + list of resume dicts (from DB)
2. Re-fit similarity engine on the combined corpus
3. Compute cosine similarity scores per resume
4. Compute skill matching (matched / missing / extra)
5. Assign recommendations based on score thresholds
6. Sort descending by score, assign rank numbers
7. Return List[RankingEntry]

Design note: RankingEngine is stateless between calls — the similarity
engine re-fits on every call to handle growing resume pools correctly.
For large corpora (1000+), cache the vectorizer externally.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.utils.similarity import SimilarityEngine, TFIDFEngine, get_similarity_engine
from backend.utils.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)


# ── Recommendation labels ────────────────────────────────────────────────────

def _get_recommendation(score: float) -> str:
    if score >= settings.EXCELLENT_THRESHOLD:
        return "Excellent Candidate"
    elif score >= settings.STRONG_THRESHOLD:
        return "Strong Match"
    elif score >= settings.SUITABLE_THRESHOLD:
        return "Suitable"
    elif score >= settings.AVERAGE_THRESHOLD:
        return "Average Match"
    else:
        return "Not Recommended"


def _get_recommendation_colour(recommendation: str) -> str:
    return {
        "Excellent Candidate": "#2ecc71",
        "Strong Match": "#27ae60",
        "Suitable": "#f39c12",
        "Average Match": "#e67e22",
        "Not Recommended": "#e74c3c",
    }.get(recommendation, "#95a5a6")


# ── Data class returned by the engine ────────────────────────────────────────

@dataclass
class RankingEntry:
    rank: int
    resume_id: int
    candidate_name: str
    filename: str
    similarity_score: float          # 0–100
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    extra_skills: List[str] = field(default_factory=list)
    recommendation: str = ""
    quality_score: float = 0.0       # completeness score from parser
    keyword_density: float = 0.0
    experience_years: float = 0.0
    colour: str = "#95a5a6"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "resume_id": self.resume_id,
            "candidate_name": self.candidate_name,
            "filename": self.filename,
            "similarity_score": self.similarity_score,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "extra_skills": self.extra_skills,
            "recommendation": self.recommendation,
            "quality_score": self.quality_score,
            "keyword_density": self.keyword_density,
            "experience_years": self.experience_years,
        }


# ── Main engine ───────────────────────────────────────────────────────────────

class RankingEngine:
    """
    Stateless ranking engine. Accepts any SimilarityEngine implementation,
    making it easy to swap TF-IDF for SBERT without touching this class.
    """

    def __init__(self, similarity_engine: Optional[SimilarityEngine] = None) -> None:
        self.engine: SimilarityEngine = similarity_engine or get_similarity_engine()
        self.cleaner = TextCleaner()

    def rank(
        self,
        job_description: Dict[str, Any],
        resumes: List[Dict[str, Any]],
    ) -> List[RankingEntry]:
        """
        Rank resumes against the job description.

        Parameters
        ----------
        job_description : dict with at minimum "cleaned_text" and "required_skills"
        resumes         : list of dicts — each must have "id", "cleaned_text", "skills"

        Returns
        -------
        Sorted list of RankingEntry (highest score first)
        """
        if not resumes:
            logger.warning("RankingEngine.rank called with empty resume list.")
            return []

        jd_text = job_description.get("cleaned_text") or ""
        jd_skills: set[str] = {s.lower() for s in job_description.get("required_skills", [])}

        # Add preferred skills to JD skill set with lower implicit weight
        for s in job_description.get("preferred_skills", []):
            jd_skills.add(s.lower())

        resume_texts = [r.get("cleaned_text") or "" for r in resumes]

        # Re-fit on this corpus so vocabulary covers all documents
        all_texts = [jd_text] + resume_texts
        self.engine.fit(all_texts)

        scores = self.engine.compute_similarity(jd_text, resume_texts)

        entries: List[RankingEntry] = []
        for resume, raw_score in zip(resumes, scores):
            score_pct = round(raw_score * 100, 2)
            resume_skills: set[str] = {s.lower() for s in resume.get("skills", [])}

            matched = sorted(jd_skills & resume_skills)
            missing = sorted(jd_skills - resume_skills)
            extra = sorted(resume_skills - jd_skills)
            recommendation = _get_recommendation(score_pct)

            entry = RankingEntry(
                rank=0,  # set after sorting
                resume_id=resume.get("id", -1),
                candidate_name=resume.get("candidate_name") or "Unknown",
                filename=resume.get("filename", ""),
                similarity_score=score_pct,
                matched_skills=matched,
                missing_skills=missing,
                extra_skills=extra,
                recommendation=recommendation,
                quality_score=resume.get("completeness_score", 0.0),
                keyword_density=self._keyword_density(
                    resume.get("raw_text", ""), jd_skills
                ),
                experience_years=resume.get("experience_years", 0.0),
                colour=_get_recommendation_colour(recommendation),
            )
            entries.append(entry)

        # Sort descending
        entries.sort(key=lambda e: e.similarity_score, reverse=True)

        # Assign ranks (ties share rank)
        for i, entry in enumerate(entries):
            entry.rank = i + 1

        logger.info(
            "Ranked %d resumes for job '%s'. Top score: %.2f",
            len(entries),
            job_description.get("title", "—"),
            entries[0].similarity_score if entries else 0,
        )
        return entries

    def _keyword_density(self, text: str, keywords: set[str]) -> float:
        """Fraction of text words that are JD keywords, as a percentage."""
        if not text or not keywords:
            return 0.0
        words = text.lower().split()
        if not words:
            return 0.0
        hits = sum(1 for w in words if w in keywords)
        return round(hits / len(words) * 100, 3)

    def compute_metrics(
        self, ranked_entries: List[RankingEntry], labels: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Compute evaluation metrics when ground-truth labels are available.

        labels : list of 1 (relevant) / 0 (irrelevant) for each entry in rank order.
        If None, returns only descriptive statistics.
        """
        if not ranked_entries:
            return {}

        scores = [e.similarity_score for e in ranked_entries]
        metrics: Dict[str, Any] = {
            "total": len(ranked_entries),
            "mean_score": round(sum(scores) / len(scores), 2),
            "max_score": round(max(scores), 2),
            "min_score": round(min(scores), 2),
            "recommendation_distribution": self._recommendation_distribution(ranked_entries),
        }

        if labels and len(labels) == len(ranked_entries):
            metrics.update(self._classification_metrics(ranked_entries, labels))

        return metrics

    def _recommendation_distribution(
        self, entries: List[RankingEntry]
    ) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for entry in entries:
            dist[entry.recommendation] = dist.get(entry.recommendation, 0) + 1
        return dist

    def _classification_metrics(
        self, entries: List[RankingEntry], labels: List[int]
    ) -> Dict[str, Any]:
        """Binary classification metrics treating score ≥ SUITABLE_THRESHOLD as positive."""
        try:
            from sklearn.metrics import (
                accuracy_score,
                classification_report,
                confusion_matrix,
                f1_score,
                precision_score,
                recall_score,
                roc_auc_score,
            )
            import numpy as np

            threshold = settings.SUITABLE_THRESHOLD
            predicted = [1 if e.similarity_score >= threshold else 0 for e in entries]
            scores_norm = [e.similarity_score / 100 for e in entries]

            cm = confusion_matrix(labels, predicted).tolist()
            report = classification_report(labels, predicted, output_dict=True, zero_division=0)

            result: Dict[str, Any] = {
                "accuracy": round(accuracy_score(labels, predicted), 4),
                "precision": round(precision_score(labels, predicted, zero_division=0), 4),
                "recall": round(recall_score(labels, predicted, zero_division=0), 4),
                "f1_score": round(f1_score(labels, predicted, zero_division=0), 4),
                "confusion_matrix": cm,
                "classification_report": report,
            }

            # ROC-AUC only if both classes present
            if len(set(labels)) == 2:
                result["roc_auc"] = round(roc_auc_score(labels, scores_norm), 4)

            return result
        except Exception as exc:
            logger.warning("Could not compute classification metrics: %s", exc)
            return {}

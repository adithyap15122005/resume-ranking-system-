"""
Advanced hybrid ranking engine — SBERT (50%) + Skill overlap (30%) + Experience (20%).
All individual component scores are on 0.0–1.0 scale.
composite_score (0.0–1.0) is stored as similarity_score * 100 in the DB (percentage).
"""
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RankingResult:
    resume_id: str
    rank: int
    # Stored as 0–100 in DB (percentage display)
    similarity_score: float
    # Component scores 0–1
    semantic_score: float = 0.0
    skill_score: float = 0.0
    experience_score: float = 0.0
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    extra_skills: List[str] = field(default_factory=list)
    recommendation: str = ""
    shap_values: Dict[str, Any] = field(default_factory=dict)
    skill_contributions: Dict[str, float] = field(default_factory=dict)
    experience_contribution: float = 0.0
    education_contribution: float = 0.0
    technical_score: float = 0.0
    hiring_probability: float = 0.0   # 0–1
    keyword_density: float = 0.0
    experience_years: float = 0.0
    quality_score: float = 0.0


def _safe_float(val, default: float = 0.0) -> float:
    """Return a guaranteed finite float, replacing None/NaN/Inf with default."""
    try:
        v = float(val) if val is not None else default
        return v if (v == v and v != float("inf") and v != float("-inf")) else default
    except (TypeError, ValueError):
        return default


class AdvancedRankingEngine:
    """
    Hybrid ranking engine combining:
    - SBERT semantic similarity  → 50 %
    - Skill overlap score        → 30 %
    - Experience match           → 20 %
    with SHAP-style contribution explanations.
    """

    EMBEDDING_WEIGHT = 0.50
    SKILL_WEIGHT = 0.30
    EXPERIENCE_WEIGHT = 0.20

    # Thresholds for the 0–100 composite score
    THRESHOLDS = {
        "excellent": 85.0,
        "strong":    70.0,
        "suitable":  55.0,
        "average":   35.0,
    }

    def __init__(self):
        self.hiring_model: Optional[Any] = None
        self.scaler: Optional[Any] = None
        self.feature_names: List[str] = []
        self._tfidf_vectorizer: Optional[Any] = None

    # ── Skill Scoring (0.0–1.0) ───────────────────────────────────────────────

    def compute_skill_score(
        self,
        candidate_skills: List[str],
        required_skills: List[str],
        preferred_skills: Optional[List[str]] = None,
    ) -> float:
        """
        Returns a float in [0.0, 1.0].
        70 % of weight from required-skill coverage, 30 % from preferred.
        """
        preferred_skills = preferred_skills or []
        resume_set = {s.lower().strip() for s in candidate_skills if s}
        required_set = {s.lower().strip() for s in required_skills if s}
        preferred_set = {s.lower().strip() for s in preferred_skills if s}

        if not required_set:
            return 1.0

        req_coverage = len(resume_set & required_set) / len(required_set)
        if preferred_set:
            pref_coverage = len(resume_set & preferred_set) / len(preferred_set)
            score = req_coverage * 0.70 + pref_coverage * 0.30
        else:
            # No preferred skills → full weight on required coverage
            score = req_coverage

        return round(min(max(_safe_float(score), 0.0), 1.0), 4)

    def _skill_details(
        self,
        candidate_skills: List[str],
        required_skills: List[str],
        preferred_skills: Optional[List[str]] = None,
    ) -> Tuple[float, List[str], List[str], List[str]]:
        """
        Returns (score_0_1, matched_skills, missing_skills, extra_skills).
        """
        preferred_skills = preferred_skills or []
        resume_set = {s.lower().strip() for s in candidate_skills if s}
        required_set = {s.lower().strip() for s in required_skills if s}
        preferred_set = {s.lower().strip() for s in preferred_skills if s}

        matched = sorted((resume_set & required_set) | (resume_set & preferred_set))
        missing = sorted(required_set - resume_set)
        extra = sorted((resume_set - required_set - preferred_set))[:8]

        score = self.compute_skill_score(candidate_skills, required_skills, preferred_skills)
        return score, matched, missing, extra

    # ── Experience Scoring (0.0–1.0) ─────────────────────────────────────────

    def compute_experience_score(
        self,
        candidate_years: float,
        requirement_text: str = "",
    ) -> float:
        """Returns a float in [0.0, 1.0]."""
        candidate_years = _safe_float(candidate_years)
        numbers = re.findall(r"\d+(?:\.\d+)?", requirement_text or "")
        if not numbers:
            # No stated requirement → credit experience up to 10 years
            return round(min(candidate_years / 10.0, 1.0), 4)

        req_min = float(numbers[0])
        req_max = float(numbers[-1]) if len(numbers) > 1 else req_min + 2

        if candidate_years >= req_min:
            overshoot = max(0.0, candidate_years - req_max - 3)
            score = 1.0 - overshoot * 0.05
        else:
            gap = req_min - candidate_years
            score = max(0.0, 1.0 - gap * 0.20)

        return round(min(max(_safe_float(score), 0.0), 1.0), 4)

    # ── Recommendation Label ──────────────────────────────────────────────────

    def get_recommendation(self, composite_100: float) -> str:
        """Takes composite score on 0–100 scale."""
        if composite_100 >= self.THRESHOLDS["excellent"]:
            return "Excellent Candidate"
        if composite_100 >= self.THRESHOLDS["strong"]:
            return "Strong Match"
        if composite_100 >= self.THRESHOLDS["suitable"]:
            return "Suitable"
        if composite_100 >= self.THRESHOLDS["average"]:
            return "Average Match"
        return "Not Recommended"

    # ── SHAP Contributions ────────────────────────────────────────────────────

    def compute_shap_contributions(
        self,
        semantic_score: float,
        skill_score: float,
        experience_score: float,
        skill_details: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Returns a dict with percentage contributions summing to 100.
        All inputs are 0–1 component scores.
        """
        sem_c = _safe_float(semantic_score) * self.EMBEDDING_WEIGHT
        sk_c = _safe_float(skill_score) * self.SKILL_WEIGHT
        ex_c = _safe_float(experience_score) * self.EXPERIENCE_WEIGHT
        total = sem_c + sk_c + ex_c

        if total <= 0.0:
            return {
                "semantic_match": 50.0,
                "skill_match": 30.0,
                "experience": 20.0,
                "skills": {},
            }

        return {
            "semantic_match": round(sem_c / total * 100, 1),
            "skill_match": round(sk_c / total * 100, 1),
            "experience": round(ex_c / total * 100, 1),
            "skills": skill_details or {},
        }

    # ── Keyword Density ───────────────────────────────────────────────────────

    def _keyword_density(self, resume_text: str, job_text: str) -> float:
        if not resume_text or not job_text:
            return 0.0
        job_words = set(job_text.lower().split())
        res_words = resume_text.lower().split()
        if not res_words:
            return 0.0
        matched = sum(1 for w in res_words if w in job_words)
        return round(_safe_float(matched / len(res_words) * 100), 2)

    # ── TF-IDF Fallback ───────────────────────────────────────────────────────

    def _tfidf_score(self, job_text: str, resume_text: str) -> float:
        """Returns 0–1 cosine similarity via TF-IDF."""
        if not job_text or not resume_text:
            return 0.0
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            vec = TfidfVectorizer(max_features=8000, ngram_range=(1, 2), sublinear_tf=True)
            mat = vec.fit_transform([job_text, resume_text])
            score = float(cosine_similarity(mat[0:1], mat[1:2])[0][0])
            return round(min(max(_safe_float(score), 0.0), 1.0), 4)
        except Exception:
            return 0.5

    # ── Main Ranking Pipeline ─────────────────────────────────────────────────

    def rank_candidates(
        self,
        job_embedding: Optional[np.ndarray],
        resume_embeddings: List[Tuple[str, Optional[np.ndarray]]],
        job_skills_required: List[str],
        job_skills_preferred: List[str],
        resume_data: Dict[str, Dict],
        job_text: str = "",
    ) -> List["RankingResult"]:
        results: List[RankingResult] = []

        for resume_id, resume_emb in resume_embeddings:
            rdata = resume_data.get(resume_id) or {}

            # ── Semantic similarity (0–1) ─────────────────────────────────────
            if job_embedding is not None and resume_emb is not None:
                try:
                    raw_dot = float(np.dot(
                        job_embedding.astype(np.float64),
                        resume_emb.astype(np.float64)
                    ))
                    semantic_score = round(min(max(_safe_float(raw_dot), 0.0), 1.0), 4)
                except Exception:
                    semantic_score = 0.0
            else:
                resume_text = rdata.get("cleaned_text") or rdata.get("raw_text") or ""
                semantic_score = self._tfidf_score(job_text, resume_text)

            # ── Skill score (0–1) ─────────────────────────────────────────────
            cand_skills = rdata.get("skills") or []
            skill_score, matched, missing, extra = self._skill_details(
                cand_skills, job_skills_required, job_skills_preferred
            )

            # ── Experience score (0–1) ────────────────────────────────────────
            exp_years = _safe_float(rdata.get("experience_years"), 0.0)
            exp_req = rdata.get("experience_requirement") or ""
            experience_score = self.compute_experience_score(exp_years, exp_req)

            # ── Composite (0–1 → stored as 0–100) ────────────────────────────
            composite_01 = (
                semantic_score * self.EMBEDDING_WEIGHT
                + skill_score * self.SKILL_WEIGHT
                + experience_score * self.EXPERIENCE_WEIGHT
            )
            composite_01 = round(min(max(_safe_float(composite_01), 0.0), 1.0), 4)
            similarity_score_100 = round(composite_01 * 100, 2)

            # ── Keyword density ───────────────────────────────────────────────
            resume_text = rdata.get("cleaned_text") or rdata.get("raw_text") or ""
            kd = self._keyword_density(resume_text, job_text)

            # ── Skill contributions for SHAP ──────────────────────────────────
            skill_weight_per = round(skill_score / max(len(matched), 1), 3) if matched else 0.0
            skill_detail_map: Dict[str, float] = {}
            for s in matched[:6]:
                skill_detail_map[s] = skill_weight_per
            for s in missing[:4]:
                skill_detail_map[s] = -round(skill_weight_per / 2, 3)

            shap = self.compute_shap_contributions(
                semantic_score, skill_score, experience_score, skill_detail_map
            )

            results.append(
                RankingResult(
                    resume_id=resume_id,
                    rank=0,
                    similarity_score=similarity_score_100,
                    semantic_score=semantic_score,
                    skill_score=skill_score,
                    experience_score=experience_score,
                    matched_skills=matched,
                    missing_skills=missing,
                    extra_skills=extra,
                    recommendation=self.get_recommendation(similarity_score_100),
                    shap_values=shap,
                    skill_contributions={k: round(_safe_float(v), 3) for k, v in skill_detail_map.items()},
                    experience_contribution=experience_score,
                    education_contribution=0.0,
                    technical_score=semantic_score,
                    hiring_probability=composite_01,
                    keyword_density=kd,
                    experience_years=exp_years,
                    quality_score=_safe_float(rdata.get("completeness_score"), 0.0),
                )
            )

        results.sort(key=lambda r: r.similarity_score, reverse=True)
        for i, r in enumerate(results):
            r.rank = i + 1

        return results

    # ── Model Training / Persistence ──────────────────────────────────────────

    def train_hiring_model(
        self,
        features: np.ndarray,
        labels: np.ndarray,
        feature_names: List[str],
        model_type: str = "xgboost",
    ) -> Dict[str, Any]:
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score,
            f1_score, roc_auc_score, confusion_matrix,
        )
        from sklearn.preprocessing import StandardScaler

        self.feature_names = feature_names
        X_tr, X_te, y_tr, y_te = train_test_split(
            features, labels, test_size=0.2, random_state=42
        )
        self.scaler = StandardScaler()
        X_tr_s = self.scaler.fit_transform(X_tr)
        X_te_s = self.scaler.transform(X_te)

        model = self._build_model(model_type)
        start = time.time()
        use_scaled = model_type == "logistic"
        model.fit(X_tr_s if use_scaled else X_tr, y_tr)
        elapsed = time.time() - start

        X_eval = X_te_s if use_scaled else X_te
        y_pred = model.predict(X_eval)
        y_prob = model.predict_proba(X_eval)[:, 1]

        n_classes = len(np.unique(labels))
        avg = "binary" if n_classes == 2 else "weighted"

        metrics: Dict[str, Any] = {
            "model_type": model_type,
            "accuracy": round(float(accuracy_score(y_te, y_pred)), 4),
            "precision": round(float(precision_score(y_te, y_pred, average=avg, zero_division=0)), 4),
            "recall": round(float(recall_score(y_te, y_pred, average=avg, zero_division=0)), 4),
            "f1": round(float(f1_score(y_te, y_pred, average=avg, zero_division=0)), 4),
            "confusion_matrix": confusion_matrix(y_te, y_pred).tolist(),
            "training_time_s": round(elapsed, 2),
            "train_samples": int(len(X_tr)),
            "test_samples": int(len(X_te)),
        }
        if n_classes == 2:
            try:
                metrics["roc_auc"] = round(float(roc_auc_score(y_te, y_prob)), 4)
            except Exception:
                pass

        if hasattr(model, "feature_importances_"):
            imp = model.feature_importances_
            metrics["feature_importance"] = dict(
                sorted(zip(feature_names, imp.tolist()), key=lambda x: x[1], reverse=True)[:20]
            )

        self.hiring_model = model
        return metrics

    def _build_model(self, model_type: str):
        if model_type == "xgboost":
            import xgboost as xgb
            return xgb.XGBClassifier(
                n_estimators=200, max_depth=6, learning_rate=0.1,
                subsample=0.8, colsample_bytree=0.8, random_state=42,
                eval_metric="logloss", verbosity=0,
            )
        if model_type == "lightgbm":
            import lightgbm as lgb
            return lgb.LGBMClassifier(
                n_estimators=200, learning_rate=0.1, random_state=42, verbose=-1,
            )
        if model_type == "random_forest":
            from sklearn.ensemble import RandomForestClassifier
            return RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
        from sklearn.linear_model import LogisticRegression
        return LogisticRegression(max_iter=1000, random_state=42)

    def save(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        if self.hiring_model:
            joblib.dump(self.hiring_model, path / "hiring_model.joblib")
        if self.scaler:
            joblib.dump(self.scaler, path / "scaler.joblib")
        if self.feature_names:
            (path / "feature_names.json").write_text(json.dumps(self.feature_names))

    def load(self, path: Path):
        m = path / "hiring_model.joblib"
        s = path / "scaler.joblib"
        fn = path / "feature_names.json"
        if m.exists():
            self.hiring_model = joblib.load(m)
        if s.exists():
            self.scaler = joblib.load(s)
        if fn.exists():
            self.feature_names = json.loads(fn.read_text())


ranking_engine = AdvancedRankingEngine()

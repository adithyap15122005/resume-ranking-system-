"""
SimilarityEngine — abstract interface + concrete implementations.

Concrete engines
----------------
TFIDFEngine   : sklearn TF-IDF + cosine similarity (default, no GPU needed)
SBERTEngine   : sentence-transformers MiniLM (production upgrade, optional dep)

Swap engines via config.SIMILARITY_ENGINE or the factory function
get_similarity_engine().

Adding a new engine
-------------------
1. Subclass SimilarityEngine
2. Implement fit(), compute_similarity(), save(), load()
3. Register in _ENGINE_REGISTRY at the bottom of this file
"""
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.config import settings

logger = logging.getLogger(__name__)


class SimilarityEngine(ABC):
    """Abstract base — any engine must implement these four methods."""

    @abstractmethod
    def fit(self, texts: List[str]) -> None: ...

    @abstractmethod
    def compute_similarity(self, query: str, candidates: List[str]) -> List[float]:
        """Return cosine-like similarity score in [0, 1] for each candidate."""
        ...

    @abstractmethod
    def save(self, path: str) -> None: ...

    @abstractmethod
    def load(self, path: str) -> None: ...

    def to_percentage(self, score: float) -> float:
        return round(max(0.0, min(score, 1.0)) * 100, 2)


# ---------------------------------------------------------------------------
# TF-IDF Engine
# ---------------------------------------------------------------------------

class TFIDFEngine(SimilarityEngine):
    """
    TF-IDF vectorisation + cosine similarity.
    Fits on the combined corpus (job description + all resumes) to build
    a shared vocabulary before computing pairwise distances.
    """

    _DEFAULT_PATH: Path = settings.TRAINED_DIR / "tfidf_engine.joblib"

    def __init__(
        self,
        max_features: int = settings.MAX_FEATURES,
        ngram_range: Tuple[int, int] = settings.NGRAM_RANGE,
    ) -> None:
        self._vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            sublinear_tf=True,
            min_df=1,
            analyzer="word",
            token_pattern=r"(?u)\b\w\w+\b",
        )
        self._fitted = False

    # -- SimilarityEngine interface -----------------------------------------

    def fit(self, texts: List[str]) -> None:
        clean = [t for t in texts if t and t.strip()]
        if not clean:
            logger.warning("TFIDFEngine.fit called with empty corpus.")
            return
        self._vectorizer.fit(clean)
        self._fitted = True

    def compute_similarity(self, query: str, candidates: List[str]) -> List[float]:
        if not candidates:
            return []

        all_texts = [query] + candidates

        if not self._fitted:
            self.fit(all_texts)

        query_vec = self._vectorizer.transform([query])
        candidate_vecs = self._vectorizer.transform(candidates)
        scores: np.ndarray = cosine_similarity(query_vec, candidate_vecs)[0]
        return [float(s) for s in scores]

    def save(self, path: Optional[str] = None) -> None:
        target = Path(path) if path else self._DEFAULT_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._vectorizer, target)

    def load(self, path: Optional[str] = None) -> None:
        target = Path(path) if path else self._DEFAULT_PATH
        if not target.exists():
            raise FileNotFoundError(f"Model file not found: {target}")
        self._vectorizer = joblib.load(target)
        self._fitted = True

    def get_vocabulary_size(self) -> int:
        if not self._fitted:
            return 0
        return len(self._vectorizer.vocabulary_)


# ---------------------------------------------------------------------------
# SBERT Engine (optional — requires sentence-transformers)
# ---------------------------------------------------------------------------

class SBERTEngine(SimilarityEngine):
    """
    Sentence-BERT engine using all-MiniLM-L6-v2 (or any other ST model).

    Install:  pip install sentence-transformers
    This class is a first-class citizen — it follows the same interface
    as TFIDFEngine and can be selected via config.SIMILARITY_ENGINE = "sbert".
    """

    def __init__(self, model_name: str = settings.SBERT_MODEL) -> None:
        self._model_name = model_name
        self._model = None

    def _load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers"
            ) from exc
        if self._model is None:
            logger.info("Loading SBERT model: %s", self._model_name)
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)

    def fit(self, texts: List[str]) -> None:
        # SBERT doesn't require fitting — it uses pre-trained embeddings.
        self._load_model()

    def compute_similarity(self, query: str, candidates: List[str]) -> List[float]:
        self._load_model()
        from sentence_transformers import util as st_util

        query_emb = self._model.encode([query], convert_to_tensor=True, normalize_embeddings=True)
        cand_embs = self._model.encode(candidates, convert_to_tensor=True, normalize_embeddings=True)
        scores = st_util.cos_sim(query_emb, cand_embs)[0]
        return [float(s) for s in scores.cpu().tolist()]

    def save(self, path: Optional[str] = None) -> None:
        # SBERT models are managed by Hugging Face hub — nothing to persist locally.
        logger.info("SBERTEngine: model '%s' is loaded from HuggingFace hub.", self._model_name)

    def load(self, path: Optional[str] = None) -> None:
        self._load_model()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_ENGINE_REGISTRY: dict[str, type] = {
    "tfidf": TFIDFEngine,
    "sbert": SBERTEngine,
}


def get_similarity_engine(engine_type: Optional[str] = None) -> SimilarityEngine:
    """
    Return a SimilarityEngine instance.

    engine_type defaults to config.SIMILARITY_ENGINE ("tfidf").
    Pass "sbert" to use Sentence-BERT (requires sentence-transformers).
    """
    key = (engine_type or settings.SIMILARITY_ENGINE).lower()
    if key not in _ENGINE_REGISTRY:
        raise ValueError(
            f"Unknown similarity engine '{key}'. "
            f"Available: {list(_ENGINE_REGISTRY.keys())}"
        )
    return _ENGINE_REGISTRY[key]()

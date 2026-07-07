"""
FeatureExtractor: wraps TfidfVectorizer with persistence and lazy loading.
"""
import logging
from pathlib import Path
from typing import List, Optional, Tuple

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from backend.config import settings

logger = logging.getLogger(__name__)

_MODEL_PATH: Path = settings.TRAINED_DIR / "tfidf_vectorizer.joblib"


class FeatureExtractor:
    """Stateful TF-IDF feature extractor with save/load support."""

    def __init__(
        self,
        max_features: int = settings.MAX_FEATURES,
        ngram_range: Tuple[int, int] = settings.NGRAM_RANGE,
        min_df: int = settings.MIN_DF,
        sublinear_tf: bool = settings.SUBLINEAR_TF,
    ) -> None:
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            min_df=min_df,
            sublinear_tf=sublinear_tf,
            analyzer="word",
            token_pattern=r"(?u)\b\w\w+\b",
        )
        self._fitted = False

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def fit(self, texts: List[str]) -> "FeatureExtractor":
        self.vectorizer.fit([t for t in texts if t.strip()])
        self._fitted = True
        self.save()
        return self

    def transform(self, texts: List[str]) -> np.ndarray:
        if not self._fitted:
            self._try_load()
        return self.vectorizer.transform(texts)

    def fit_transform(self, texts: List[str]) -> np.ndarray:
        result = self.vectorizer.fit_transform([t for t in texts if t.strip()])
        self._fitted = True
        self.save()
        return result

    def get_feature_names(self) -> List[str]:
        if not self._fitted:
            self._try_load()
        return self.vectorizer.get_feature_names_out().tolist()

    def get_top_terms(self, text: str, n: int = 20) -> List[Tuple[str, float]]:
        """Return the n highest TF-IDF terms for a given document."""
        if not self._fitted:
            self._try_load()
        vec = self.vectorizer.transform([text])
        feature_names = self.get_feature_names()
        scores = vec.toarray()[0]
        top_idx = scores.argsort()[::-1][:n]
        return [(feature_names[i], float(scores[i])) for i in top_idx if scores[i] > 0]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Optional[Path] = None) -> None:
        target = path or _MODEL_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.vectorizer, target)
        logger.debug("TF-IDF vectorizer saved to %s", target)

    def load(self, path: Optional[Path] = None) -> None:
        target = path or _MODEL_PATH
        self.vectorizer = joblib.load(target)
        self._fitted = True
        logger.debug("TF-IDF vectorizer loaded from %s", target)

    def _try_load(self) -> None:
        if _MODEL_PATH.exists():
            self.load()
        else:
            logger.warning("No saved vectorizer found; vectorizer is unfitted.")

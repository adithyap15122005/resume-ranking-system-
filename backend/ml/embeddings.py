"""
Sentence-BERT embeddings with FAISS vector search.
Provides semantic similarity search over resume embeddings.
"""
import logging
import pickle
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Manages SBERT embeddings and FAISS vector index for semantic search."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._index = None
        self.id_map: List[str] = []
        self.dimension = 384  # all-MiniLM-L6-v2

    def _get_model(self):
        """Lazy-load the SBERT model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading SBERT model: %s", self.model_name)
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                logger.warning("sentence-transformers not installed; using TF-IDF fallback")
                self._model = None
        return self._model

    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Encode texts to L2-normalized float32 embeddings."""
        model = self._get_model()
        if model is None:
            return self._tfidf_fallback(texts)
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embeddings.astype(np.float32)

    def encode_single(self, text: str) -> np.ndarray:
        return self.encode([text])[0]

    def _tfidf_fallback(self, texts: List[str]) -> np.ndarray:
        """TF-IDF based fallback when SBERT is not available."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.preprocessing import normalize
        vec = TfidfVectorizer(max_features=self.dimension, ngram_range=(1, 2), sublinear_tf=True)
        X = vec.fit_transform(texts).toarray()
        # Pad or truncate to fixed dimension
        if X.shape[1] < self.dimension:
            X = np.pad(X, ((0, 0), (0, self.dimension - X.shape[1])))
        else:
            X = X[:, :self.dimension]
        return normalize(X).astype(np.float32)

    # ── FAISS Index ───────────────────────────────────────────────────────────

    def _ensure_index(self):
        if self._index is None:
            try:
                import faiss
                self._index = faiss.IndexFlatIP(self.dimension)
            except ImportError:
                logger.warning("faiss-cpu not installed; semantic search disabled")
                self._index = None

    def build_index(self, embeddings: np.ndarray, ids: List[str]):
        """Build FAISS flat inner-product index."""
        self._ensure_index()
        if self._index is None:
            return
        import faiss
        self._index = faiss.IndexFlatIP(self.dimension)
        self._index.add(embeddings.astype(np.float32))
        self.id_map = ids
        logger.info("FAISS index built: %d vectors", len(ids))

    def add_to_index(self, embedding: np.ndarray, resume_id: str):
        """Incrementally add a single embedding."""
        self._ensure_index()
        if self._index is None:
            return
        self._index.add(embedding.reshape(1, -1).astype(np.float32))
        self.id_map.append(resume_id)

    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> List[Tuple[str, float]]:
        """Return top-k (resume_id, score) pairs by cosine similarity."""
        if self._index is None or len(self.id_map) == 0:
            return []
        k = min(top_k, len(self.id_map))
        query = query_embedding.reshape(1, -1).astype(np.float32)
        scores, indices = self._index.search(query, k)
        return [
            (self.id_map[idx], float(score))
            for score, idx in zip(scores[0], indices[0])
            if idx >= 0
        ]

    def save(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        if self._index is not None:
            import faiss
            faiss.write_index(self._index, str(path / "faiss.index"))
        with open(path / "id_map.pkl", "wb") as f:
            pickle.dump(self.id_map, f)
        logger.info("FAISS index saved to %s", path)

    def load(self, path: Path):
        index_file = path / "faiss.index"
        id_map_file = path / "id_map.pkl"
        if index_file.exists():
            import faiss
            self._index = faiss.read_index(str(index_file))
        if id_map_file.exists():
            with open(id_map_file, "rb") as f:
                self.id_map = pickle.load(f)
        logger.info("FAISS index loaded: %d vectors", len(self.id_map))


embedding_service = EmbeddingService()

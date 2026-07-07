"""
TextCleaner: Low-level text normalisation pipeline.

Steps applied in order:
    1. Lowercase
    2. Remove URLs, emails, phone numbers
    3. Remove punctuation and special characters
    4. Lemmatise via spaCy
    5. Remove NLTK stopwords
    6. Normalise whitespace
    7. Remove duplicate consecutive words
"""
import logging
import re
import string
from functools import lru_cache
from typing import Optional

import nltk
import spacy

from backend.config import settings

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"http\S+|www\.\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\S+@\S+\.\S+")
_PHONE_RE = re.compile(r"(\+?\d{1,3}[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}")
_SPECIAL_RE = re.compile(r"[^a-z0-9\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def _ensure_nltk() -> None:
    for corpus in ("stopwords", "wordnet", "punkt"):
        try:
            nltk.data.find(f"corpora/{corpus}" if corpus != "punkt" else f"tokenizers/{corpus}")
        except LookupError:
            nltk.download(corpus, quiet=True)


class TextCleaner:
    """Thread-safe text cleaner; spaCy pipeline is loaded once per instance."""

    def __init__(self) -> None:
        _ensure_nltk()
        self._stop_words = set(nltk.corpus.stopwords.words("english"))
        # Keep technical terms that NLTK marks as stopwords
        self._stop_words -= {"no", "not", "more", "most", "new", "own", "same", "few"}

        try:
            self._nlp = spacy.load(settings.SPACY_MODEL, disable=["ner", "parser"])
        except OSError:
            logger.warning("spaCy model '%s' not found — downloading.", settings.SPACY_MODEL)
            import subprocess
            subprocess.run(
                ["python", "-m", "spacy", "download", settings.SPACY_MODEL],
                check=True,
            )
            self._nlp = spacy.load(settings.SPACY_MODEL, disable=["ner", "parser"])

    def clean(self, text: str, preserve_skills: bool = True) -> str:
        """Return fully cleaned and lemmatised text."""
        if not text:
            return ""
        text = text.lower()
        text = _URL_RE.sub(" ", text)
        text = _EMAIL_RE.sub(" ", text)
        text = _PHONE_RE.sub(" ", text)
        text = text.translate(str.maketrans(string.punctuation, " " * len(string.punctuation)))
        text = _SPECIAL_RE.sub(" ", text)
        text = self._lemmatise(text)
        text = self._remove_stopwords(text)
        text = _WHITESPACE_RE.sub(" ", text).strip()
        return text

    def _lemmatise(self, text: str) -> str:
        # spaCy has a 1M character limit; chunk if needed
        chunk_size = 900_000
        if len(text) <= chunk_size:
            doc = self._nlp(text)
            return " ".join(token.lemma_ for token in doc if not token.is_space)

        chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
        lemmas = []
        for chunk in chunks:
            doc = self._nlp(chunk)
            lemmas.extend(token.lemma_ for token in doc if not token.is_space)
        return " ".join(lemmas)

    def _remove_stopwords(self, text: str) -> str:
        return " ".join(w for w in text.split() if w not in self._stop_words)

    def light_clean(self, text: str) -> str:
        """Minimal cleaning: lowercase, remove URLs/emails, normalise whitespace.
        Useful when preserving skill names verbatim matters."""
        text = text.lower()
        text = _URL_RE.sub(" ", text)
        text = _EMAIL_RE.sub(" ", text)
        text = _WHITESPACE_RE.sub(" ", text).strip()
        return text

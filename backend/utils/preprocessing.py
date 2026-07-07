"""
Preprocessing pipeline: orchestrates TextCleaner + tokenisation + NLP tagging.
Exposes a single PreprocessingPipeline class used by both the parser and ranking engine.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import List

import nltk
import spacy

from backend.config import settings
from backend.utils.text_cleaner import TextCleaner, _ensure_nltk

logger = logging.getLogger(__name__)


@dataclass
class ProcessedDocument:
    raw_text: str
    cleaned_text: str
    tokens: List[str] = field(default_factory=list)
    noun_chunks: List[str] = field(default_factory=list)
    entities: List[dict] = field(default_factory=list)
    sentences: List[str] = field(default_factory=list)
    word_count: int = 0
    unique_word_count: int = 0


class PreprocessingPipeline:
    """Full NLP preprocessing: clean → tokenise → extract entities/chunks."""

    def __init__(self) -> None:
        _ensure_nltk()
        self.cleaner = TextCleaner()
        try:
            # Load full pipeline for entity extraction
            self._nlp_full = spacy.load(settings.SPACY_MODEL)
        except OSError:
            import subprocess
            subprocess.run(
                ["python", "-m", "spacy", "download", settings.SPACY_MODEL],
                check=True,
            )
            self._nlp_full = spacy.load(settings.SPACY_MODEL)

    def process(self, text: str) -> ProcessedDocument:
        if not text:
            return ProcessedDocument(raw_text="", cleaned_text="")

        cleaned = self.cleaner.clean(text)

        # Run full spaCy pipeline on original (not cleaned) text for NER accuracy
        doc = self._nlp_full(text[:100_000])

        tokens = [token.text.lower() for token in doc if not token.is_space and not token.is_punct]
        noun_chunks = [chunk.text.lower() for chunk in doc.noun_chunks]
        entities = [
            {"text": ent.text, "label": ent.label_}
            for ent in doc.ents
        ]
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

        return ProcessedDocument(
            raw_text=text,
            cleaned_text=cleaned,
            tokens=tokens,
            noun_chunks=noun_chunks,
            entities=entities,
            sentences=sentences,
            word_count=len(tokens),
            unique_word_count=len(set(tokens)),
        )

    def tokenise(self, text: str) -> List[str]:
        """Tokenise cleaned text for downstream ML."""
        _ensure_nltk()
        try:
            return nltk.word_tokenize(text.lower())
        except LookupError:
            nltk.download("punkt_tab", quiet=True)
            return nltk.word_tokenize(text.lower())

    def get_bigrams(self, tokens: List[str]) -> List[str]:
        return [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]

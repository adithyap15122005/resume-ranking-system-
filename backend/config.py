"""
Central configuration for the Resume Ranking System.
All tuneable parameters live here — no magic numbers scattered across modules.
"""
import logging
import logging.handlers
from pathlib import Path
from typing import Tuple

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AI Resume Ranking System"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    FRONTEND_PORT: int = 8501
    API_BASE_URL: str = "http://localhost:8000"

    # Directories (resolved relative to project root)
    BASE_DIR: Path = Path(__file__).parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    RESUME_DIR: Path = UPLOAD_DIR / "resumes"
    JOB_DIR: Path = UPLOAD_DIR / "jobs"
    DATASET_DIR: Path = UPLOAD_DIR / "dataset"
    TRAINED_DIR: Path = BASE_DIR / "trained"
    LOG_DIR: Path = BASE_DIR / "logs"

    # Database
    DATABASE_URL: str = "sqlite:///./resume_ranking.db"

    # ML — TF-IDF
    MAX_FEATURES: int = 8000
    NGRAM_RANGE: Tuple[int, int] = (1, 2)
    MIN_DF: int = 1
    SUBLINEAR_TF: bool = True

    # Similarity engine: "tfidf" | "sbert"
    SIMILARITY_ENGINE: str = "tfidf"
    SBERT_MODEL: str = "all-MiniLM-L6-v2"

    # Ranking thresholds
    EXCELLENT_THRESHOLD: float = 95.0
    STRONG_THRESHOLD: float = 80.0
    SUITABLE_THRESHOLD: float = 60.0
    AVERAGE_THRESHOLD: float = 40.0

    # Upload limits
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: Tuple[str, ...] = (".pdf", ".docx", ".txt")

    # spaCy model
    SPACY_MODEL: str = "en_core_web_sm"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure all required directories exist on import
for _dir in [
    settings.RESUME_DIR,
    settings.JOB_DIR,
    settings.DATASET_DIR,
    settings.TRAINED_DIR,
    settings.LOG_DIR,
]:
    _dir.mkdir(parents=True, exist_ok=True)


def setup_logging() -> None:
    """Configure rotating file + console logging."""
    log_file = settings.LOG_DIR / "app.log"
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)

    # Rotating file handler — 5 MB per file, keep 3 backups
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    if not root.handlers:
        root.addHandler(console)
        root.addHandler(file_handler)

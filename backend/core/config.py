"""
Central configuration for HireIQ AI Hiring Intelligence Platform.
All settings are environment-variable driven with sensible defaults.
"""
import logging
import logging.handlers
from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "HireIQ - AI Hiring Intelligence Platform"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development | staging | production

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    EMAIL_VERIFY_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 2

    # ── Server ────────────────────────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./hireiq.db"
    # For PostgreSQL: postgresql+asyncpg://hireiq:hireiq@localhost:5432/hireiq
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL_SECONDS: int = 300

    # ── OAuth ─────────────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None

    # ── Email (SMTP) ──────────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "noreply@hireiq.ai"

    # ── AWS / Storage ─────────────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: Optional[str] = None

    # ── File Paths ────────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    RESUME_DIR: Path = UPLOAD_DIR / "resumes"
    JOB_DIR: Path = UPLOAD_DIR / "jobs"
    DATASET_DIR: Path = UPLOAD_DIR / "datasets"
    TRAINED_DIR: Path = BASE_DIR / "trained"
    MODELS_DIR: Path = BASE_DIR / "models"
    EMBEDDINGS_DIR: Path = BASE_DIR / "embeddings"
    EXPERIMENTS_DIR: Path = BASE_DIR / "experiments"
    LOG_DIR: Path = BASE_DIR / "logs"

    # ── ML / AI ───────────────────────────────────────────────────────────────
    SBERT_MODEL: str = "all-MiniLM-L6-v2"
    FAISS_INDEX_PATH: str = "embeddings/faiss"
    EMBEDDING_DIMENSION: int = 384
    MAX_FEATURES: int = 8000
    NGRAM_RANGE: Tuple[int, int] = (1, 2)
    SPACY_MODEL: str = "en_core_web_sm"

    # Similarity engine: "tfidf" | "sbert"
    SIMILARITY_ENGINE: str = "sbert"

    # Ranking thresholds
    EXCELLENT_THRESHOLD: float = 90.0
    STRONG_THRESHOLD: float = 75.0
    SUITABLE_THRESHOLD: float = 55.0
    AVERAGE_THRESHOLD: float = 35.0

    # ── MLflow ────────────────────────────────────────────────────────────────
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME: str = "hireiq-hiring-prediction"

    # ── Upload Limits ─────────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_RESUME_EXTENSIONS: Tuple[str, ...] = (".pdf", ".docx", ".txt")
    ALLOWED_DATASET_EXTENSIONS: Tuple[str, ...] = (".csv", ".xlsx")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


settings = Settings()

# Ensure all directories exist
for _dir in [
    settings.RESUME_DIR,
    settings.JOB_DIR,
    settings.DATASET_DIR,
    settings.TRAINED_DIR,
    settings.MODELS_DIR,
    settings.EMBEDDINGS_DIR,
    settings.EXPERIMENTS_DIR,
    settings.LOG_DIR,
]:
    _dir.mkdir(parents=True, exist_ok=True)


def setup_logging() -> None:
    """Configure rotating file + console logging."""
    log_file = settings.LOG_DIR / "hireiq.log"
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    if not root.handlers:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        root.addHandler(console)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

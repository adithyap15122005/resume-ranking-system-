"""
FastAPI application entry point.

Run with:
    uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

Interactive API docs:  http://localhost:8000/docs
ReDoc:                 http://localhost:8000/redoc
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.ranking import router as ranking_router
from backend.api.upload import router as upload_router
from backend.config import settings, setup_logging
from backend.database import init_db

# Initialise logging before anything else
setup_logging()
logger = logging.getLogger(__name__)

# ── Application factory ───────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description=(
        "AI-powered recruitment system that ranks resumes against a job description "
        "using TF-IDF / cosine similarity, spaCy NER, and a modular ML pipeline."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Allow the Streamlit frontend (and any other client) to reach the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(upload_router, prefix="")
app.include_router(ranking_router, prefix="")

# ── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info(
        "%s v%s started — docs at http://%s:%d/docs",
        settings.APP_NAME,
        settings.VERSION,
        settings.API_HOST,
        settings.API_PORT,
    )


@app.on_event("shutdown")
def on_shutdown() -> None:
    logger.info("%s shutting down.", settings.APP_NAME)


# ── Health & info endpoints ───────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


@app.get("/info", tags=["Health"])
def info():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "similarity_engine": settings.SIMILARITY_ENGINE,
        "max_features": settings.MAX_FEATURES,
        "ngram_range": settings.NGRAM_RANGE,
        "upload_dir": str(settings.UPLOAD_DIR),
    }

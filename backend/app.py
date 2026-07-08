"""
HireIQ — AI Hiring Intelligence Platform
FastAPI application entry point.

Run with:
    uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import settings, setup_logging
from backend.core.database import init_db

setup_logging()
logger = logging.getLogger(__name__)

# ── App Factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description=(
        "Production-grade AI Hiring Intelligence Platform — "
        "SBERT embeddings, FAISS vector search, SHAP explainability, "
        "multi-model ML pipeline, JWT auth, and recruiter workflow automation."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS + ["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Routers ───────────────────────────────────────────────────────────────────

from backend.api.auth import router as auth_router
from backend.api.resumes import router as resumes_router
from backend.api.jobs import router as jobs_router
from backend.api.analytics import router as analytics_router
from backend.api.training import router as training_router
from backend.api.chat import router as chat_router

# New v2 routers
app.include_router(auth_router)
app.include_router(resumes_router)
app.include_router(jobs_router)
app.include_router(analytics_router)
app.include_router(training_router)
app.include_router(chat_router)

# ── Legacy v1 compatibility (old Streamlit API) ────────────────────────────────
try:
    from backend.api.upload import router as upload_router_v1
    from backend.api.ranking import router as ranking_router_v1
    app.include_router(upload_router_v1, prefix="/v1")
    app.include_router(ranking_router_v1, prefix="/v1")
except Exception as e:
    logger.warning("Could not load legacy v1 routers: %s", e)

# ── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    await init_db()
    logger.info("%s v%s — docs at http://localhost:%d/docs", settings.APP_NAME, settings.VERSION, settings.API_PORT)


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("%s shutting down.", settings.APP_NAME)

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
        "features": [
            "JWT Authentication",
            "SBERT Semantic Ranking",
            "FAISS Vector Search",
            "SHAP Explainability",
            "Multi-Model ML Pipeline",
            "Recruiter Pipeline Kanban",
            "AI Chat Assistant",
            "Dataset Training",
        ],
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "version": settings.VERSION}


@app.get("/info", tags=["Health"])
def info():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "similarity_engine": settings.SIMILARITY_ENGINE,
        "sbert_model": settings.SBERT_MODEL,
        "database": settings.DATABASE_URL.split("///")[0],
        "upload_dir": str(settings.UPLOAD_DIR),
    }

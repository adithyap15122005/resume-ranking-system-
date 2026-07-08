# HireIQ — Production-Grade AI Hiring Intelligence Platform

> An end-to-end AI hiring platform that competes with Greenhouse, Lever, and Eightfold AI.  
> Built for hackathon wins and real-world recruiting teams.

---

## Architecture Overview

```
resume-ranking-system/
├── backend/                    # FastAPI async backend
│   ├── core/
│   │   ├── config.py           # pydantic-settings v2 Settings
│   │   ├── database.py         # async SQLAlchemy 2.0
│   │   └── security.py         # JWT, bcrypt, token helpers
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── user.py             # Users with OAuth, roles
│   │   ├── organization.py     # Multi-tenant orgs
│   │   ├── resume.py           # Rich resume with AI scores
│   │   ├── job.py              # Job descriptions
│   │   ├── ranking.py          # Ranking results + SHAP
│   │   └── notification.py     # In-app notifications
│   ├── api/                    # FastAPI routers
│   │   ├── auth.py             # JWT auth + OAuth stubs
│   │   ├── resumes.py          # Upload, parse, search
│   │   ├── jobs.py             # CRUD + AI ranking trigger
│   │   ├── analytics.py        # Dashboard stats
│   │   ├── training.py         # Dataset upload + ML training
│   │   └── chat.py             # AI assistant with RAG
│   └── ml/                     # ML pipeline
│       ├── embeddings.py       # SBERT + FAISS vector search
│       ├── ranking_engine.py   # Hybrid ranking (50/30/20)
│       ├── ai_intelligence.py  # Candidate intelligence scores
│       └── training.py         # Multi-model training pipeline
├── frontend-next/              # Next.js 14 App Router frontend
│   └── src/
│       ├── app/
│       │   ├── (auth)/         # Login + Signup pages
│       │   └── (dashboard)/    # All dashboard pages
│       │       ├── dashboard/  # Analytics overview
│       │       ├── candidates/ # Resume upload + talent pool
│       │       ├── jobs/       # Job posting management
│       │       ├── rankings/   # AI ranking results + SHAP
│       │       ├── pipeline/   # Kanban drag-and-drop
│       │       ├── analytics/  # Full analytics suite
│       │       ├── training/   # Dataset training dashboard
│       │       ├── assistant/  # AI chat assistant
│       │       └── settings/   # User + org settings
│       ├── components/
│       │   └── layout/         # Sidebar + Topbar
│       ├── lib/
│       │   ├── api.ts          # Axios + all API functions
│       │   └── auth.ts         # Token management
│       └── store/
│           └── auth.ts         # Zustand auth store
├── docker-compose.yml          # Full stack: PG + Redis + Backend + Frontend + MLflow
├── Dockerfile.backend
├── .env.example
└── .github/workflows/ci.yml    # GitHub Actions CI/CD
```

---

## Key Features

| Feature | Technology |
|---------|-----------|
| **AI Resume Parsing** | spaCy NER, PyMuPDF, python-docx |
| **Semantic Ranking** | SBERT all-MiniLM-L6-v2 + FAISS |
| **Hybrid Scoring** | Embedding (50%) + Skills (30%) + Experience (20%) |
| **Explainable AI** | SHAP-style contribution breakdown per candidate |
| **Candidate Intelligence** | Leadership/communication/technical/culture-fit scores |
| **ML Training** | XGBoost, LightGBM, Random Forest, Logistic Regression |
| **Kanban Pipeline** | Drag-and-drop across 8 hiring stages |
| **AI Chat Assistant** | Intent-based RAG over resumes + jobs |
| **Multi-tenant** | Organization isolation on all queries |
| **Auth** | JWT (access + refresh), roles, email verification |

---

## Quick Start

### 1. Backend (Development)

```bash
# Copy env
cp .env.example .env

# Install deps
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Run
uvicorn backend.app:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend-next
npm install --legacy-peer-deps
npm run dev
```

Open: http://localhost:3000

### 3. Full Stack with Docker

```bash
docker compose up --build
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- MLflow: http://localhost:5001
- PostgreSQL: localhost:5432

---

## API Highlights

```
POST   /api/auth/signup           Create account
POST   /api/auth/login            Login → JWT tokens
POST   /api/resumes/upload        Upload + AI parse resumes
GET    /api/resumes/search/semantic  FAISS semantic search
POST   /api/jobs/{id}/rank        Run AI ranking for a job
GET    /api/jobs/{id}/rankings    Get ranked candidates + SHAP
PUT    /api/jobs/{id}/pipeline/{resume_id}  Move kanban stage
GET    /api/analytics/dashboard   Hiring funnel + stats
POST   /api/training/upload-dataset  Upload Kaggle CSV
POST   /api/training/train        Train XGBoost/LightGBM/RF
GET    /api/training/leaderboard  Model performance comparison
POST   /api/chat                  AI assistant with RAG
```

---

## Tech Stack

**Backend:** FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL · Redis · Celery · Alembic  
**AI/ML:** SBERT · FAISS · XGBoost · LightGBM · scikit-learn · spaCy · MLflow  
**Frontend:** Next.js 14 · TypeScript · Tailwind CSS · Framer Motion · Recharts · Zustand  
**DevOps:** Docker · GitHub Actions · Vercel (frontend) · Railway/Render (backend)

---

## Environment Variables

See `.env.example` for all configuration options including:
- `SECRET_KEY` — JWT signing secret
- `DATABASE_URL` — SQLite (dev) or PostgreSQL (prod)
- `SBERT_MODEL` — Sentence transformer model name
- OAuth credentials for Google and GitHub
- AWS S3 for resume file storage

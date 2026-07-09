# HireIQ — AI-Powered Resume Ranking System

A full-stack AI hiring intelligence platform with semantic search, ML-based candidate ranking, SHAP explainability, and a 5-step model training pipeline. Built with FastAPI + Next.js 14.

---

## What This Does

HireIQ lets a recruiting team:

1. **Upload resumes** (PDF/DOCX) — parsed automatically into structured data
2. **Post job descriptions** — with required/preferred skills, experience, and education requirements
3. **Run AI ranking** — candidates are scored against a job using one of four ranking modes
4. **Explain every score** — SHAP feature contributions show *why* a candidate ranked where they did
5. **Train custom ML models** — upload a hiring dataset, train XGBoost/LightGBM/RF, deploy the best model
6. **Move candidates through a kanban pipeline** — from Applied → Screened → Interview → Offer → Hired

---

## System Architecture

```
resume-ranking-system/
├── backend/                        # FastAPI async backend
│   ├── app.py                      # App entry point, CORS, router registration
│   ├── core/
│   │   ├── config.py               # pydantic-settings v2 (env vars, paths)
│   │   ├── database.py             # Async SQLAlchemy 2.0 + SQLite/PostgreSQL
│   │   └── security.py             # JWT (access + refresh tokens), bcrypt
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── user.py                 # Users with roles (admin / recruiter)
│   │   ├── organization.py         # Multi-tenant org isolation
│   │   ├── resume.py               # Rich resume: skills, embeddings, AI scores
│   │   ├── job.py                  # Job descriptions with skill lists
│   │   ├── ranking.py              # Ranking results + SHAP JSON
│   │   ├── ml_model.py             # Trained model registry
│   │   ├── training_dataset.py     # Uploaded training datasets
│   │   ├── training_experiment.py  # Training run tracking
│   │   └── hiring_outcome.py       # Post-hire feedback for continuous learning
│   ├── api/                        # FastAPI routers
│   │   ├── auth.py                 # Signup / login / refresh / me
│   │   ├── resumes.py              # Upload, parse, search, pin, notes
│   │   ├── jobs.py                 # CRUD + AI ranking trigger
│   │   ├── analytics.py            # Dashboard, hiring funnel, skill demand
│   │   ├── training.py             # Dataset upload, EDA, training, leaderboard
│   │   └── chat.py                 # AI assistant with intent-based RAG
│   └── ml/                         # Core ML pipeline
│       ├── feature_engineering.py  # 51-feature canonical vector (training + inference)
│       ├── ranking_engine.py       # Hybrid ranking engine + ML scoring + SHAP
│       ├── model_registry.py       # Production model management + artifact loading
│       ├── embeddings.py           # SBERT all-MiniLM-L6-v2 + FAISS index
│       ├── ai_intelligence.py      # Candidate intelligence profiling
│       └── training.py             # Legacy training stub
│
├── frontend-next/                  # Next.js 14 App Router frontend
│   └── src/
│       ├── app/
│       │   ├── (auth)/             # Login + Signup
│       │   └── (dashboard)/        # All dashboard pages
│       │       ├── dashboard/      # Analytics overview cards
│       │       ├── candidates/     # Resume upload + talent pool
│       │       ├── jobs/           # Job posting management
│       │       ├── rankings/       # AI ranking results + SHAP bars
│       │       ├── pipeline/       # Kanban (8 stages, drag-and-drop)
│       │       ├── analytics/      # Funnel, skill demand, model performance
│       │       ├── training/       # 5-step ML training console
│       │       ├── assistant/      # AI chat interface
│       │       └── settings/       # User + org settings
│       ├── lib/
│       │   ├── api.ts              # Axios client + all API functions
│       │   └── auth.ts             # Token storage + refresh logic
│       └── store/
│           └── auth.ts             # Zustand auth store
│
├── requirements.txt                # All Python dependencies (pinned)
├── docker-compose.yml              # Full stack: Backend + Frontend + MLflow + Redis + PG
├── Dockerfile.backend
├── .env.example
└── .github/workflows/ci.yml        # GitHub Actions CI
```

---

## Feature Overview

### Resume & Job Management
- Upload PDF / DOCX resumes — parsed with PyMuPDF + pdfplumber + python-docx
- spaCy NER extracts skills, education, experience dates, contact info
- Resume completeness score (ATS score) computed automatically
- Pin resumes, add recruiter notes, view parsed fields
- Semantic search across all resumes using FAISS vector index

### AI Ranking Engine — Four Modes

| Mode | Formula | When to use |
|---|---|---|
| **Traditional** | SBERT 50% + Skills 30% + Experience 20% | No trained model available |
| **Semantic** | Pure SBERT embedding cosine similarity | Text-heavy JDs |
| **ML Only** | Trained model probability output | When you have a good trained model |
| **Hybrid AI** *(default)* | ML 70% + SBERT 20% + Skills 10% | Best overall accuracy |

The ranking mode is selectable per-run from the frontend or via `?ranking_mode=hybrid` query param.

### SHAP Explainability
Every candidate in ML / Hybrid mode gets a per-feature SHAP breakdown showing exactly which features pushed their score up or down. Displayed as green (positive) / red (negative) contribution bars in the candidate detail panel.

### Hiring Pipeline (Kanban)
Candidates can be moved through 8 stages: Applied → Screened → Phone Screen → Technical Interview → Final Round → Offer Extended → Hired / Rejected. Stage changes are tracked and feed into analytics.

### AI Assistant
Intent-based chat interface that understands queries like "who has the best Python skills for job X?" and "compare top 3 candidates for the Data Engineer role". Uses RAG over the resume + job database.

---

## ML Training Pipeline

### Overview
Admins can upload a training dataset, run multi-model experiments, compare results on a leaderboard, and deploy the best model to production. Deployed models are automatically used for ranking.

### 5-Step Workflow

```
Step 1: Upload Dataset     → CSV or XLSX (hiring format or pre-engineered features)
Step 2: EDA                → Column stats, class distribution, missing value report
Step 3: Feature Engineering→ Auto-extract 51 features if hiring format detected
Step 4: Train Experiments  → Multiple algorithms in parallel, tracked per run
Step 5: Leaderboard        → Compare F1 / ROC-AUC / PR-AUC / CV scores, deploy best
```

### Supported Algorithms
Logistic Regression, Random Forest, Extra Trees, Gradient Boosting, SVM, Neural Network (MLP), XGBoost, LightGBM, CatBoost

### Professional ML Practices Implemented

| Practice | Implementation |
|---|---|
| **No data leakage** | `train_test_split` BEFORE `StandardScaler.fit()` — scaler fitted on training set only |
| **Class imbalance** | SMOTE with adaptive `k_neighbors`; fallback to `class_weight='balanced'` |
| **Cross-validation** | 5-fold stratified CV → `cv_f1_mean` + `cv_f1_std` reported per model |
| **Probability calibration** | `CalibratedClassifierCV(method='isotonic')` fixes the ~50% constant prediction bug |
| **SHAP-safe artifact** | `base_model.pkl` (raw, for SHAP) saved alongside `model.pkl` (calibrated, for inference) |
| **PR-AUC metric** | `average_precision_score` added — more informative than ROC-AUC on imbalanced data |

### Training Dataset Format (Hiring Format)

When your CSV has `resume_text` + `job_description` columns, HireIQ auto-extracts all 51 features — no manual feature engineering needed.

```csv
job_title, job_description, required_skills, preferred_skills,
experience_requirement, education_requirement,
resume_text, skills, experience_years, education,
certifications, projects, ats_score, portfolio_url, github_url,
soft_skills, languages,
shortlisted
```

- `skills`, `required_skills`, etc. — comma-separated strings or lists
- `shortlisted` — `0`/`1` or `No`/`Yes`
- `ats_score` — 0–100 completeness score

---

## The 51-Feature Vector

`backend/ml/feature_engineering.py` defines a canonical 51-feature vector (VERSION 2.0) used identically at training time and inference time — eliminating training/serving skew.

### Feature Groups

**Text Similarity (0–15, original 16)**
| Feature | Description |
|---|---|
| `tfidf_similarity` | Unigram + bigram TF-IDF cosine sim between resume and job |
| `sbert_similarity` | SBERT embedding cosine similarity (falls back to TF-IDF if no embeddings) |
| `skill_match_required` | Fraction of required skills covered by resume |
| `skill_match_preferred` | Fraction of preferred skills covered |
| `experience_match` | Graduated score: candidate years vs required years |
| `education_score` | Resume education level vs job requirement (0.5 neutral if no req) |
| `ats_score` | Resume completeness / 100 |
| `projects_count_norm` | min(projects, 10) / 10 |
| `certifications_count_norm` | min(certs, 5) / 5 |
| `languages_count_norm` | min(languages, 5) / 5 |
| `soft_skills_count_norm` | min(soft skills, 10) / 10 |
| `has_portfolio` | 1 if portfolio URL present |
| `has_github` | 1 if GitHub URL present |
| `years_experience_norm` | min(years, 15) / 15 |
| `skills_count_norm` | min(skills, 30) / 30 |
| `keyword_density` | Job keyword unigram overlap in resume |

**Text Similarity Additions (16–21)**
`bigram_similarity`, `title_match_score`, `job_coverage_ratio`, `tech_term_match`, `resume_length_norm`, `vocabulary_richness`

**Experience Quality (22–26)**
`experience_surplus_norm`, `experience_deficit_norm`, `seniority_level` (entry/mid/senior/exec tiers), `leadership_score`, `quantification_score`

**Skills Depth (27–31)**
`skill_gap_required`, `skill_gap_preferred`, `raw_skill_overlap_norm`, `tech_skills_ratio`, `skills_per_year_norm`

**Education & Credentials (32–35)**
`candidate_education_level`, `has_relevant_degree`, `certifications_per_year_norm`, `total_credentials_norm`

**Resume Quality Signals (36–41)**
`has_summary`, `has_work_experience_section`, `has_education_section`, `section_completeness`, `achievement_density`, `contact_completeness`

**Career Trajectory (42–46)**
`career_growth_score`, `multi_company_indicator`, `industry_match_score`, `soft_skill_overlap`, `professional_presence`

**Domain & Role Fit (47–50)**
`functional_area_match`, `description_keyword_density`, `role_seniority_match`, `job_title_word_count_norm`

All features are clamped to `[0.0, 1.0]`. Missing or invalid inputs default to `0.0` (education score defaults to `0.5` — neutral when no requirement stated).

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### 1. Clone & Setup

```bash
git clone https://github.com/adithyap15122005/resume-ranking-system-.git
cd resume-ranking-system-
cp .env.example .env
```

### 2. Backend

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Start backend (dev mode)
uvicorn backend.app:app --reload --port 8000
```

API docs: http://localhost:8000/docs  
OpenAPI schema: http://localhost:8000/openapi.json

### 3. Frontend

```bash
cd frontend-next
npm install --legacy-peer-deps
npm run dev
```

Open: http://localhost:3000

### 4. Full Stack with Docker

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000/docs |
| MLflow | http://localhost:5001 |
| PostgreSQL | localhost:5432 |

---

## API Reference

### Auth
```
POST  /api/auth/signup          Register (email, username, full_name, password, role)
POST  /api/auth/login           Login → { access_token, refresh_token }
POST  /api/auth/refresh         Refresh access token
GET   /api/auth/me              Current user profile
PUT   /api/auth/me              Update profile
```

### Resumes
```
POST  /api/resumes/upload                Upload PDF/DOCX files (multipart)
GET   /api/resumes/                      List resumes (paginated, searchable)
GET   /api/resumes/{id}                  Get parsed resume
DELETE /api/resumes/{id}                 Delete
PUT   /api/resumes/{id}/pin              Toggle pin
PUT   /api/resumes/{id}/notes            Update recruiter notes
GET   /api/resumes/{id}/intelligence     AI intelligence profile
GET   /api/resumes/search/semantic       FAISS semantic search (?q=...&top_k=10)
```

### Jobs & Ranking
```
POST  /api/jobs/                         Create job
GET   /api/jobs/                         List jobs (?status=open)
GET   /api/jobs/{id}                     Get job
PUT   /api/jobs/{id}                     Update job
DELETE /api/jobs/{id}                    Delete job
POST  /api/jobs/{id}/rank                Run AI ranking
                                           ?ranking_mode=hybrid|ml|semantic|traditional
                                           ?min_score=0
GET   /api/jobs/{id}/rankings            Get saved ranking results
PUT   /api/jobs/{id}/pipeline/{resume_id} Move candidate to kanban stage
GET   /api/jobs/{id}/analytics           Job-level analytics
```

### ML Training (Admin only)
```
POST  /api/training/datasets/upload      Upload training CSV/XLSX
GET   /api/training/datasets             List datasets
POST  /api/training/datasets/{id}/analyze  EDA (class distribution, stats)
POST  /api/training/datasets/{id}/engineer  Feature engineering preview
POST  /api/training/experiments          Start training experiment
GET   /api/training/experiments/{id}     Poll training progress
GET   /api/training/experiments          List all experiments
GET   /api/training/models               Model leaderboard
GET   /api/training/models/production    Current production model
POST  /api/training/models/{id}/deploy   Deploy to production
DELETE /api/training/models/{id}         Delete model
POST  /api/training/outcomes             Record post-hire feedback
```

### Analytics & Chat
```
GET   /api/analytics/dashboard           Overall KPIs
GET   /api/analytics/hiring-funnel       Pipeline conversion rates
GET   /api/analytics/skill-demand        Top skills across jobs
GET   /api/analytics/model-performance   ML model comparison chart
POST  /api/chat/                         AI assistant message
GET   /api/chat/history                  Chat history by session
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
# Core
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite+aiosqlite:///./hireiq.db   # or postgresql+asyncpg://...
MODELS_DIR=./models

# ML
SBERT_MODEL=all-MiniLM-L6-v2
FAISS_INDEX_PATH=./embeddings/faiss.index

# Optional: OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# Optional: AWS S3
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=

# Optional: Redis + Celery
REDIS_URL=redis://localhost:6379/0
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend framework** | FastAPI 0.115 + Uvicorn |
| **Database ORM** | SQLAlchemy 2.0 (async) + Alembic migrations |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Auth** | python-jose (JWT) + passlib (bcrypt) |
| **NLP / Parsing** | spaCy 3.8, NLTK, PyMuPDF, pdfplumber, python-docx |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2, 384-dim) |
| **Vector search** | FAISS CPU |
| **ML classifiers** | scikit-learn 1.6, XGBoost 2.1, LightGBM 4.5, CatBoost 1.2 |
| **Imbalanced data** | imbalanced-learn 0.12 (SMOTE) |
| **Explainability** | SHAP 0.46 (TreeExplainer + LinearExplainer) |
| **MLOps** | MLflow 2.18 (experiment tracking) |
| **Frontend** | Next.js 14 (App Router) + TypeScript |
| **Styling** | Tailwind CSS + Framer Motion |
| **Charts** | Recharts |
| **State** | Zustand |
| **HTTP client** | Axios |
| **Export** | ReportLab, openpyxl, fpdf2 |
| **Containerization** | Docker + Docker Compose |
| **CI/CD** | GitHub Actions |

---

## Development Notes

### Running with an existing database
The SQLite database (`hireiq.db`) is excluded from git. On first run, the app auto-creates all tables via `Base.metadata.create_all()`.

### Training a model end-to-end
1. Log in as an admin account
2. Go to **AI Model Studio** → **Upload Dataset**
3. Upload a CSV with the hiring dataset format (see above)
4. Click **Analyze** → review class distribution
5. Click **Start Experiment** → select algorithms
6. Watch training progress in real-time
7. Open the **Leaderboard** → compare F1, ROC-AUC, PR-AUC, CV scores
8. Click **Deploy** on the best model
9. Go to **Rankings** → select **Hybrid AI** mode → run ranking
10. Expand any candidate → see SHAP feature contribution bars

### Model artifact format
Each trained model is saved as a directory bundle:
```
models/{uuid}/
├── model.pkl           # CalibratedClassifierCV — used for predict_proba()
├── base_model.pkl      # Raw classifier — used for SHAP TreeExplainer
├── preprocessor.pkl    # Fitted StandardScaler
├── label_encoder.pkl   # Target LabelEncoder
├── feature_metadata.json  # feature_names, version, smote_applied, cv scores
├── metrics.json        # accuracy, f1, roc_auc, pr_auc, confusion_matrix
├── training_config.json
└── version.json
```

Old single-`.pkl` models are still supported via a legacy loader for backward compatibility.

### Feature versioning
- VERSION 1.0 — original 16 features (prior models)
- VERSION 2.0 — current 51 features

If a deployed model's `feature_count` doesn't match the current extractor output (51), the ranking engine automatically falls back to `"traditional"` mode (no crash).

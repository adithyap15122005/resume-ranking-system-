# AI-Powered Resume Ranking System

An end-to-end recruitment AI that automatically ranks resumes against a job description using TF-IDF, cosine similarity, spaCy NER, and a modular ML pipeline.

---

## Quick Start (New Machine)

Follow these steps exactly — takes about 5 minutes.

### Prerequisites
- Python **3.10, 3.11, or 3.12** (do NOT use 3.13/3.14 — incompatible with some packages)
- Git

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/resume-ranking-system.git
cd resume-ranking-system
```

### 2. Create and activate a virtual environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Download the NLP models (one-time setup)
```bash
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('punkt'); nltk.download('punkt_tab')"
```

### 5. Start the backend
```bash
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

Leave this terminal running.

### 6. Start the frontend (open a second terminal)
```bash
# Make sure the venv is activated in this terminal too
cd frontend/web
python -m http.server 3000
```

### 7. Open the app
Go to **http://localhost:3000** in your browser.

On first run, click **Upload Resumes → Sample Data → Generate Sample Data** to load demo resumes and job descriptions instantly.

---

## Project Structure

```
resume-ranking-system/
├── backend/
│   ├── app.py                  # FastAPI entry point
│   ├── config.py               # All settings (env-aware)
│   ├── database.py             # SQLAlchemy engine + session
│   ├── models/
│   │   ├── resume.py           # Resume ORM model
│   │   ├── job.py              # JobDescription ORM model
│   │   └── ranking.py         # RankingResult ORM model
│   ├── schemas/
│   │   ├── resume.py           # Pydantic request/response schemas
│   │   ├── job.py
│   │   └── ranking.py
│   ├── utils/
│   │   ├── resume_parser.py    # PDF/DOCX/TXT parser + NER extractor
│   │   ├── text_cleaner.py     # Lowercase, stopwords, lemmatisation
│   │   ├── preprocessing.py    # Full NLP pipeline (spaCy + NLTK)
│   │   ├── feature_extractor.py # TF-IDF with save/load
│   │   ├── similarity.py       # Abstract SimilarityEngine + TFIDFEngine + SBERTEngine
│   │   └── ranking_engine.py   # Ranking orchestration + metrics
│   └── api/
│       ├── upload.py           # Resume/Job upload endpoints
│       └── ranking.py          # Rank/Results/History/Evaluate endpoints
├── frontend/
│   ├── streamlit_app.py        # Multi-page Streamlit UI
│   └── components/
│       ├── charts.py           # Plotly chart builders
│       └── export.py           # CSV / Excel / PDF export
├── data/
│   ├── skills_db.py            # 400+ skills across all domains
│   ├── sample_generator.py     # 20 synthetic resumes + 5 job descriptions
│   └── dataset_loader.py       # Kaggle dataset loader + DB importer
├── uploads/
│   ├── resumes/                # Uploaded resume files
│   ├── jobs/                   # Uploaded job description files
│   └── dataset/                # Kaggle CSV goes here
├── trained/                    # Saved TF-IDF vectorizers
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .gitignore
```

---

## Installation

### 1. Clone / set up the project

```bash
cd resume-ranking-system
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Download spaCy model

```bash
python -m spacy download en_core_web_sm
```

### 4. Download NLTK data

```bash
python -c "import nltk; nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('punkt'); nltk.download('punkt_tab')"
```

---

## Running the Application

### Start the backend (FastAPI)

```bash
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### Start the frontend (Streamlit)

```bash
streamlit run frontend/streamlit_app.py
```

UI: http://localhost:8501

---

## Using the Kaggle Dataset

1. Download from: https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset
2. Place the CSV in `uploads/dataset/` (filename: `Resume.csv` or `UpdatedResumeDataSet.csv`)
3. Import via the API:

```bash
python -c "
from backend.database import SessionLocal, init_db
from data.dataset_loader import DatasetLoader
init_db()
db = SessionLocal()
loader = DatasetLoader()
n = loader.import_to_db(db)
print(f'Imported {n} resumes')
db.close()
"
```

Or use the **Load Sample Data** button in the Streamlit UI for synthetic data.

---

## REST API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload-resume` | Upload one or more resume files |
| POST | `/upload-job` | Upload job description (file or text) |
| GET | `/resumes` | List all stored resumes |
| GET | `/jobs` | List all stored job descriptions |
| GET | `/rank?job_id=1` | Run ranking for a job |
| GET | `/results?job_id=1` | Get stored ranking results |
| GET | `/history` | Ranking session history |
| GET | `/evaluate?job_id=1` | Classification metrics |
| DELETE | `/delete/{id}` | Delete a resume |
| DELETE | `/jobs/{id}` | Delete a job description |
| GET | `/health` | Health check |

---

## ML Pipeline

```
Resume File / Text
        ↓
ResumeParser (PyMuPDF → pdfplumber → python-docx)
        ↓
spaCy NER (PERSON, ORG, DATE entities)
        ↓
Regex extractors (email, phone, skills, certifications)
        ↓
TextCleaner (lowercase, remove URLs/punctuation, lemmatise, remove stopwords)
        ↓
TFIDFEngine.fit([job_desc] + [all_resumes])
        ↓
cosine_similarity(job_vec, resume_vecs)  →  scores [0, 1]
        ↓
RankingEngine.rank()  →  sorted RankingEntry list
        ↓
Recommendation label + skill gap analysis
```

---

## Swapping to SBERT (Future Upgrade)

No frontend or API changes needed. Just set the engine:

```bash
# Via environment variable
SIMILARITY_ENGINE=sbert uvicorn backend.app:app --reload

# Or per-request via the API
GET /rank?job_id=1&engine=sbert
```

Install the extra dependency:

```bash
pip install sentence-transformers
```

The `SBERTEngine` class in `backend/utils/similarity.py` implements the same `SimilarityEngine` interface as `TFIDFEngine` — this is the extensibility contract.

---

## Evaluation Metrics

The `/evaluate` endpoint computes (when ground-truth labels are available):

- Accuracy, Precision, Recall, F1-Score
- Confusion Matrix
- ROC-AUC

With the Kaggle dataset, each resume's category serves as its ground-truth label.

---

## Docker

```bash
# Build and start both services
docker-compose up --build

# Backend only
docker build -t resume-ranker .
docker run -p 8000:8000 resume-ranker
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend API | FastAPI + Uvicorn |
| Frontend | Streamlit |
| NLP | spaCy, NLTK |
| ML | scikit-learn (TF-IDF + cosine similarity) |
| Resume Parsing | PyMuPDF, pdfplumber, python-docx |
| Database | SQLite + SQLAlchemy |
| Visualisation | Plotly |
| Export | pandas, openpyxl, reportlab |
| Deployment | Docker, docker-compose |

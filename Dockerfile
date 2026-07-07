FROM python:3.12-slim

WORKDIR /app

# System dependencies for PyMuPDF + spaCy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Download NLTK data
RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('punkt'); nltk.download('punkt_tab')"

COPY . .

# Create upload directories
RUN mkdir -p uploads/resumes uploads/jobs uploads/dataset trained logs

EXPOSE 8000 8501

# Default: start FastAPI backend
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]

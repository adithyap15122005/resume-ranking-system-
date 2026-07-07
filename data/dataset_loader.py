"""
Kaggle dataset loader.

Expects the dataset from:
  https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset

Columns: ID | Resume_str | Resume_html | Category

Place the CSV at:  uploads/dataset/Resume.csv   (or UpdatedResumeDataSet.csv)

Usage
-----
    from data.dataset_loader import DatasetLoader
    loader = DatasetLoader()
    df = loader.load()
    loader.import_to_db(db_session)
"""
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.resume import Resume
from backend.utils.resume_parser import ResumeParser
from backend.utils.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)

_CANDIDATE_CSV_NAMES = [
    "Resume.csv",
    "UpdatedResumeDataSet.csv",
    "resume_dataset.csv",
    "resumes.csv",
]


class DatasetLoader:
    """Load the Kaggle resume dataset and (optionally) import it into SQLite."""

    def __init__(self) -> None:
        self._parser = ResumeParser()
        self._cleaner = TextCleaner()
        self._csv_path: Optional[Path] = self._find_csv()

    def _find_csv(self) -> Optional[Path]:
        for name in _CANDIDATE_CSV_NAMES:
            path = settings.DATASET_DIR / name
            if path.exists():
                logger.info("Dataset found: %s", path)
                return path
        logger.warning(
            "No dataset CSV found in %s. "
            "Download from Kaggle and place it there.",
            settings.DATASET_DIR,
        )
        return None

    def is_available(self) -> bool:
        return self._csv_path is not None

    def load(self, max_rows: Optional[int] = None) -> pd.DataFrame:
        """
        Load the dataset into a DataFrame.

        Returns a DataFrame with normalised columns:
            resume_text, category
        """
        if not self.is_available():
            raise FileNotFoundError(
                f"Dataset CSV not found in {settings.DATASET_DIR}. "
                "Download from https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset"
            )

        df = pd.read_csv(self._csv_path)
        logger.info("Loaded %d rows from %s", len(df), self._csv_path.name)

        # Normalise column names (the dataset has different spellings)
        col_map: dict[str, str] = {}
        for col in df.columns:
            lower = col.lower().replace(" ", "_")
            if "resume_str" in lower or "resume_text" in lower or lower == "resume":
                col_map[col] = "resume_text"
            elif "category" in lower:
                col_map[col] = "category"
            elif lower == "id":
                col_map[col] = "resume_id"
        df = df.rename(columns=col_map)

        required = {"resume_text", "category"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"CSV is missing expected columns: {missing}. "
                f"Found columns: {list(df.columns)}"
            )

        df = df.dropna(subset=["resume_text", "category"])
        df["resume_text"] = df["resume_text"].astype(str).str.strip()
        df = df[df["resume_text"].str.len() > 50]  # drop empty/garbage rows

        if max_rows:
            df = df.head(max_rows)

        logger.info("Dataset ready: %d resumes, %d categories", len(df), df["category"].nunique())
        return df.reset_index(drop=True)

    def get_categories(self) -> list[str]:
        df = self.load()
        return sorted(df["category"].unique().tolist())

    def import_to_db(
        self,
        db: Session,
        max_per_category: int = 10,
        overwrite: bool = False,
    ) -> int:
        """
        Parse each resume and insert into the resumes table.
        Returns the number of records inserted.
        """
        if overwrite:
            db.query(Resume).delete()
            db.commit()
            logger.info("Cleared existing resumes.")

        df = self.load()
        inserted = 0

        for _, row in df.iterrows():
            text = str(row["resume_text"])
            category = str(row["category"])
            filename = f"{category.replace(' ', '_').lower()}_{inserted}.txt"

            parsed = self._parser.parse_text(text, filename)

            # Skip duplicates by hash
            existing = db.query(Resume).filter(Resume.file_hash == parsed["file_hash"]).first()
            if existing:
                continue

            cleaned = self._cleaner.clean(text)

            resume = Resume(
                filename=filename,
                filepath="",
                file_hash=parsed["file_hash"],
                candidate_name=parsed.get("candidate_name"),
                email=parsed.get("email"),
                phone=parsed.get("phone"),
                skills=parsed.get("skills", []),
                education=parsed.get("education", []),
                experience=parsed.get("experience"),
                projects=parsed.get("projects", []),
                certifications=parsed.get("certifications", []),
                languages=parsed.get("languages", []),
                tools=parsed.get("tools", []),
                raw_text=text,
                cleaned_text=cleaned,
                experience_years=parsed.get("experience_years", 0.0),
                completeness_score=parsed.get("completeness_score", 0.0),
            )
            db.add(resume)
            inserted += 1

            if inserted % 50 == 0:
                db.commit()
                logger.info("Imported %d resumes so far…", inserted)

        db.commit()
        logger.info("Dataset import complete. Inserted %d resumes.", inserted)
        return inserted

    def build_job_descriptions(self) -> list[dict]:
        """
        Generate one representative job description per category.
        Used for automated evaluation and demo data.
        """
        df = self.load()
        jobs = []

        category_samples: dict[str, list[str]] = {}
        for _, row in df.iterrows():
            cat = str(row["category"])
            if cat not in category_samples:
                category_samples[cat] = []
            if len(category_samples[cat]) < 3:
                category_samples[cat].append(str(row["resume_text"])[:500])

        for category, samples in category_samples.items():
            combined = " ".join(samples)
            parsed = self._parser.parse_text(combined, f"{category}.txt")
            jobs.append({
                "title": category,
                "raw_text": combined,
                "required_skills": parsed.get("skills", [])[:20],
            })

        logger.info("Built %d job descriptions from dataset categories.", len(jobs))
        return jobs

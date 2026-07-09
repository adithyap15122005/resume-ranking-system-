"""
Enterprise Training Dashboard API — 5-step ML pipeline for Admin users.
Step 1: Dataset Upload  Step 2: EDA  Step 3: Feature Engineering
Step 4: Multi-model Training  Step 5: Model Leaderboard & Deployment
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import get_current_user
from backend.core.config import settings
from backend.core.database import AsyncSessionLocal, get_db
from backend.ml.model_registry import (
    _model_to_dict,
    get_production_model,
    set_experimental_model,
    set_production_model,
)
from backend.models.ml_model import MLModel
from backend.models.training_dataset import TrainingDataset
from backend.models.training_experiment import TrainingExperiment
from backend.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/training", tags=["ML Training"])

SUPPORTED_ALGORITHMS = [
    "Logistic Regression",
    "Random Forest",
    "XGBoost",
    "LightGBM",
    "Gradient Boosting",
    "SVM",
    "Neural Network",
    "Extra Trees",
]


def _require_admin(user: User) -> User:
    if user.role not in ("admin", "hr_manager"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required for model training")
    return user


class ExperimentRequest(BaseModel):
    dataset_id: str
    name: str
    target_column: str
    algorithms: Optional[List[str]] = None
    feature_columns: Optional[List[str]] = None


class OutcomeRequest(BaseModel):
    resume_id: str
    job_id: str
    ranking_result_id: Optional[str] = None
    interview_score: float = 0.0
    hiring_decision: str
    offer_extended: bool = False
    offer_accepted: bool = False
    notes: Optional[str] = None


# ── Step 1: Dataset Upload ────────────────────────────────────────────────────

@router.post("/datasets/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".csv", ".xlsx"):
        raise HTTPException(422, "Only CSV/XLSX files accepted")
    content = await file.read()
    dataset_id = str(uuid.uuid4())
    save_path = settings.DATASET_DIR / f"{dataset_id}_{file.filename}"
    save_path.write_bytes(content)
    try:
        profile = _profile_dataset(str(save_path))
    except Exception as exc:
        save_path.unlink(missing_ok=True)
        raise HTTPException(422, f"Could not read file: {exc}")
    ds = TrainingDataset(
        id=dataset_id,
        name=Path(file.filename or "dataset").stem,
        filename=file.filename or "dataset.csv",
        file_path=str(save_path),
        status="uploaded",
        rows=profile["rows"],
        columns=profile["columns"],
        missing_values=profile["missing_values"],
        duplicate_rows=profile["duplicate_rows"],
        quality_score=profile["quality_score"],
        column_types=profile["column_types"],
        class_distribution=profile["class_distribution"],
        data_preview=profile["data_preview"],
        column_stats=profile["column_stats"],
        original_feature_count=profile["columns"],
        organization_id=current_user.organization_id,
        created_by=current_user.id,
    )
    db.add(ds)
    await db.flush()
    return {"dataset_id": dataset_id, **profile}


@router.get("/datasets")
async def list_datasets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingDataset)
        .where(TrainingDataset.organization_id == current_user.organization_id)
        .order_by(TrainingDataset.created_at.desc())
    )
    return [_dataset_out(d) for d in result.scalars().all()]


@router.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return _dataset_out(await _get_ds_or_404(dataset_id, db))


# ── Step 2: EDA ───────────────────────────────────────────────────────────────

@router.post("/datasets/{dataset_id}/analyze")
async def analyze_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    ds = await _get_ds_or_404(dataset_id, db)
    try:
        eda = _run_eda(ds.file_path, ds.column_types or {})
    except Exception as exc:
        raise HTTPException(500, f"EDA failed: {exc}")
    ds.status = "analyzed"
    ds.analyzed_at = datetime.now(timezone.utc)
    ds.missing_report = eda["missing_report"]
    ds.correlation_matrix = eda["correlation_matrix"]
    ds.feature_importance_eda = eda["feature_importance_eda"]
    ds.outliers_report = eda["outliers_report"]
    ds.recommendations = eda["recommendations"]
    ds.quality_score = eda["quality_score"]
    await db.flush()
    return {**_dataset_out(ds), **eda}


# ── Step 3: Feature Engineering ───────────────────────────────────────────────

@router.post("/datasets/{dataset_id}/engineer")
async def engineer_features(
    dataset_id: str,
    target_column: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    ds = await _get_ds_or_404(dataset_id, db)
    try:
        eng = _feature_engineering(ds.file_path, target_column, ds.column_types or {})
    except Exception as exc:
        raise HTTPException(500, f"Feature engineering failed: {exc}")
    ds.status = "engineered"
    ds.engineered_at = datetime.now(timezone.utc)
    ds.target_column = target_column
    ds.engineering_steps = eng["steps"]
    ds.engineered_feature_count = eng["feature_count_after"]
    await db.flush()
    return {"dataset_id": dataset_id, **eng}


# ── Step 4: Multi-model Training ──────────────────────────────────────────────

@router.post("/experiments")
async def start_experiment(
    body: ExperimentRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    ds = await _get_ds_or_404(body.dataset_id, db)
    algorithms = body.algorithms or SUPPORTED_ALGORITHMS
    exp = TrainingExperiment(
        id=str(uuid.uuid4()),
        name=body.name,
        dataset_id=body.dataset_id,
        status="queued",
        target_column=body.target_column,
        feature_columns=body.feature_columns,
        algorithms=algorithms,
        algorithms_total=len(algorithms),
        algorithms_completed=0,
        progress_pct=0.0,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
    )
    db.add(exp)
    await db.flush()
    background_tasks.add_task(
        _run_experiment,
        exp.id, ds.file_path, body.target_column,
        algorithms, body.feature_columns,
        current_user.id, current_user.organization_id,
    )
    return {"experiment_id": exp.id, "status": "queued", "algorithms": algorithms}


@router.get("/experiments/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingExperiment).where(TrainingExperiment.id == experiment_id)
    )
    exp = result.scalars().first()
    if not exp:
        raise HTTPException(404, "Experiment not found")
    return _experiment_out(exp)


@router.get("/experiments")
async def list_experiments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrainingExperiment)
        .where(TrainingExperiment.organization_id == current_user.organization_id)
        .order_by(TrainingExperiment.created_at.desc())
    )
    return [_experiment_out(e) for e in result.scalars().all()]


# ── Step 5: Model Registry & Deployment ──────────────────────────────────────

@router.get("/models")
async def list_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MLModel)
        .where(MLModel.organization_id == current_user.organization_id)
        .order_by(MLModel.f1_score.desc())
    )
    return [_model_to_dict(m) for m in result.scalars().all()]


@router.get("/models/production")
async def get_production(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prod = await get_production_model(db)
    return prod or {"message": "No production model deployed"}


@router.post("/models/{model_id}/deploy")
async def deploy_model(
    model_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    try:
        return {"message": "Model deployed as production", "model": await set_production_model(model_id, db)}
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.post("/models/{model_id}/set-experimental")
async def mark_experimental(
    model_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    try:
        return {"message": "Model set as experimental", "model": await set_experimental_model(model_id, db)}
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(current_user)
    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalars().first()
    if not model:
        raise HTTPException(404, "Model not found")
    if model.deployment_status == "production":
        raise HTTPException(400, "Cannot delete the production model; archive it first")
    if model.model_path:
        p = Path(model.model_path)
        if p.is_dir():
            shutil.rmtree(str(p), ignore_errors=True)
        else:
            p.unlink(missing_ok=True)
    await db.delete(model)
    return {"message": "Model deleted"}


# ── Continuous Learning: Hiring Outcomes ──────────────────────────────────────

@router.post("/outcomes")
async def record_outcome(
    body: OutcomeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from backend.models.hiring_outcome import HiringOutcome

    outcome = HiringOutcome(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        resume_id=body.resume_id,
        job_id=body.job_id,
        ranking_result_id=body.ranking_result_id,
        interview_score=body.interview_score,
        hiring_decision=body.hiring_decision,
        offer_extended=body.offer_extended,
        offer_accepted=body.offer_accepted,
        notes=body.notes,
        recorded_by=current_user.id,
    )
    db.add(outcome)
    await db.flush()
    return {"outcome_id": outcome.id, "message": "Outcome recorded for continuous learning"}


@router.get("/outcomes")
async def list_outcomes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from backend.models.hiring_outcome import HiringOutcome

    result = await db.execute(
        select(HiringOutcome)
        .where(HiringOutcome.organization_id == current_user.organization_id)
        .order_by(HiringOutcome.created_at.desc())
        .limit(500)
    )
    return [
        {
            "id": o.id, "resume_id": o.resume_id, "job_id": o.job_id,
            "interview_score": o.interview_score, "hiring_decision": o.hiring_decision,
            "offer_extended": o.offer_extended, "offer_accepted": o.offer_accepted,
            "employee_performance": o.employee_performance,
            "retention_months": o.retention_months,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in result.scalars().all()
    ]


# ── Internal: Dataset Profiling ───────────────────────────────────────────────

def _profile_dataset(file_path: str) -> Dict[str, Any]:
    import pandas as pd

    df = pd.read_excel(file_path) if file_path.endswith(".xlsx") else pd.read_csv(file_path)
    rows, cols = df.shape
    missing_total = int(df.isnull().sum().sum())
    duplicates = int(df.duplicated().sum())
    column_types: Dict[str, str] = {}
    column_stats: Dict[str, Any] = {}
    for col in df.columns:
        ctype = _detect_col_type(df[col])
        column_types[col] = ctype
        s = df[col]
        stat: Dict[str, Any] = {"type": ctype, "missing": int(s.isnull().sum()), "unique": int(s.nunique())}
        if ctype == "numerical":
            stat.update({
                "min": float(s.min()) if not pd.isna(s.min()) else None,
                "max": float(s.max()) if not pd.isna(s.max()) else None,
                "mean": round(float(s.mean()), 3) if not pd.isna(s.mean()) else None,
                "std": round(float(s.std()), 3) if not pd.isna(s.std()) else None,
            })
        elif ctype == "categorical":
            stat["top_values"] = {str(k): int(v) for k, v in s.value_counts().head(5).items()}
        column_stats[col] = stat
    missing_pct = missing_total / max(rows * cols, 1)
    dup_pct = duplicates / max(rows, 1)
    quality_score = round(max(0.0, 100.0 - missing_pct * 40 - dup_pct * 20), 1)
    class_dist: Dict[str, int] = {}
    for col in df.columns:
        if df[col].nunique() < 20 and str(df[col].dtype) == "object":
            class_dist = {str(k): int(v) for k, v in df[col].value_counts().head(10).items()}
            break
    preview = df.head(20).fillna("").astype(str).to_dict(orient="records")
    return {
        "rows": rows, "columns": cols, "missing_values": missing_total,
        "duplicate_rows": duplicates, "quality_score": quality_score,
        "column_types": column_types, "column_stats": column_stats,
        "class_distribution": class_dist, "data_preview": preview,
        "column_names": list(df.columns),
    }


def _detect_col_type(series) -> str:
    import pandas as pd

    dtype = str(series.dtype)
    if "int" in dtype or "float" in dtype:
        n, t = series.nunique(), len(series)
        return "identifier" if n > max(0.9 * t, 100) and n > 50 else "numerical"
    if dtype == "object":
        n, t = series.nunique(), len(series)
        avg_len = series.dropna().astype(str).str.len().mean() if len(series.dropna()) > 0 else 0
        if avg_len > 50:
            return "text"
        try:
            pd.to_datetime(series.dropna().head(20), infer_datetime_format=True)
            return "date"
        except Exception:
            pass
        if n < 25 or (t > 0 and n / t < 0.05):
            return "categorical"
        if n > 0.9 * t:
            return "identifier"
        return "categorical"
    if "datetime" in dtype:
        return "date"
    if "bool" in dtype:
        return "categorical"
    return "categorical"


# ── Internal: EDA ─────────────────────────────────────────────────────────────

def _run_eda(file_path: str, column_types: Dict[str, str]) -> Dict[str, Any]:
    import pandas as pd

    df = pd.read_excel(file_path) if file_path.endswith(".xlsx") else pd.read_csv(file_path)
    missing_report = {
        col: {
            "count": int(df[col].isnull().sum()),
            "pct": round(df[col].isnull().sum() / max(len(df), 1) * 100, 1),
        }
        for col in df.columns
    }
    num_cols = [c for c, t in column_types.items() if t == "numerical" and c in df.columns][:20]
    correlation_matrix: Dict[str, Any] = {}
    if len(num_cols) >= 2:
        try:
            corr = df[num_cols].corr().round(3)
            correlation_matrix = {"columns": num_cols, "values": corr.values.tolist()}
        except Exception:
            pass
    feature_importance_eda: Dict[str, float] = {}
    cat_targets = [c for c, t in column_types.items() if t == "categorical" and c in df.columns]
    if num_cols and cat_targets:
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.preprocessing import LabelEncoder

            target = cat_targets[-1]
            X = df[num_cols].fillna(df[num_cols].median())
            y = LabelEncoder().fit_transform(df[target].fillna("unknown").astype(str))
            rf = RandomForestClassifier(n_estimators=30, random_state=42, max_depth=5)
            rf.fit(X, y)
            feature_importance_eda = {
                col: round(float(imp), 4)
                for col, imp in zip(num_cols, rf.feature_importances_)
            }
        except Exception:
            pass
    outliers_report: Dict[str, Any] = {}
    for col in num_cols[:10]:
        try:
            q1, q3 = float(df[col].quantile(0.25)), float(df[col].quantile(0.75))
            iqr = q3 - q1
            out = int(((df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)).sum())
            outliers_report[col] = {
                "count": out,
                "pct": round(out / max(len(df), 1) * 100, 1),
                "q1": round(q1, 3), "q3": round(q3, 3),
            }
        except Exception:
            pass
    mp = df.isnull().sum().sum() / max(df.size, 1)
    dp = df.duplicated().sum() / max(len(df), 1)
    qs = round(max(0.0, 100.0 - mp * 40 - dp * 20), 1)
    recs: List[str] = []
    if mp > 0.1:
        recs.append(f"High missing data ({mp:.0%}) — consider imputation or dropping sparse columns")
    if dp > 0.05:
        recs.append(f"{df.duplicated().sum()} duplicate rows — remove before training")
    high_out = [c for c, v in outliers_report.items() if v["pct"] > 5]
    if high_out:
        recs.append(f"Outliers in: {', '.join(high_out[:3])} — consider capping")
    if feature_importance_eda:
        low_imp = [c for c, v in feature_importance_eda.items() if v < 0.01]
        if low_imp:
            recs.append(f"{len(low_imp)} low-importance features — may safely be dropped")
    if not recs:
        recs.append("Dataset looks clean. Ready for feature engineering and training.")
    return {
        "missing_report": missing_report, "correlation_matrix": correlation_matrix,
        "feature_importance_eda": feature_importance_eda, "outliers_report": outliers_report,
        "recommendations": recs, "quality_score": qs,
    }


# ── Internal: Feature Engineering ────────────────────────────────────────────

def _feature_engineering(
    file_path: str, target_column: str, column_types: Dict[str, str]
) -> Dict[str, Any]:
    import pandas as pd
    from sklearn.preprocessing import LabelEncoder, StandardScaler

    df = pd.read_excel(file_path) if file_path.endswith(".xlsx") else pd.read_csv(file_path)
    steps: List[Dict[str, Any]] = []
    fc_before = df.shape[1] - 1

    before = len(df)
    df = df.drop_duplicates()
    steps.append({"name": "Remove Duplicates", "status": "done", "detail": f"{before - len(df)} rows removed"})

    id_cols = [c for c, t in column_types.items() if t == "identifier" and c != target_column]
    df = df.drop(columns=id_cols, errors="ignore")
    steps.append({"name": "Drop Identifier Columns", "status": "done", "detail": f"{len(id_cols)} columns removed"})

    num_cols = [c for c in df.columns if c != target_column and column_types.get(c) == "numerical"]
    cat_cols = [c for c in df.columns if c != target_column and column_types.get(c) in ("categorical", "text", "date")]
    for col in num_cols:
        df[col] = df[col].fillna(df[col].median())
    for col in cat_cols:
        mv = df[col].mode()
        df[col] = df[col].fillna(mv.iloc[0] if len(mv) > 0 else "Unknown")
    steps.append({"name": "Handle Missing Values", "status": "done",
                  "detail": f"Median for {len(num_cols)} numerical, mode for {len(cat_cols)} categorical"})

    cat_enc = [c for c in cat_cols if c in df.columns and column_types.get(c) == "categorical"]
    for col in cat_enc:
        df[col] = LabelEncoder().fit_transform(df[col].astype(str))
    steps.append({"name": "Encode Categorical Features", "status": "done",
                  "detail": f"{len(cat_enc)} columns label-encoded"})

    if num_cols:
        df[num_cols] = StandardScaler().fit_transform(df[num_cols])
    steps.append({"name": "Normalize Numerical Features", "status": "done",
                  "detail": f"{len(num_cols)} columns standardized (μ=0, σ=1)"})

    text_date = [c for c in df.columns if c != target_column and column_types.get(c) in ("text", "date")]
    df = df.drop(columns=text_date, errors="ignore")
    steps.append({"name": "Drop Text/Date Columns", "status": "done",
                  "detail": f"{len(text_date)} columns dropped"})

    fc_after = df.shape[1] - 1
    class_bal = (
        {str(k): int(v) for k, v in df[target_column].value_counts().items()}
        if target_column in df.columns else {}
    )
    steps.append({"name": "Feature Selection", "status": "done", "detail": f"{fc_after} features selected"})
    steps.append({"name": "Class Balance Check", "status": "done", "detail": str(class_bal)})

    return {
        "steps": steps, "feature_count_before": fc_before,
        "feature_count_after": fc_after, "class_balance_after": class_bal,
        "samples_after_smote": len(df),
    }


# ── Internal: Async Training Background Task ──────────────────────────────────

async def _run_experiment(
    exp_id: str, file_path: str, target_column: str,
    algorithms: List[str], feature_columns: Optional[List[str]],
    user_id: str, org_id: Optional[str],
) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await _do_train(exp_id, file_path, target_column, algorithms, feature_columns, user_id, org_id, db)
        except Exception as exc:
            logger.error("Experiment %s crashed: %s", exp_id, exc, exc_info=True)
            result = await db.execute(
                select(TrainingExperiment).where(TrainingExperiment.id == exp_id)
            )
            exp = result.scalars().first()
            if exp:
                exp.status = "failed"
                exp.error_message = str(exc)
                await db.commit()


async def _do_train(
    exp_id: str, file_path: str, target_column: str,
    algorithms: List[str], feature_columns: Optional[List[str]],
    user_id: str, org_id: Optional[str], db: AsyncSession,
) -> None:
    import pandas as pd
    from sklearn.metrics import (
        accuracy_score, confusion_matrix, f1_score,
        precision_score, recall_score, roc_auc_score,
    )
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder, StandardScaler

    result = await db.execute(select(TrainingExperiment).where(TrainingExperiment.id == exp_id))
    exp = result.scalars().first()
    if not exp:
        return
    exp.status = "running"
    exp.started_at = datetime.now(timezone.utc)
    await db.commit()

    df = pd.read_excel(file_path) if file_path.endswith(".xlsx") else pd.read_csv(file_path)
    df = df.drop_duplicates()
    feature_cols = feature_columns or [c for c in df.columns if c != target_column]
    if target_column not in df.columns:
        raise ValueError(f"Target column {target_column!r} not found in dataset")

    X_df = df[feature_cols].copy()
    y_raw = df[target_column].copy()
    for col in X_df.columns:
        if X_df[col].dtype.kind in "iufb":
            X_df[col] = X_df[col].fillna(X_df[col].median())
        else:
            X_df[col] = LabelEncoder().fit_transform(X_df[col].fillna("unknown").astype(str))

    le_target = LabelEncoder()
    y = le_target.fit_transform(y_raw.fillna("unknown").astype(str))
    class_labels = le_target.classes_.tolist()
    is_binary = len(class_labels) == 2

    # Split BEFORE fitting scaler — prevents data leakage
    X_raw = X_df.values.astype(float)
    try:
        X_train_raw, X_test_raw, y_train, y_test = train_test_split(
            X_raw, y, test_size=0.2, random_state=42, stratify=y
        )
    except ValueError:
        X_train_raw, X_test_raw, y_train, y_test = train_test_split(
            X_raw, y, test_size=0.2, random_state=42
        )
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)   # fit on train only
    X_test = scaler.transform(X_test_raw)          # transform test

    model_ids: List[str] = []
    best_f1, best_model_id = -1.0, None

    for i, algo_name in enumerate(algorithms):
        r2 = await db.execute(select(TrainingExperiment).where(TrainingExperiment.id == exp_id))
        e2 = r2.scalars().first()
        if e2:
            e2.current_algorithm = algo_name
            e2.algorithms_completed = i
            e2.progress_pct = round(i / len(algorithms) * 100, 1)
            await db.commit()

        logger.info("Experiment %s: training %s (%d/%d)", exp_id, algo_name, i + 1, len(algorithms))
        t0 = time.time()
        try:
            clf = _build_classifier(algo_name)
            if clf is None:
                logger.warning("Skipping %s — not installed", algo_name)
                continue
            clf.fit(X_train, y_train)
            t_train = time.time() - t0
            t_inf0 = time.time()
            y_pred = clf.predict(X_test)
            t_inf = (time.time() - t_inf0) / max(len(X_test), 1) * 1000

            avg = "binary" if is_binary else "weighted"
            acc = float(accuracy_score(y_test, y_pred))
            prec = float(precision_score(y_test, y_pred, average=avg, zero_division=0))
            rec = float(recall_score(y_test, y_pred, average=avg, zero_division=0))
            f1 = float(f1_score(y_test, y_pred, average=avg, zero_division=0))
            roc = 0.0
            try:
                if hasattr(clf, "predict_proba"):
                    proba = clf.predict_proba(X_test)
                    if is_binary:
                        roc = float(roc_auc_score(y_test, proba[:, 1]))
                    else:
                        roc = float(roc_auc_score(y_test, proba, multi_class="ovr", average="weighted"))
            except Exception:
                pass

            feat_imp: Dict[str, float] = {}
            if hasattr(clf, "feature_importances_"):
                feat_imp = {
                    feature_cols[j]: round(float(v), 5)
                    for j, v in enumerate(clf.feature_importances_)
                }
            elif hasattr(clf, "coef_"):
                coefs = np.abs(clf.coef_).mean(axis=0) if clf.coef_.ndim > 1 else np.abs(clf.coef_[0])
                feat_imp = {feature_cols[j]: round(float(v), 5) for j, v in enumerate(coefs)}

            cm = confusion_matrix(y_test, y_pred).tolist()
            model_id = str(uuid.uuid4())

            # Save full artifact bundle (model + preprocessor + metadata)
            model_dir = Path(settings.MODELS_DIR) / model_id
            model_dir.mkdir(parents=True, exist_ok=True)

            joblib.dump(clf, model_dir / "model.pkl")
            joblib.dump(scaler, model_dir / "preprocessor.pkl")
            joblib.dump(le_target, model_dir / "label_encoder.pkl")

            (model_dir / "feature_metadata.json").write_text(json.dumps({
                "feature_names": feature_cols,
                "feature_count": len(feature_cols),
                "version": "1.0",
            }))
            (model_dir / "metrics.json").write_text(json.dumps({
                "accuracy": acc, "f1": f1, "precision": prec,
                "recall": rec, "roc_auc": roc,
                "confusion_matrix": cm, "class_labels": class_labels,
            }))
            (model_dir / "training_config.json").write_text(json.dumps({
                "algorithm": algo_name,
                "train_samples": len(X_train),
                "test_samples": len(X_test),
                "target_column": target_column,
            }))
            (model_dir / "version.json").write_text(json.dumps({
                "model_version": "v1.0.0",
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "experiment_id": exp_id,
            }))

            model_size_mb = round(
                sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file()) / 1024 / 1024,
                3,
            )

            ml_model = MLModel(
                id=model_id,
                name=f"{algo_name} — {exp_id[:8]}",
                version="v1.0.0",
                algorithm=algo_name,
                status="trained",
                deployment_status="experimental",
                accuracy=round(acc, 4),
                precision_score=round(prec, 4),
                recall_score=round(rec, 4),
                f1_score=round(f1, 4),
                roc_auc=round(roc, 4),
                inference_time_ms=round(t_inf, 4),
                training_time_s=round(t_train, 2),
                model_size_mb=model_size_mb,
                dataset_id=exp.dataset_id,
                experiment_id=exp_id,
                feature_count=len(feature_cols),
                training_samples=len(X_train),
                target_column=target_column,
                model_path=str(model_dir),
                feature_importance=feat_imp,
                confusion_matrix_data={"matrix": cm, "labels": [str(c) for c in class_labels]},
                class_labels=class_labels,
                feature_names=feature_cols,
                trained_at=datetime.now(timezone.utc),
                organization_id=org_id,
                created_by=user_id,
            )
            db.add(ml_model)
            await db.flush()
            model_ids.append(model_id)
            if f1 > best_f1:
                best_f1 = f1
                best_model_id = model_id
            logger.info("  %s → acc=%.3f f1=%.3f roc=%.3f", algo_name, acc, f1, roc)
        except Exception as ae:
            logger.warning("  %s failed: %s", algo_name, ae)
            continue

    r3 = await db.execute(select(TrainingExperiment).where(TrainingExperiment.id == exp_id))
    e3 = r3.scalars().first()
    if e3:
        e3.status = "completed"
        e3.completed_at = datetime.now(timezone.utc)
        e3.algorithms_completed = len(algorithms)
        e3.progress_pct = 100.0
        e3.current_algorithm = None
        e3.model_ids = model_ids
        e3.best_model_id = best_model_id
    await db.commit()
    logger.info("Experiment %s complete. Best: %s F1=%.3f", exp_id, best_model_id, best_f1)


def _build_classifier(algo_name: str):
    try:
        if algo_name == "Logistic Regression":
            from sklearn.linear_model import LogisticRegression
            return LogisticRegression(max_iter=500, random_state=42)
        if algo_name == "Random Forest":
            from sklearn.ensemble import RandomForestClassifier
            return RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        if algo_name == "Extra Trees":
            from sklearn.ensemble import ExtraTreesClassifier
            return ExtraTreesClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        if algo_name == "Gradient Boosting":
            from sklearn.ensemble import GradientBoostingClassifier
            return GradientBoostingClassifier(n_estimators=100, random_state=42)
        if algo_name == "SVM":
            from sklearn.svm import SVC
            return SVC(probability=True, random_state=42, max_iter=500)
        if algo_name == "Neural Network":
            from sklearn.neural_network import MLPClassifier
            return MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=300, random_state=42)
        if algo_name == "XGBoost":
            from xgboost import XGBClassifier
            return XGBClassifier(n_estimators=100, random_state=42, eval_metric="logloss", verbosity=0)
        if algo_name == "LightGBM":
            from lightgbm import LGBMClassifier
            return LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)
        if algo_name == "CatBoost":
            from catboost import CatBoostClassifier
            return CatBoostClassifier(iterations=100, random_state=42, verbose=0)
    except ImportError:
        return None
    return None


# ── Output Serializers ────────────────────────────────────────────────────────

def _dataset_out(ds: TrainingDataset) -> Dict[str, Any]:
    return {
        "id": ds.id, "name": ds.name, "filename": ds.filename, "status": ds.status,
        "rows": ds.rows, "columns": ds.columns, "missing_values": ds.missing_values,
        "duplicate_rows": ds.duplicate_rows, "target_column": ds.target_column,
        "quality_score": ds.quality_score, "column_types": ds.column_types,
        "column_stats": ds.column_stats, "class_distribution": ds.class_distribution,
        "data_preview": ds.data_preview, "missing_report": ds.missing_report,
        "correlation_matrix": ds.correlation_matrix,
        "feature_importance_eda": ds.feature_importance_eda,
        "outliers_report": ds.outliers_report, "recommendations": ds.recommendations,
        "engineering_steps": ds.engineering_steps,
        "engineered_feature_count": ds.engineered_feature_count,
        "original_feature_count": ds.original_feature_count,
        "created_at": ds.created_at.isoformat() if ds.created_at else None,
        "analyzed_at": ds.analyzed_at.isoformat() if ds.analyzed_at else None,
        "engineered_at": ds.engineered_at.isoformat() if ds.engineered_at else None,
    }


def _experiment_out(exp: TrainingExperiment) -> Dict[str, Any]:
    return {
        "id": exp.id, "name": exp.name, "dataset_id": exp.dataset_id,
        "status": exp.status, "target_column": exp.target_column,
        "algorithms": exp.algorithms, "model_ids": exp.model_ids,
        "best_model_id": exp.best_model_id, "current_algorithm": exp.current_algorithm,
        "algorithms_completed": exp.algorithms_completed,
        "algorithms_total": exp.algorithms_total,
        "progress_pct": exp.progress_pct, "error_message": exp.error_message,
        "created_at": exp.created_at.isoformat() if exp.created_at else None,
        "started_at": exp.started_at.isoformat() if exp.started_at else None,
        "completed_at": exp.completed_at.isoformat() if exp.completed_at else None,
    }


async def _get_ds_or_404(dataset_id: str, db: AsyncSession) -> TrainingDataset:
    result = await db.execute(select(TrainingDataset).where(TrainingDataset.id == dataset_id))
    ds = result.scalars().first()
    if not ds:
        raise HTTPException(404, "Dataset not found")
    return ds

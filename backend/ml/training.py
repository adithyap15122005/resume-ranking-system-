"""
Dataset training pipeline supporting Kaggle CSV datasets.
Runs AutoML-style multi-model comparison, feature engineering,
and returns a leaderboard with the best model highlighted.
"""
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

logger = logging.getLogger(__name__)


class DatasetTrainingPipeline:
    """End-to-end training pipeline for Kaggle-style hiring datasets."""

    def __init__(self, output_dir: Path = Path("trained")):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.scaler = StandardScaler()
        self.models: Dict[str, Any] = {}
        self.metrics: Dict[str, Dict] = {}
        self.best_model_name: str = ""
        self.feature_names: List[str] = []
        self._df: Optional[pd.DataFrame] = None

    # ── Loading ───────────────────────────────────────────────────────────────

    def load_dataset(self, path: str) -> pd.DataFrame:
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                df = pd.read_csv(path, encoding=enc)
                logger.info("Loaded dataset %s: %s", path, df.shape)
                self._df = df
                return df
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Cannot read dataset (tried utf-8, latin-1, cp1252): {path}")

    # ── EDA ───────────────────────────────────────────────────────────────────

    def analyze_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        analysis: Dict[str, Any] = {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "column_names": df.columns.tolist(),
            "dtypes": df.dtypes.astype(str).to_dict(),
            "missing_values": df.isnull().sum().to_dict(),
            "missing_pct": (df.isnull().mean() * 100).round(2).to_dict(),
            "total_missing": int(df.isnull().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum()),
            "numeric_stats": {},
            "category_counts": {},
        }
        num_df = df.select_dtypes(include=np.number)
        if not num_df.empty:
            analysis["numeric_stats"] = (
                num_df.describe().round(3).to_dict()
            )
        for col in df.select_dtypes(include="object").columns:
            if df[col].nunique() <= 30:
                analysis["category_counts"][col] = df[col].value_counts().head(20).to_dict()
        return analysis

    # ── Cleaning ──────────────────────────────────────────────────────────────

    def clean_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        original = df.shape
        # Drop columns >70% missing
        df = df.dropna(thresh=int(0.3 * len(df)), axis=1)
        df = df.drop_duplicates()
        for col in df.select_dtypes(include=np.number).columns:
            df[col] = df[col].fillna(df[col].median())
        for col in df.select_dtypes(include="object").columns:
            mode = df[col].mode()
            df[col] = df[col].fillna(mode.iloc[0] if not mode.empty else "Unknown")
        logger.info("Dataset cleaned: %s -> %s", original, df.shape)
        return df

    # ── Feature Engineering ───────────────────────────────────────────────────

    def prepare_features(
        self,
        df: pd.DataFrame,
        target_col: str,
        drop_cols: Optional[List[str]] = None,
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        drop_cols = drop_cols or []
        y_raw = df[target_col]
        df_feat = df.drop(columns=[target_col] + drop_cols, errors="ignore")

        parts: List[pd.Series] = []
        names: List[str] = []

        for col in df_feat.columns:
            dtype = df_feat[col].dtype
            if dtype == "object":
                n_unique = df_feat[col].nunique()
                if n_unique <= 20:
                    dummies = pd.get_dummies(df_feat[col], prefix=col, dtype=float)
                    parts.extend(dummies[c] for c in dummies.columns)
                    names.extend(dummies.columns.tolist())
                else:
                    le = LabelEncoder()
                    encoded = le.fit_transform(df_feat[col].astype(str)).astype(float)
                    parts.append(pd.Series(encoded, name=col))
                    names.append(col)
                    self.label_encoders[col] = le
            elif np.issubdtype(dtype, np.number):
                parts.append(df_feat[col].astype(float))
                names.append(col)

        if parts:
            X = np.column_stack([s.values for s in parts]).astype(np.float32)
        else:
            X = np.zeros((len(df), 1), dtype=np.float32)

        if y_raw.dtype == "object":
            le_t = LabelEncoder()
            y = le_t.fit_transform(y_raw.astype(str)).astype(np.int32)
            self.label_encoders["__target__"] = le_t
        else:
            y = y_raw.values.astype(np.int32)

        self.feature_names = names
        return X, y, names

    # ── Training ──────────────────────────────────────────────────────────────

    def train_all_models(
        self, X: np.ndarray, y: np.ndarray
    ) -> Dict[str, Dict[str, Any]]:
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
        X_tr_s = self.scaler.fit_transform(X_tr)
        X_te_s = self.scaler.transform(X_te)

        n_classes = len(np.unique(y))
        avg = "binary" if n_classes == 2 else "weighted"

        configs: List[Tuple[str, Any, bool]] = [
            ("Random Forest", RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1), False),
            ("Gradient Boosting", GradientBoostingClassifier(n_estimators=100, random_state=42), False),
            ("Logistic Regression", LogisticRegression(max_iter=1000, random_state=42), True),
        ]

        # Optional heavy models
        try:
            import xgboost as xgb
            configs.insert(0, ("XGBoost", xgb.XGBClassifier(
                n_estimators=200, max_depth=6, learning_rate=0.1, random_state=42,
                verbosity=0, eval_metric="logloss"
            ), False))
        except ImportError:
            pass

        try:
            import lightgbm as lgb
            configs.insert(1, ("LightGBM", lgb.LGBMClassifier(
                n_estimators=200, learning_rate=0.1, random_state=42, verbose=-1
            ), False))
        except ImportError:
            pass

        leaderboard: Dict[str, Dict] = {}

        for name, model, use_scaled in configs:
            X_fit = X_tr_s if use_scaled else X_tr
            X_eval = X_te_s if use_scaled else X_te
            t0 = time.time()
            try:
                model.fit(X_fit, y_tr)
                y_pred = model.predict(X_eval)
                y_prob = model.predict_proba(X_eval)[:, 1] if n_classes == 2 else np.zeros(len(y_te))
                elapsed = time.time() - t0

                m: Dict[str, Any] = {
                    "accuracy": round(float(accuracy_score(y_te, y_pred)), 4),
                    "f1": round(float(f1_score(y_te, y_pred, average=avg, zero_division=0)), 4),
                    "precision": round(float(precision_score(y_te, y_pred, average=avg, zero_division=0)), 4),
                    "recall": round(float(recall_score(y_te, y_pred, average=avg, zero_division=0)), 4),
                    "training_time_s": round(elapsed, 2),
                }
                if n_classes == 2:
                    m["roc_auc"] = round(float(roc_auc_score(y_te, y_prob)), 4)
                if hasattr(model, "feature_importances_") and self.feature_names:
                    imp = model.feature_importances_
                    m["feature_importance"] = dict(
                        sorted(zip(self.feature_names, imp.tolist()), key=lambda x: x[1], reverse=True)[:15]
                    )

                self.models[name] = model
                leaderboard[name] = m
                logger.info("%s: acc=%.4f f1=%.4f time=%.1fs", name, m["accuracy"], m["f1"], elapsed)
            except Exception as exc:
                logger.error("Failed to train %s: %s", name, exc)
                leaderboard[name] = {"error": str(exc)}

        self.metrics = leaderboard
        valid = {k: v for k, v in leaderboard.items() if "f1" in v}
        if valid:
            self.best_model_name = max(valid, key=lambda k: valid[k]["f1"])

        return leaderboard

    # ── Save ─────────────────────────────────────────────────────────────────

    def save_best_model(self) -> Optional[Path]:
        if not self.best_model_name or self.best_model_name not in self.models:
            return None
        model = self.models[self.best_model_name]
        save_path = self.output_dir / "best_model.joblib"
        joblib.dump(model, save_path)
        joblib.dump(self.scaler, self.output_dir / "scaler.joblib")
        meta = {
            "model_name": self.best_model_name,
            "metrics": self.metrics.get(self.best_model_name, {}),
            "feature_names": self.feature_names,
        }
        (self.output_dir / "model_meta.json").write_text(json.dumps(meta, indent=2))
        logger.info("Best model saved: %s -> %s", self.best_model_name, save_path)
        return save_path

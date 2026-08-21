"""
model.py

Singleton model loader for the Virality Forensics prediction pipeline.

The scikit-learn Pipeline (imputer → scaler → LogisticRegression) is loaded
once at application startup via the FastAPI lifespan event and reused across
all requests.  Feature ordering is enforced from features.json so callers
do not need to worry about column order.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

log = logging.getLogger("virality.model")

MODEL_PATH    = Path("model/final_logistic_regression_15min.joblib")
FEATURES_PATH = Path("model/features.json")

# Prediction thresholds
THRESHOLD_DEFAULT    = 0.50
THRESHOLD_F1_OPTIMAL = 0.778


class ViralityModel:
    """
    Wraps the trained sklearn Pipeline and exposes predict_one / predict_batch.

    The pipeline handles:
      - Median imputation of missing features
      - StandardScaler
      - Logistic Regression (balanced class weight, C=1.0)

    All input dicts may have None values for any feature; the imputer will
    substitute the training-set median for that feature.
    """

    def __init__(self) -> None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model file not found: {MODEL_PATH}. "
                "Run the notebook to produce model/final_logistic_regression_15min.joblib."
            )
        if not FEATURES_PATH.exists():
            raise FileNotFoundError(f"Feature list not found: {FEATURES_PATH}.")

        self.pipeline = joblib.load(MODEL_PATH)
        # Compatibility patch for unpickling estimators across sklearn versions
        if hasattr(self.pipeline, "named_steps"):
            for step in self.pipeline.named_steps.values():
                if not hasattr(step, "_fill_dtype"):
                    if hasattr(step, "_fit_dtype"):
                        step._fill_dtype = step._fit_dtype
                    elif hasattr(step, "statistics_"):
                        step._fill_dtype = getattr(step.statistics_, "dtype", np.float64)

        with open(FEATURES_PATH) as f:
            self.feature_cols: list[str] = json.load(f)

        log.info(
            "ViralityModel loaded: %s | features: %s",
            MODEL_PATH,
            self.feature_cols,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_dataframe(self, features_dicts: list[dict[str, Any]]) -> pd.DataFrame:
        """Convert a list of feature dicts to a DataFrame in the correct column order."""
        return pd.DataFrame(features_dicts, columns=self.feature_cols)

    def _score(self, df: pd.DataFrame) -> np.ndarray:
        """Return P(label=1) for each row."""
        return self.pipeline.predict_proba(df)[:, 1]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def predict_one(self, features: dict[str, Any]) -> dict[str, Any]:
        """Score a single story. Returns a dict ready to unpack into PredictionResponse."""
        df = self._to_dataframe([features])
        p = float(self._score(df)[0])
        return {
            "p_viral": round(p, 6),
            "prediction_default":    p >= THRESHOLD_DEFAULT,
            "prediction_f1_optimal": p >= THRESHOLD_F1_OPTIMAL,
        }

    def predict_batch(
        self, rows: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Score a batch of stories. Returns a list of dicts."""
        df = self._to_dataframe(rows)
        probs = self._score(df)
        return [
            {
                "p_viral": round(float(p), 6),
                "prediction_default":    float(p) >= THRESHOLD_DEFAULT,
                "prediction_f1_optimal": float(p) >= THRESHOLD_F1_OPTIMAL,
            }
            for p in probs
        ]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_model_instance: ViralityModel | None = None


def load_model() -> None:
    """Load the model at startup. Called from the FastAPI lifespan handler."""
    global _model_instance
    _model_instance = ViralityModel()


def get_model() -> ViralityModel:
    """FastAPI dependency — returns the loaded model singleton."""
    if _model_instance is None:
        # Should not happen if lifespan is wired correctly, but guard anyway
        load_model()
    return _model_instance  # type: ignore[return-value]

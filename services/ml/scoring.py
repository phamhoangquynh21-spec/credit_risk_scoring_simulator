"""Thin scoring layer over the existing src/ ML code. No model logic is
re-implemented here — it reuses the tested pipeline."""
from __future__ import annotations

import functools

import joblib
import pandas as pd

from src import config
from src.explain import explain_in_plain_language, score_batch


@functools.lru_cache(maxsize=1)
def load_bundle() -> dict:
    return joblib.load(config.MODEL_PATH)


def _features() -> list[str]:
    return load_bundle()["features"]


FEATURES = None  # populated lazily via _features(); kept for import symmetry


def score_one(raw_row: dict) -> dict:
    """Score one applicant given a dict of RAW UCI column names."""
    bundle = load_bundle()
    scored = score_batch(bundle["model"], bundle["features"],
                         pd.DataFrame([raw_row]))
    row = scored.iloc[0]
    prob = float(row["risk_score"]) / 100.0
    return {
        "probability": prob,
        "risk_score": float(row["risk_score"]),
        "risk_band": str(row["risk_band"]),
        "model_type": bundle["model_type"],
    }


def explain_one(raw_row: dict) -> list[dict]:
    """Plain-language SHAP top factors for one applicant."""
    from src.preprocessing import clean_data, engineer_features

    bundle = load_bundle()
    feat_df = engineer_features(clean_data(pd.DataFrame([raw_row])))
    single = feat_df[bundle["features"]].iloc[0]
    items = explain_in_plain_language(bundle["model"], single)
    return [{"feature": i["feature"], "friendly": i["friendly"],
             "contribution": float(i["contribution"]), "direction": i["direction"]}
            for i in items]

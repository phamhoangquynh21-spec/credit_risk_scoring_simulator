"""Model training, evaluation and serialisation.

Implements Technical_Spec.md section 5. Two models:
  * baseline  : Logistic Regression (scaled, class_weight='balanced')
  * advanced  : XGBoost if available, else RandomForest — both tree models are
                left unscaled so shap.TreeExplainer can consume them directly.

Running this module as a script performs the full pipeline and writes
``models/model.pkl`` (a bundle dict) and ``models/metrics.json``.
"""

from __future__ import annotations

import json

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from . import config


def train_baseline(X_train, y_train) -> Pipeline:
    """Logistic Regression with class_weight='balanced'. Returns fitted pipeline."""
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=42,
        )),
    ])
    pipe.fit(X_train, y_train)
    return pipe


def _xgboost_available() -> bool:
    try:
        import xgboost  # noqa: F401
        return True
    except Exception:
        return False


def train_advanced(X_train, y_train, model_type: str = "xgboost"):
    """Train RandomForest or XGBoost with light cross-validated tuning.

    Falls back to RandomForest if xgboost is requested but not installed.
    Returns the fitted best estimator (unscaled, tree-based).
    """
    if model_type == "xgboost" and not _xgboost_available():
        model_type = "randomforest"

    # Class imbalance handling differs per library.
    neg, pos = int((y_train == 0).sum()), int((y_train == 1).sum())
    scale_pos_weight = neg / max(pos, 1)

    if model_type == "xgboost":
        from xgboost import XGBClassifier

        estimator = XGBClassifier(
            objective="binary:logistic",
            eval_metric="auc",
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            n_jobs=-1,
            tree_method="hist",
        )
        param_grid = {
            "n_estimators": [200, 400],
            "max_depth": [3, 4],
            "learning_rate": [0.05, 0.1],
            "subsample": [0.9],
        }
    else:
        estimator = RandomForestClassifier(
            class_weight="balanced", random_state=42, n_jobs=-1,
        )
        param_grid = {
            "n_estimators": [300],
            "max_depth": [8, 12],
            "min_samples_leaf": [20, 50],
        }

    search = GridSearchCV(
        estimator, param_grid, scoring="roc_auc", cv=3, n_jobs=-1,
    )
    search.fit(X_train, y_train)
    best = search.best_estimator_
    best.model_type_ = model_type  # tag for downstream (explain/dashboard)
    best.cv_best_auc_ = float(search.best_score_)
    best.cv_best_params_ = search.best_params_
    return best


def evaluate_model(model, X_test, y_test) -> dict:
    """Return auc_roc, precision, recall, f1, accuracy and confusion_matrix."""
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    cm = confusion_matrix(y_test, pred)
    return {
        "auc_roc": float(roc_auc_score(y_test, proba)),
        "precision": float(precision_score(y_test, pred, zero_division=0)),
        "recall": float(recall_score(y_test, pred, zero_division=0)),
        "f1": float(f1_score(y_test, pred, zero_division=0)),
        "accuracy": float((pred == y_test).mean()),
        "confusion_matrix": cm.tolist(),  # [[TN, FP], [FN, TP]]
    }


def save_model(model, path: str | None = None) -> None:
    """Serialise ``model`` to models/model.pkl using joblib."""
    path = str(path) if path is not None else str(config.MODEL_PATH)
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


# ---------------------------------------------------------------------------
# Full training pipeline (script entrypoint)
# ---------------------------------------------------------------------------
def run_training() -> dict:
    """Generate data if needed, build features, train both models, persist the
    advanced model bundle + metrics. Returns the metrics dict."""
    from .preprocessing import build_processed_dataset, split_data
    from . import generate_data

    if not config.RAW_CSV.exists():
        generate_data.main()

    df = build_processed_dataset()
    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.PROCESSED_CSV, index=False)

    X_train, X_test, y_train, y_test = split_data(df)

    print("Training baseline (Logistic Regression)...")
    baseline = train_baseline(X_train, y_train)
    baseline_metrics = evaluate_model(baseline, X_test, y_test)

    print("Training advanced model (XGBoost/RandomForest) with CV...")
    advanced = train_advanced(X_train, y_train)
    advanced_metrics = evaluate_model(advanced, X_test, y_test)

    feature_cols = list(X_train.columns)
    bundle = {
        "model": advanced,
        "baseline": baseline,
        "features": feature_cols,
        "model_type": getattr(advanced, "model_type_", "randomforest"),
    }
    save_model(bundle)

    metrics = {
        "advanced": advanced_metrics,
        "baseline": baseline_metrics,
        "model_type": bundle["model_type"],
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "default_rate": float(df[config.TARGET].mean()),
        "features": feature_cols,
    }
    with open(config.METRICS_PATH, "w") as fh:
        json.dump(metrics, fh, indent=2)

    # Optional MLflow logging (Stage 3.1). Best-effort: a missing mlflow or any
    # logging failure must never break training — the MVP still trains without
    # it. Does not change this function's return value or existing prints.
    try:
        from .ml import registry

        run_id = registry.log_training_run(
            params={
                "model_type": bundle["model_type"],
                "n_train": len(X_train),
                "n_test": len(X_test),
                **{f"cv_{k}": v for k, v in
                   getattr(advanced, "cv_best_params_", {}).items()},
            },
            metrics={k: v for k, v in advanced_metrics.items()
                     if isinstance(v, (int, float))},
            artifact_path=str(config.MODEL_PATH),
        )
        print(f"MLflow run_id: {run_id}")
    except Exception as exc:  # pragma: no cover - exercised only when mlflow present
        print(f"MLflow logging skipped: {exc}")

    print(f"\nBaseline  AUC-ROC: {baseline_metrics['auc_roc']:.4f}")
    print(f"Advanced  AUC-ROC: {advanced_metrics['auc_roc']:.4f}  "
          f"({bundle['model_type']})")
    print(f"Model saved to {config.MODEL_PATH}")
    print(f"Metrics saved to {config.METRICS_PATH}")
    return metrics


if __name__ == "__main__":
    run_training()

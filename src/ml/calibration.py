"""Probability calibration (Stage 3.3).

Additive: wraps an already-fitted estimator in a CalibratedClassifierCV without
touching models/model.pkl. Isotonic by default, falling back to Platt scaling
("sigmoid") when the calibration set is small (< 1000), where isotonic tends to
overfit. Also exposes the Brier score and a calibration curve that can be saved
to reports/ for the model card.
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import config

# Below this many calibration samples, isotonic overfits — use Platt instead.
MIN_ISOTONIC_SAMPLES = 1000
DEFAULT_CURVE_PATH = config.REPORTS_DIR / "calibration_curve.json"


def calibrate(estimator, X_cal, y_cal, method="isotonic"):
    """Return a CalibratedClassifierCV wrapping the prefit ``estimator``.

    Falls back from isotonic to "sigmoid" (Platt) when n < MIN_ISOTONIC_SAMPLES.
    The base estimator is treated as already fitted (frozen), so the original
    model is left untouched.
    """
    from sklearn.calibration import CalibratedClassifierCV

    if method == "isotonic" and len(y_cal) < MIN_ISOTONIC_SAMPLES:
        method = "sigmoid"

    try:  # sklearn >= 1.6 prefers FrozenEstimator over cv="prefit"
        from sklearn.frozen import FrozenEstimator

        calibrated = CalibratedClassifierCV(FrozenEstimator(estimator),
                                            method=method)
    except ImportError:  # pragma: no cover - older sklearn
        calibrated = CalibratedClassifierCV(estimator, method=method, cv="prefit")

    calibrated.fit(X_cal, y_cal)
    return calibrated


def brier(y_true, y_proba) -> float:
    """Brier score (mean squared error of predicted probabilities). Lower=better."""
    from sklearn.metrics import brier_score_loss

    return float(brier_score_loss(y_true, y_proba))


def calibration_curve_points(y_true, y_proba, n_bins=10):
    """Return (prob_true, prob_pred) reliability-curve points as lists."""
    from sklearn.calibration import calibration_curve

    prob_true, prob_pred = calibration_curve(
        y_true, y_proba, n_bins=n_bins, strategy="uniform")
    return prob_true.tolist(), prob_pred.tolist()


def save_calibration_curve(y_true, y_proba, path=None, n_bins=10) -> str:
    """Write reliability-curve points + Brier score as JSON to reports/.

    Returns the path written. ``path`` defaults to reports/calibration_curve.json.
    """
    path = Path(path) if path is not None else DEFAULT_CURVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    prob_true, prob_pred = calibration_curve_points(y_true, y_proba, n_bins=n_bins)
    payload = {
        "brier": brier(y_true, y_proba),
        "n_bins": n_bins,
        "prob_true": prob_true,
        "prob_pred": prob_pred,
    }
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2)
    return str(path)

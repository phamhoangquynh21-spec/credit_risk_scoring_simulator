"""Tests for probability calibration (Stage 3.3)."""
from __future__ import annotations

import json

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from src.ml import calibration


@pytest.fixture
def synthetic_split():
    """Three-way split (train / calibrate / held-out) for calibration testing.

    Returns est, (Xcal, ycal), (Xhold, yhold). The estimator is deliberately
    mis-calibrated (under-regularised) so calibration has room to help.
    """
    rng = np.random.RandomState(0)
    n = 1200
    X = rng.normal(size=(n, 4))
    logit = X[:, 0] * 2.0 + X[:, 1]
    y = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit))).astype(int)

    Xtr, ytr = X[:400], y[:400]
    Xcal, ycal = X[400:800], y[400:800]
    Xhold, yhold = X[800:], y[800:]
    est = LogisticRegression(C=0.05).fit(Xtr, ytr)  # under-regularised => skewed
    return est, (Xcal, ycal), (Xhold, yhold)


def test_calibration_does_not_worsen_brier(synthetic_split):
    est, (Xcal, ycal), (Xhold, yhold) = synthetic_split

    # Fit calibration on the calibration split, evaluate on a SEPARATE held-out
    # split (out-of-sample) so the improvement isn't tautological.
    calibrated = calibration.calibrate(est, Xcal, ycal)

    uncal = est.predict_proba(Xhold)[:, 1]
    cal = calibrated.predict_proba(Xhold)[:, 1]

    # With n<1000 this falls back to Platt; calibrated Brier must be <= or ~equal.
    assert calibration.brier(yhold, cal) <= calibration.brier(yhold, uncal) + 1e-6


def test_small_set_falls_back_to_sigmoid(synthetic_split):
    est, (Xcal, ycal), _ = synthetic_split  # 400 samples < MIN_ISOTONIC_SAMPLES
    calibrated = calibration.calibrate(est, Xcal, ycal, method="isotonic")
    methods = {getattr(cc, "method", None)
               for cc in calibrated.calibrated_classifiers_}
    assert methods == {"sigmoid"}


def test_save_calibration_curve_writes_artifact(synthetic_split, tmp_path):
    est, (Xcal, ycal), _ = synthetic_split
    proba = est.predict_proba(Xcal)[:, 1]

    out = tmp_path / "curve.json"
    written = calibration.save_calibration_curve(ycal, proba, path=out, n_bins=5)

    assert written == str(out)
    payload = json.loads(out.read_text())
    assert "brier" in payload
    assert len(payload["prob_true"]) == len(payload["prob_pred"])

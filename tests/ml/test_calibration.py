"""Tests for probability calibration (Stage 3.3)."""
from __future__ import annotations

import json

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from src.ml import calibration


@pytest.fixture
def synthetic_split():
    """A small, deliberately mis-calibrated split for calibration testing."""
    rng = np.random.RandomState(0)
    n = 800
    X = rng.normal(size=(n, 4))
    logit = X[:, 0] * 2.0 + X[:, 1]
    y = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit))).astype(int)

    # Fit on the first half, calibrate/evaluate on the second.
    Xtr, ytr = X[:400], y[:400]
    Xcal, ycal = X[400:], y[400:]
    est = LogisticRegression(C=0.05).fit(Xtr, ytr)  # under-regularised => skewed
    return est, Xcal, ycal


def test_calibration_does_not_worsen_brier(synthetic_split):
    est, Xcal, ycal = synthetic_split
    uncal = est.predict_proba(Xcal)[:, 1]

    calibrated = calibration.calibrate(est, Xcal, ycal)
    cal = calibrated.predict_proba(Xcal)[:, 1]

    # With n<1000 this falls back to Platt; calibrated Brier must be <= or ~equal.
    assert calibration.brier(ycal, cal) <= calibration.brier(ycal, uncal) + 1e-6


def test_small_set_falls_back_to_sigmoid(synthetic_split):
    est, Xcal, ycal = synthetic_split  # 400 samples < MIN_ISOTONIC_SAMPLES
    calibrated = calibration.calibrate(est, Xcal, ycal, method="isotonic")
    methods = {getattr(cc, "method", None)
               for cc in calibrated.calibrated_classifiers_}
    assert methods == {"sigmoid"}


def test_save_calibration_curve_writes_artifact(synthetic_split, tmp_path):
    est, Xcal, ycal = synthetic_split
    proba = est.predict_proba(Xcal)[:, 1]

    out = tmp_path / "curve.json"
    written = calibration.save_calibration_curve(ycal, proba, path=out, n_bins=5)

    assert written == str(out)
    payload = json.loads(out.read_text())
    assert "brier" in payload
    assert len(payload["prob_true"]) == len(payload["prob_pred"])

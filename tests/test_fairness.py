"""Tests for src/fairness.py — the per-group fairness audit table."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.fairness import disparity_summary, run_fairness_audit


class _StubModel:
    """Returns fixed positive-class probabilities, one per row."""

    def __init__(self, proba):
        self._p = np.asarray(proba, dtype=float)

    def predict_proba(self, X):
        p = self._p[: len(X)]
        return np.column_stack([1.0 - p, p])


@pytest.fixture
def sample():
    X = pd.DataFrame({
        "age": [25, 35, 45, 55, 28, 38],
        "sex": [1, 2, 1, 2, 1, 2],
        "education": [1, 2, 1, 2, 3, 3],
    })
    y = pd.Series([1, 0, 1, 0, 1, 0])
    # Two rows (0.45, 0.35) sit between 0.3 and 0.5 — they flip when the
    # threshold drops, which is what the threshold test relies on.
    return _StubModel([0.9, 0.1, 0.6, 0.2, 0.45, 0.35]), X, y


def test_audit_shape_and_groups(sample):
    model, X, y = sample
    audit = run_fairness_audit(model, X, y, protected_attrs=["sex"])
    assert {"attribute", "group", "n", "predicted_positive_rate",
            "recall", "precision"} <= set(audit.columns)
    assert set(audit["group"]) == {"Male", "Female"}
    assert audit["n"].sum() == len(X)


def test_default_threshold_is_one_half(sample):
    """The default must stay 0.5 — existing callers rely on it."""
    model, X, y = sample
    default = run_fairness_audit(model, X, y, protected_attrs=["sex"])
    explicit = run_fairness_audit(model, X, y, protected_attrs=["sex"], threshold=0.5)
    pd.testing.assert_frame_equal(default, explicit)


def test_lower_threshold_flags_more_people(sample):
    """Auditing at a lower (cost-tuned) cut-off must raise selection rates —
    otherwise the audit would describe a model nobody is running."""
    model, X, y = sample
    high = run_fairness_audit(model, X, y, protected_attrs=["sex"], threshold=0.5)
    low = run_fairness_audit(model, X, y, protected_attrs=["sex"], threshold=0.3)
    assert low["predicted_positive_rate"].sum() > high["predicted_positive_rate"].sum()


def test_disparity_summary_reports_ratio_per_attribute(sample):
    model, X, y = sample
    audit = run_fairness_audit(model, X, y, protected_attrs=["sex"])
    summary = disparity_summary(audit)
    assert set(summary["attribute"]) == {"sex"}
    ratio = summary.loc[0, "selection_rate_ratio"]
    assert 0.0 <= ratio <= 1.0

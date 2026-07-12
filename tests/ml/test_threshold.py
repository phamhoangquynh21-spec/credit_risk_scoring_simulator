"""Tests for the cost-sensitive threshold optimiser (Stage 3.4)."""
from __future__ import annotations

import numpy as np
import pytest

from src.ml import threshold


@pytest.fixture
def imbalanced_scores():
    """Imbalanced synthetic set (~15% positives) with a usable probability signal."""
    rng = np.random.RandomState(1)
    n = 2000
    y = (rng.uniform(size=n) < 0.15).astype(int)
    # Positives score higher on average, but with overlap.
    proba = np.clip(np.where(y == 1,
                             rng.normal(0.55, 0.2, n),
                             rng.normal(0.30, 0.2, n)), 0, 1)
    return y, proba


def test_fn_heavy_cost_pushes_threshold_below_half(imbalanced_scores):
    y, proba = imbalanced_scores
    t = threshold.optimize_threshold(y, proba)  # FN_COST=5, FP_COST=1
    assert t < 0.5, f"expected threshold < 0.5 with FN=5xFP, got {t}"
    print(f"chosen threshold = {t}")


def test_equal_costs_threshold_not_forced_low(imbalanced_scores):
    y, proba = imbalanced_scores
    t_equal = threshold.optimize_threshold(y, proba, fn_cost=1, fp_cost=1)
    t_fn = threshold.optimize_threshold(y, proba, fn_cost=5, fp_cost=1)
    # Heavier FN penalty never raises the threshold above the equal-cost choice.
    assert t_fn <= t_equal

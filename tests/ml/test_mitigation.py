"""Tests for the fairness mitigation experiments (Stage 7.1).

Synthetic, offline, no optional libs. The biased scenario deliberately fails the
four-fifths rule under a single global threshold and recovers under per-group
thresholds.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.ml import mitigation, threshold


@pytest.fixture
def imbalanced_two_group():
    """Two groups (A ~25%); group A has a LOWER positive rate than B, so the
    (A, positive) cell is under-represented relative to statistical independence
    — exactly the imbalance reweighing is meant to correct."""
    rng = np.random.RandomState(7)
    n = 4000
    s = np.where(rng.uniform(size=n) < 0.25, "A", "B")
    pos_rate = np.where(s == "A", 0.07, 0.18)
    y = (rng.uniform(size=n) < pos_rate).astype(int)
    proba = np.clip(np.where(y == 1,
                             rng.normal(0.55, 0.2, n),
                             rng.normal(0.30, 0.2, n)), 0, 1)
    return y, proba, s


def test_reweigh_upweights_underrepresented_cells(imbalanced_two_group):
    y, _, s = imbalanced_two_group
    w = mitigation.reweigh(y, s)

    # One weight per sample and (all cells populated) sums to ~n.
    assert w.shape == (len(y),)
    assert w.sum() == pytest.approx(len(y), rel=1e-9)

    # Group A has the lower positive rate, so (A, positive) is under-represented
    # vs independence and is upweighted (>1), while (A, negative) is
    # over-represented and downweighted (<1). Reweighing weights form a
    # checkerboard: the other over-represented diagonal, (B, positive), is
    # likewise downweighted. (Note (A,positive) and (B,negative) share a
    # diagonal, so both are upweighted together — you can never have one >1 and
    # the other <1.)
    a_pos = w[(s == "A") & (y == 1)][0]
    a_neg = w[(s == "A") & (y == 0)][0]
    b_pos = w[(s == "B") & (y == 1)][0]
    assert a_pos > 1.0
    assert a_neg < 1.0
    assert a_pos > a_neg
    assert b_pos < 1.0


def test_reweigh_makes_group_label_independent(imbalanced_two_group):
    y, _, s = imbalanced_two_group
    w = mitigation.reweigh(y, s)
    # After reweighting, weighted P(label=1 | group) equals weighted P(label=1).
    overall = w[y == 1].sum() / w.sum()
    for g in np.unique(s):
        gm = s == g
        pos_g = w[gm & (y == 1)].sum() / w[gm].sum()
        assert pos_g == pytest.approx(overall, abs=1e-9)


def test_per_group_thresholds_one_per_group(imbalanced_two_group):
    y, proba, s = imbalanced_two_group
    thr = mitigation.per_group_thresholds(y, proba, s)
    assert set(thr) == {"A", "B"}
    assert all(0.0 <= t <= 1.0 for t in thr.values())
    # Costs default to the cost-sensitive FN=5/FP=1 constants.
    thr_explicit = mitigation.per_group_thresholds(
        y, proba, s, fn_cost=threshold.FN_COST, fp_cost=threshold.FP_COST)
    assert thr == thr_explicit


def test_disparity_ratio_min_over_max():
    assert mitigation.disparity_ratio({"A": 0.2, "B": 0.5}) == pytest.approx(0.4)
    assert np.isnan(mitigation.disparity_ratio({"A": 0.0, "B": 0.0}))


@pytest.fixture
def biased_scenario():
    """Group B's scores are inflated by +0.2 while true default rates are equal.

    A single global threshold therefore selects far more of group B (adverse
    impact); per-group cost-optimal thresholds compensate for the inflation.
    """
    rng = np.random.RandomState(11)
    n = 6000
    s = np.where(rng.uniform(size=n) < 0.5, "A", "B")
    y = (rng.uniform(size=n) < 0.15).astype(int)
    base = np.where(y == 1, rng.normal(0.55, 0.15, n), rng.normal(0.30, 0.15, n))
    proba = np.clip(base + np.where(s == "B", 0.20, 0.0), 0, 1)
    return y, proba, s


def test_biased_scenario_fails_then_improves(biased_scenario):
    y, proba, s = biased_scenario
    result = mitigation.evaluate_mitigation(y, proba, s)

    global_dr = result["global"]["disparity_ratio"]
    group_dr = result["per_group"]["disparity_ratio"]

    # Under one global threshold the 0.8 rule FAILS...
    assert global_dr < mitigation.FOUR_FIFTHS
    assert result["global"]["passes_four_fifths"] is False
    # ...and per-group thresholds IMPROVE the ratio (here, back above 0.8).
    assert group_dr > global_dr
    assert group_dr >= mitigation.FOUR_FIFTHS
    assert result["per_group"]["passes_four_fifths"] is True

    print(f"global disparity_ratio = {global_dr:.3f} "
          f"(threshold={result['global_threshold']:.3f}); "
          f"per-group disparity_ratio = {group_dr:.3f} "
          f"(thresholds={ {g: round(t, 3) for g, t in result['group_thresholds'].items()} })")


def test_evaluate_mitigation_accepts_supplied_thresholds(biased_scenario):
    y, proba, s = biased_scenario
    custom = {"A": 0.4, "B": 0.6}
    result = mitigation.evaluate_mitigation(y, proba, s, group_thresholds=custom)
    assert result["group_thresholds"] == custom

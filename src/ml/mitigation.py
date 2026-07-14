"""Fairness *mitigation* experiments (Stage 7.1) — builds on the detection-only
audit in ``src.fairness``.

The existing audit (``src.fairness.run_fairness_audit``/``disparity_summary``)
*detects* and *discloses* disparity. This module adds two governance
*experiments* so a human can weigh the accuracy-vs-fairness trade-off:

1. **Reweighing** (Kamiran & Calders, 2012) — pre-processing sample weights that
   rebalance the (group, label) cells without touching features or labels.
2. **Per-group thresholds** — reuses the cost-sensitive optimiser
   (``src.ml.threshold.optimize_threshold``) once per protected group.

Both are EXPERIMENTS whose output feeds a governance decision; nothing here is
auto-applied to the champion. The disparity yardstick is the four-fifths (0.8)
rule Adam locked (``FOUR_FIFTHS``).

Implemented with numpy/sklearn only. ``fairlearn`` is the optional upgrade path
(``ExponentiatedGradient``/``ThresholdOptimizer`` give constrained-optimisation
mitigations); it is intentionally NOT a dependency here, mirroring the way
Stage 5 kept ``evidently`` optional.
"""
from __future__ import annotations

import numpy as np

from . import threshold

# The four-fifths (80%) rule: min/max selection rate below this flags adverse
# impact. Locked project-wide as the disparity yardstick.
FOUR_FIFTHS = 0.8


def reweigh(y_true, sensitive) -> np.ndarray:
    """Kamiran-Calders reweighing sample weights (one per sample).

    ``w[i] = ( P(group=g) * P(label=c) ) / P(group=g, label=c)`` for sample i's
    (group g, label c). Under-represented (group, label) cells get weight > 1 and
    over-represented cells get weight < 1, so a reweighted fit sees group and
    label as statistically independent. The weights sum to ~n (exactly n when
    every (group, label) cell is populated).
    """
    y = np.asarray(y_true)
    s = np.asarray(sensitive)
    n = len(y)
    if n == 0:
        return np.empty(0, dtype=float)

    w = np.ones(n, dtype=float)
    for g in np.unique(s):
        p_g = float(np.mean(s == g))
        for c in np.unique(y):
            cell = (s == g) & (y == c)
            p_gc = float(np.mean(cell))
            if p_gc == 0.0:
                continue
            p_c = float(np.mean(y == c))
            w[cell] = (p_g * p_c) / p_gc
    return w


def per_group_thresholds(y_true, y_proba, sensitive,
                         fn_cost=None, fp_cost=None) -> dict:
    """Cost-optimal decision threshold per protected group.

    Reuses ``threshold.optimize_threshold`` on each group's slice. Costs default
    to ``threshold.FN_COST``/``threshold.FP_COST`` (a missed default costs 5x a
    false alarm), so each group is operated at its own minimum-cost point.
    """
    fn_cost = threshold.FN_COST if fn_cost is None else fn_cost
    fp_cost = threshold.FP_COST if fp_cost is None else fp_cost

    y = np.asarray(y_true)
    p = np.asarray(y_proba)
    s = np.asarray(sensitive)

    out = {}
    for g in np.unique(s):
        mask = s == g
        out[g] = threshold.optimize_threshold(
            y[mask], p[mask], fn_cost=fn_cost, fp_cost=fp_cost)
    return out


def _selection_rates(y_proba, sensitive, thresholds) -> dict:
    """Predicted-positive (selection) rate per group under ``thresholds``.

    ``thresholds`` is either a single float applied to every group, or a
    ``dict[group, float]`` of per-group thresholds.
    """
    p = np.asarray(y_proba)
    s = np.asarray(sensitive)
    rates = {}
    for g in np.unique(s):
        mask = s == g
        t = thresholds[g] if isinstance(thresholds, dict) else thresholds
        rates[g] = float((p[mask] >= t).mean())
    return rates


def disparity_ratio(selection_rates: dict) -> float:
    """Four-fifths ratio: min selection rate / max selection rate.

    1.0 is perfect parity; below ``FOUR_FIFTHS`` (0.8) flags adverse impact.
    Returns ``nan`` when the max rate is 0 (nobody selected — ratio undefined).
    """
    vals = [v for v in selection_rates.values()]
    hi = max(vals) if vals else 0.0
    if hi == 0.0:
        return float("nan")
    return min(vals) / hi


def evaluate_mitigation(y_true, y_proba, sensitive,
                        group_thresholds=None) -> dict:
    """Compare one global threshold vs per-group thresholds on the 0.8 rule.

    Returns, for each strategy, the per-group selection rate, the four-fifths
    ``disparity_ratio`` and whether it ``passes`` ``FOUR_FIFTHS`` — so a caller
    can read off the accuracy-vs-fairness trade-off. ``y_true`` is used only to
    derive the cost-optimal thresholds (via ``threshold.optimize_threshold`` /
    ``per_group_thresholds``), not to score the outcome.

    NOTE: per-group thresholds are a GOVERNANCE EXPERIMENT — applying different
    decision cut-offs by a protected attribute can itself be disparate treatment.
    This function quantifies the trade-off; it does not choose or apply it.
    """
    global_threshold = threshold.optimize_threshold(y_true, y_proba)
    if group_thresholds is None:
        group_thresholds = per_group_thresholds(y_true, y_proba, sensitive)

    global_rates = _selection_rates(y_proba, sensitive, global_threshold)
    group_rates = _selection_rates(y_proba, sensitive, group_thresholds)

    global_dr = disparity_ratio(global_rates)
    group_dr = disparity_ratio(group_rates)

    def _passes(dr):
        return bool(dr >= FOUR_FIFTHS) if dr == dr else False  # nan -> False

    return {
        "global_threshold": global_threshold,
        "group_thresholds": group_thresholds,
        "global": {
            "selection_rates": global_rates,
            "disparity_ratio": global_dr,
            "passes_four_fifths": _passes(global_dr),
        },
        "per_group": {
            "selection_rates": group_rates,
            "disparity_ratio": group_dr,
            "passes_four_fifths": _passes(group_dr),
        },
    }

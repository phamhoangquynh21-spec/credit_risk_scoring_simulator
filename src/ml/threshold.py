"""Cost-sensitive decision threshold (Stage 3.4) — kills the fixed 0.5.

A missed default (false negative) is far more expensive than a false alarm
(false positive), so the operating threshold is chosen to minimise total
expected cost rather than defaulting to 0.5.
"""
from __future__ import annotations

import numpy as np

# A missed default costs 5x a false alarm (ratio from the plan's B.3).
FN_COST = 5
FP_COST = 1


def optimize_threshold(y_true, y_proba, fn_cost=FN_COST, fp_cost=FP_COST,
                       n_steps=101) -> float:
    """Sweep candidate thresholds and return the one minimising total cost.

    Cost = fn_cost * (#false negatives) + fp_cost * (#false positives).
    With fn_cost > fp_cost the optimum sits below 0.5 (we accept more false
    alarms to catch more defaults).
    """
    y_true = np.asarray(y_true)
    y_proba = np.asarray(y_proba)

    best_t, best_cost = 0.5, float("inf")
    for t in np.linspace(0.0, 1.0, n_steps):
        pred = (y_proba >= t).astype(int)
        fn = int(((pred == 0) & (y_true == 1)).sum())
        fp = int(((pred == 1) & (y_true == 0)).sum())
        cost = fn_cost * fn + fp_cost * fp
        if cost < best_cost:
            best_cost, best_t = cost, float(t)
    return best_t

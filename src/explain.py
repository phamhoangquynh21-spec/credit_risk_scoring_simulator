"""SHAP-based explainability. Implements Technical_Spec.md section 6.

Works with tree models (XGBoost / RandomForest) via shap.TreeExplainer, which is
fast and exact for trees. Also provides plain-language phrasing so a non-technical
Risk Manager can read *why* a customer scored the way they did (US2).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Friendly names for the dashboard / plain-language explanations.
FRIENDLY_NAMES = {
    "limit_bal": "Credit limit",
    "sex": "Sex",
    "education": "Education level",
    "marriage": "Marital status",
    "age": "Age",
    "pay_0": "Most recent repayment status",
    "pay_2": "Repayment status (2 months ago)",
    "pay_3": "Repayment status (3 months ago)",
    "pay_4": "Repayment status (4 months ago)",
    "pay_5": "Repayment status (5 months ago)",
    "pay_6": "Repayment status (6 months ago)",
    "avg_bill_amt": "Average bill amount",
    "avg_pay_amt": "Average payment amount",
    "credit_utilization": "Credit utilisation",
    "months_delayed_count": "Number of months with late payment",
    "payment_trend": "Recent payment trend",
}


def _explainer(model):
    import shap
    return shap.TreeExplainer(model)


def get_shap_values(model, X: pd.DataFrame):
    """Compute SHAP values for ``model`` over feature matrix ``X``.

    Returns a shap.Explanation object.
    """
    explainer = _explainer(model)
    return explainer(X)


def _positive_class_values(explanation) -> np.ndarray:
    """Extract per-feature SHAP contributions for the positive (default) class.

    RandomForest yields shape (n, features, classes); XGBoost yields (n, features).
    """
    vals = np.asarray(explanation.values)
    if vals.ndim == 3:
        return vals[..., 1]
    return vals


def explain_single_customer(model, customer_row: pd.Series) -> list[tuple[str, float]]:
    """Return the top 5 features driving this customer's prediction as
    (feature_name, contribution) pairs, sorted by absolute impact."""
    X = customer_row.to_frame().T.apply(pd.to_numeric)
    explanation = get_shap_values(model, X)
    contributions = _positive_class_values(explanation)[0]
    pairs = list(zip(X.columns, (float(c) for c in contributions)))
    pairs.sort(key=lambda p: abs(p[1]), reverse=True)
    return pairs[:5]


def explain_in_plain_language(
    model, customer_row: pd.Series, top_n: int = 5
) -> list[dict]:
    """Human-readable version of :func:`explain_single_customer` for the dashboard.

    Each item: {feature, friendly, value, contribution, direction, sentence}.
    """
    pairs = explain_single_customer(model, customer_row)[:top_n]
    out = []
    for feat, contrib in pairs:
        direction = "increases" if contrib > 0 else "decreases"
        friendly = FRIENDLY_NAMES.get(feat, feat)
        raw_val = customer_row[feat]
        out.append({
            "feature": feat,
            "friendly": friendly,
            "value": raw_val,
            "contribution": contrib,
            "direction": direction,
            "sentence": f"{friendly} (value: {raw_val:g}) {direction} the default risk.",
        })
    return out


def risk_score(model, X_row: pd.DataFrame) -> float:
    """Return a 0-100 risk score (probability of default * 100) for one row."""
    proba = float(model.predict_proba(X_row)[:, 1][0])
    return round(proba * 100, 1)

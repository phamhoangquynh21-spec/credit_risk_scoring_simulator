"""Fairness audit across protected attributes. Implements Technical_Spec.md
section 7 and PRD goal on fairness (detect and disclose, not mitigate).

For each protected attribute we report, per group: size, actual default rate,
predicted-positive rate (selection rate), recall (true-positive rate) and
precision. Disparities are summarised as ratios against the best-performing
group so the report can flag gaps.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

# Age is continuous, so we bucket it into interpretable groups.
AGE_BINS = [20, 30, 40, 50, 60, 80]
AGE_LABELS = ["21-30", "31-40", "41-50", "51-60", "61+"]


def _age_group(age: pd.Series) -> pd.Series:
    return pd.cut(age, bins=AGE_BINS, labels=AGE_LABELS, right=True)


def _group_labels(attr: str, values: pd.Series) -> pd.Series:
    if attr == "sex":
        return values.map(config.SEX_LABELS)
    if attr == "education":
        return values.map(config.EDUCATION_LABELS)
    if attr == "marriage":
        return values.map(config.MARRIAGE_LABELS)
    if attr == "age_group":
        return values
    return values


def run_fairness_audit(
    model, X_test, y_test, protected_attrs: list[str] | None = None
) -> pd.DataFrame:
    """Return a per-group fairness comparison table.

    ``protected_attrs`` may include 'sex', 'education', 'marriage' and the
    special 'age_group' (derived from the ``age`` column).
    """
    if protected_attrs is None:
        protected_attrs = ["sex", "education", "age_group"]

    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)

    data = X_test.copy()
    data["_y"] = np.asarray(y_test)
    data["_pred"] = pred
    data["age_group"] = _age_group(data["age"])

    rows = []
    for attr in protected_attrs:
        source_col = attr if attr in data.columns else attr
        labels = _group_labels(attr, data[source_col])
        for group, idx in data.groupby(labels, observed=True).groups.items():
            sub = data.loc[idx]
            y = sub["_y"]
            p = sub["_pred"]
            actual_pos = int(y.sum())
            tp = int(((p == 1) & (y == 1)).sum())
            pp = int((p == 1).sum())
            rows.append({
                "attribute": attr,
                "group": str(group),
                "n": int(len(sub)),
                "actual_default_rate": round(float(y.mean()), 4),
                "predicted_positive_rate": round(float(p.mean()), 4),
                "recall": round(tp / actual_pos, 4) if actual_pos else np.nan,
                "precision": round(tp / pp, 4) if pp else np.nan,
            })

    return pd.DataFrame(rows)


def disparity_summary(audit: pd.DataFrame) -> pd.DataFrame:
    """For each attribute, the max/min ratio of selection rate and recall across
    groups — a quick read on how large the fairness gap is."""
    out = []
    for attr, grp in audit.groupby("attribute"):
        ppr = grp["predicted_positive_rate"]
        rec = grp["recall"].dropna()
        out.append({
            "attribute": attr,
            "selection_rate_ratio": round(ppr.min() / ppr.max(), 3) if ppr.max() else np.nan,
            "recall_ratio": round(rec.min() / rec.max(), 3) if len(rec) and rec.max() else np.nan,
            "n_groups": int(grp["group"].nunique()),
        })
    return pd.DataFrame(out)

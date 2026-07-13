"""Data-quality checks (Stage 5.2).

Null-rate and out-of-contract-rate per feature, with bounds/allowed values
taken from ``src.ml.feature_contract.FEATURE_CONTRACT`` (single source of
truth — nothing is duplicated here).
"""
from __future__ import annotations

from src import db
from src.ml.feature_contract import FEATURE_CONTRACT

NULL_RATE_ALERT = 0.05
OOC_RATE_ALERT = 0.05

_SPEC_BY_NAME = {spec.name: spec for spec in FEATURE_CONTRACT}


def _out_of_contract_count(col, spec) -> int:
    """Non-null values violating the contract spec (range or allowed set)."""
    values = col.dropna()
    if spec.allowed_values is not None:
        return int((~values.isin(spec.allowed_values)).sum())
    return int(((values < spec.min) | (values > spec.max)).sum())


def quality_report(df, features: list[str]) -> list[dict]:
    """Per-feature quality of ``df``.

    Returns [{feature, null_rate, out_of_contract_rate, severity}] with
    severity "alert" when either rate exceeds its threshold, else "ok".
    A feature missing from the frame counts as fully null; a feature without a
    contract spec only gets the null check.
    """
    n = len(df)
    report = []
    for feature in features:
        if feature not in df.columns or n == 0:
            null_rate, ooc_rate = 1.0, 0.0
        else:
            col = df[feature]
            null_rate = float(col.isna().mean())
            spec = _SPEC_BY_NAME.get(feature)
            ooc_rate = _out_of_contract_count(col, spec) / n if spec else 0.0
        severity = ("alert"
                    if null_rate > NULL_RATE_ALERT or ooc_rate > OOC_RATE_ALERT
                    else "ok")
        report.append({
            "feature": feature,
            "null_rate": null_rate,
            "out_of_contract_rate": float(ooc_rate),
            "severity": severity,
        })
    return report


def record_quality(report: list[dict], period_iso: str, client=None) -> None:
    """Persist a quality_report: ``dq_null_rate.<feature>`` and
    ``dq_ooc_rate.<feature>`` monitoring_metrics rows, plus a ``dq_alert``
    audit_logs row for every non-ok feature."""
    rows = []
    for r in report:
        rows.append({"period": period_iso,
                     "metric": f"dq_null_rate.{r['feature']}",
                     "value": r["null_rate"]})
        rows.append({"period": period_iso,
                     "metric": f"dq_ooc_rate.{r['feature']}",
                     "value": r["out_of_contract_rate"]})
    db.record_metrics(rows, client=client)
    for r in report:
        if r["severity"] != "ok":
            db.log_action(None, "dq_alert", "monitoring", r["feature"], {
                "null_rate": r["null_rate"],
                "out_of_contract_rate": r["out_of_contract_rate"],
                "severity": r["severity"],
                "period": period_iso,
            }, client=client)

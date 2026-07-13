"""Feature/prediction drift detection (Stage 5.1).

Deliberately dependency-light: PSI + two-sample KS implemented with
numpy/scipy only, so drift jobs run in the base environment. Evidently is the
documented upgrade path (see infra/requirements-monitoring.txt) and is NOT
imported here.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import stats

from src import db

# Population stability index conventions: < 0.1 stable, 0.1-0.2 drifting,
# >= 0.2 significant shift.
PSI_WARN = 0.1
PSI_ALERT = 0.2
KS_PVALUE_ALERT = 0.01


def psi(expected, actual, bins: int = 10) -> float:
    """Population stability index of ``actual`` against ``expected``.

    Bins are ``bins`` quantile bins of the expected distribution with the outer
    edges opened to +/-inf; zero-count bins are floored with a small epsilon so
    the log term stays finite. A constant reference feature yields 0.0.
    """
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    edges = np.unique(np.quantile(expected, np.linspace(0.0, 1.0, bins + 1)))
    if len(edges) < 2:  # constant reference: no distribution to compare against
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    eps = 1e-6
    e_frac = np.clip(np.histogram(expected, bins=edges)[0] / len(expected), eps, None)
    a_frac = np.clip(np.histogram(actual, bins=edges)[0] / len(actual), eps, None)
    return float(np.sum((a_frac - e_frac) * np.log(a_frac / e_frac)))


def ks_test(expected, actual) -> tuple[float, float]:
    """Two-sample Kolmogorov-Smirnov test: (statistic, pvalue)."""
    result = stats.ks_2samp(np.asarray(expected, dtype=float),
                            np.asarray(actual, dtype=float))
    return float(result.statistic), float(result.pvalue)


def _severity(psi_value: float, ks_pvalue: float) -> str:
    """PSI drives the level; a significant KS alone elevates ok -> warn
    (KS flags tiny shifts at large n, so it never alerts by itself)."""
    if psi_value >= PSI_ALERT:
        return "alert"
    if psi_value >= PSI_WARN or ks_pvalue < KS_PVALUE_ALERT:
        return "warn"
    return "ok"


def drift_report(reference_df, current_df, features: list[str]) -> list[dict]:
    """Per-feature drift of ``current_df`` against ``reference_df``.

    Returns [{feature, psi, ks_stat, ks_pvalue, severity}] with severity in
    "ok" | "warn" | "alert" | "insufficient_data". Nulls are dropped before
    comparison (data-quality checks cover them separately). A feature with fewer
    than two non-null values on either side (e.g. 100% null in the current
    period) is degenerate: PSI/KS would be NaN, so it is reported with
    psi/ks None and severity "insufficient_data" (never a silent "ok"), and is
    excluded from the persisted metric by ``record_drift``.
    """
    report = []
    for feature in features:
        ref = reference_df[feature].dropna().to_numpy(dtype=float)
        cur = current_df[feature].dropna().to_numpy(dtype=float)
        if ref.size < 2 or cur.size < 2:
            report.append({
                "feature": feature,
                "psi": None,
                "ks_stat": None,
                "ks_pvalue": None,
                "severity": "insufficient_data",
            })
            continue
        psi_value = psi(ref, cur)
        ks_stat, ks_pvalue = ks_test(ref, cur)
        report.append({
            "feature": feature,
            "psi": psi_value,
            "ks_stat": ks_stat,
            "ks_pvalue": ks_pvalue,
            "severity": _severity(psi_value, ks_pvalue),
        })
    return report


def _is_finite(value) -> bool:
    """True only for a real, finite number (guards json.dumps(NaN/Inf), which
    emits invalid JSON that Postgres rejects)."""
    return isinstance(value, (int, float)) and math.isfinite(value)


def record_drift(report: list[dict], period_iso: str, client=None) -> None:
    """Persist a drift_report: one monitoring_metrics row per feature with a
    finite PSI (metric ``drift_psi.<feature>``, value=psi) plus a
    ``drift_alert`` audit_logs row for every non-ok feature.

    Features with a non-finite/None PSI (``insufficient_data``) are NEVER
    written to monitoring_metrics — json.dumps(NaN) is invalid JSON and Postgres
    rejects it — but they are still audit-logged (severity != "ok"), so a
    degenerate period is surfaced rather than silently dropped.
    """
    rows = [{"period": period_iso, "metric": f"drift_psi.{r['feature']}",
             "value": r["psi"]} for r in report if _is_finite(r["psi"])]
    if rows:
        db.record_metrics(rows, client=client)
    for r in report:
        if r["severity"] != "ok":
            db.log_action(None, "drift_alert", "monitoring", r["feature"], {
                "psi": r["psi"] if _is_finite(r["psi"]) else None,
                "ks_stat": r["ks_stat"] if _is_finite(r["ks_stat"]) else None,
                "ks_pvalue": r["ks_pvalue"] if _is_finite(r["ks_pvalue"]) else None,
                "severity": r["severity"],
                "period": period_iso,
            }, client=client)

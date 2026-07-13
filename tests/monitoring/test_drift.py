"""Offline tests for src.monitoring.drift (fake db client, no network)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.monitoring import drift
from tests.data.fakes import FakeClient

_PERIOD = "2026-07-13T00:00:00Z"


def _limit_bal(seed: int, n: int = 2000) -> np.ndarray:
    return np.random.default_rng(seed).normal(180_000, 50_000, n)


# --- psi ---------------------------------------------------------------------

def test_psi_identical_arrays_is_zero():
    ref = _limit_bal(1)
    assert drift.psi(ref, ref) == pytest.approx(0.0, abs=1e-12)


def test_psi_same_distribution_stays_below_warn():
    assert drift.psi(_limit_bal(1), _limit_bal(2)) < drift.PSI_WARN


def test_psi_shifted_limit_bal_exceeds_alert():
    ref = _limit_bal(1)
    assert drift.psi(ref, ref * 1.5) > drift.PSI_ALERT  # +50% shift


def test_psi_constant_reference_returns_zero():
    assert drift.psi(np.ones(100), np.full(100, 5.0)) == 0.0


# --- ks_test -----------------------------------------------------------------

def test_ks_identical_arrays():
    ref = _limit_bal(1)
    stat, pvalue = drift.ks_test(ref, ref)
    assert stat == 0.0 and pvalue == 1.0


def test_ks_detects_shift():
    ref = _limit_bal(1)
    stat, pvalue = drift.ks_test(ref, ref * 1.5)
    assert stat > 0.1 and pvalue < drift.KS_PVALUE_ALERT


# --- severity / drift_report ---------------------------------------------------

def test_severity_thresholds():
    assert drift._severity(0.25, 0.5) == "alert"
    assert drift._severity(0.15, 0.5) == "warn"
    assert drift._severity(0.05, 0.001) == "warn"  # KS-only elevates to warn
    assert drift._severity(0.05, 0.5) == "ok"


def test_drift_report_flags_shifted_feature_only():
    rng = np.random.default_rng(7)
    ref = pd.DataFrame({"limit_bal": _limit_bal(1),
                        "age": rng.integers(20, 70, 2000).astype(float)})
    cur = pd.DataFrame({"limit_bal": _limit_bal(2) * 1.5,
                        "age": ref["age"].to_numpy()})
    report = drift.drift_report(ref, cur, ["limit_bal", "age"])
    by_feature = {r["feature"]: r for r in report}
    assert by_feature["limit_bal"]["severity"] == "alert"
    assert by_feature["limit_bal"]["psi"] > drift.PSI_ALERT
    assert by_feature["age"]["severity"] == "ok"
    assert set(report[0]) == {"feature", "psi", "ks_stat", "ks_pvalue", "severity"}


# --- record_drift --------------------------------------------------------------

def test_record_drift_persists_metric_names_and_audits_alerts():
    report = [
        {"feature": "limit_bal", "psi": 0.31, "ks_stat": 0.2,
         "ks_pvalue": 0.001, "severity": "alert"},
        {"feature": "age", "psi": 0.02, "ks_stat": 0.01,
         "ks_pvalue": 0.9, "severity": "ok"},
    ]
    fake = FakeClient(results=[[], [{"id": 1}]])
    drift.record_drift(report, _PERIOD, client=fake)

    metrics_call, audit_call = fake.calls
    assert metrics_call.table == "monitoring_metrics"
    assert metrics_call.arg("upsert") == [
        {"period": _PERIOD, "metric": "drift_psi.limit_bal", "value": 0.31},
        {"period": _PERIOD, "metric": "drift_psi.age", "value": 0.02},
    ]
    assert audit_call.table == "audit_logs"
    assert audit_call.arg("insert") == {
        "actor_id": None, "action": "drift_alert", "entity_type": "monitoring",
        "entity_id": "limit_bal",
        "detail": {"psi": 0.31, "ks_stat": 0.2, "ks_pvalue": 0.001,
                   "severity": "alert", "period": _PERIOD}}


def test_record_drift_warn_severity_also_audits():
    report = [{"feature": "age", "psi": 0.15, "ks_stat": 0.05,
               "ks_pvalue": 0.2, "severity": "warn"}]
    fake = FakeClient(results=[[], [{"id": 1}]])
    drift.record_drift(report, _PERIOD, client=fake)
    assert [c.table for c in fake.calls] == ["monitoring_metrics", "audit_logs"]


def test_record_drift_no_audit_when_all_ok():
    report = [{"feature": "age", "psi": 0.01, "ks_stat": 0.01,
               "ks_pvalue": 0.9, "severity": "ok"}]
    fake = FakeClient()
    drift.record_drift(report, _PERIOD, client=fake)
    assert [c.table for c in fake.calls] == ["monitoring_metrics"]

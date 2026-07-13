"""Offline tests for src.monitoring.quality (fake db client, no network)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.monitoring import quality
from tests.data.fakes import FakeClient

_PERIOD = "2026-07-13T00:00:00Z"


def _clean_frame(n: int = 100) -> pd.DataFrame:
    return pd.DataFrame({
        "limit_bal": np.full(n, 200_000.0),
        "age": np.full(n, 35),
        "sex": np.full(n, 1),
    })


def test_quality_report_clean_frame_all_ok():
    report = quality.quality_report(_clean_frame(), ["limit_bal", "age", "sex"])
    assert all(r["severity"] == "ok" for r in report)
    assert all(r["null_rate"] == 0.0 and r["out_of_contract_rate"] == 0.0
               for r in report)
    assert set(report[0]) == {"feature", "null_rate", "out_of_contract_rate",
                              "severity"}


def test_quality_report_nulls_alert():
    df = _clean_frame(100)
    df.loc[:9, "limit_bal"] = np.nan  # 10% nulls > NULL_RATE_ALERT
    (row,) = quality.quality_report(df, ["limit_bal"])
    assert row["null_rate"] == pytest.approx(0.10)
    assert row["severity"] == "alert"


def test_quality_report_out_of_contract_alert():
    df = _clean_frame(100)
    df.loc[:9, "age"] = 300  # outside contract range [18, 100]
    df.loc[:9, "sex"] = 7    # not an allowed category
    report = {r["feature"]: r for r in quality.quality_report(df, ["age", "sex"])}
    assert report["age"]["out_of_contract_rate"] == pytest.approx(0.10)
    assert report["age"]["severity"] == "alert"
    assert report["sex"]["out_of_contract_rate"] == pytest.approx(0.10)
    assert report["sex"]["severity"] == "alert"


def test_quality_report_missing_feature_counts_fully_null():
    (row,) = quality.quality_report(_clean_frame(), ["payment_trend"])
    assert row["null_rate"] == 1.0
    assert row["severity"] == "alert"


def test_record_quality_persists_metric_names_and_audits_alerts():
    report = [
        {"feature": "limit_bal", "null_rate": 0.1, "out_of_contract_rate": 0.0,
         "severity": "alert"},
        {"feature": "age", "null_rate": 0.0, "out_of_contract_rate": 0.0,
         "severity": "ok"},
    ]
    fake = FakeClient(results=[[], [{"id": 1}]])
    quality.record_quality(report, _PERIOD, client=fake)

    metrics_call, audit_call = fake.calls
    assert metrics_call.table == "monitoring_metrics"
    assert metrics_call.arg("upsert") == [
        {"period": _PERIOD, "metric": "dq_null_rate.limit_bal", "value": 0.1},
        {"period": _PERIOD, "metric": "dq_ooc_rate.limit_bal", "value": 0.0},
        {"period": _PERIOD, "metric": "dq_null_rate.age", "value": 0.0},
        {"period": _PERIOD, "metric": "dq_ooc_rate.age", "value": 0.0},
    ]
    assert audit_call.table == "audit_logs"
    assert audit_call.arg("insert") == {
        "actor_id": None, "action": "dq_alert", "entity_type": "monitoring",
        "entity_id": "limit_bal",
        "detail": {"null_rate": 0.1, "out_of_contract_rate": 0.0,
                   "severity": "alert", "period": _PERIOD}}


def test_record_quality_no_audit_when_all_ok():
    report = [{"feature": "age", "null_rate": 0.0, "out_of_contract_rate": 0.0,
               "severity": "ok"}]
    fake = FakeClient()
    quality.record_quality(report, _PERIOD, client=fake)
    assert [c.table for c in fake.calls] == ["monitoring_metrics"]

"""Round-trip tests for src.db against the live Supabase project.

Skipped automatically when .env credentials are absent (same gate as
tests/platform/test_rls.py). Every row written here is clearly-marked
disposable (it-/it_test_ prefixes + uuid) and deleted in a finally block.
Existing rows are never touched: promote tests move only our own disposable
versions between dev/staging/retired — never to 'champion' (the champion-swap
path is unit-tested with fakes instead).
"""
from __future__ import annotations

import os
import uuid

import pytest
from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("SUPABASE_URL")
SERVICE = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

pytestmark = pytest.mark.skipif(
    not (URL and SERVICE),
    reason="Supabase credentials not configured",
)

from src import db  # noqa: E402


@pytest.fixture(scope="module")
def svc():
    return db.get_service_client()


def _disposable_semver():
    return f"it-0.0.1-{uuid.uuid4().hex[:8]}"


def test_model_version_lifecycle(svc):
    semver = _disposable_semver()
    try:
        row = db.register_model_version(
            semver, "logreg", {"auc": 0.5}, "it-test-data", 0.5)
        assert row["stage"] == "dev"

        fetched = db.get_model_version(semver)
        assert fetched["id"] == row["id"]

        assert db.promote_model(semver, "staging")["stage"] == "staging"
        assert db.promote_model(semver, "retired")["stage"] == "retired"
        assert db.get_model_version(semver)["stage"] == "retired"

        # promote_model wrote audit entries for our disposable semver
        audits = (svc.table("audit_logs").select("action, detail")
                  .eq("entity_id", semver).execute().data)
        assert len(audits) == 2
        assert all(a["action"] == "promote_model" for a in audits)
    finally:
        svc.table("audit_logs").delete().eq("entity_id", semver).execute()
        svc.table("model_versions").delete().eq("semver", semver).execute()


def test_monitoring_metrics_roundtrip(svc):
    metric = f"it_test_metric_{uuid.uuid4().hex[:8]}"
    try:
        db.record_metric("2026-07-01T00:00:00+00:00", metric, 0.10)
        db.record_metrics([
            {"period": "2026-07-02T00:00:00+00:00", "metric": metric, "value": 0.20},
            {"period": "2026-07-03T00:00:00+00:00", "metric": metric, "value": 0.30},
        ])
        # upsert on the (period, metric) PK is idempotent
        db.record_metric("2026-07-01T00:00:00+00:00", metric, 0.11)

        rows = db.get_metrics(metric)
        assert [r["value"] for r in rows] == [0.11, 0.20, 0.30]

        recent = db.get_metrics(metric, since="2026-07-02T00:00:00+00:00")
        assert [r["value"] for r in recent] == [0.20, 0.30]
    finally:
        svc.table("monitoring_metrics").delete().eq("metric", metric).execute()


def test_fairness_run_roundtrip(svc):
    semver = _disposable_semver()
    run_id = None
    try:
        mv = db.register_model_version(
            semver, "logreg", {}, "it-test-data", 0.5)
        run_id = db.create_fairness_run(mv["id"])
        db.add_fairness_results(run_id, [
            {"attribute": "sex", "grp": "F", "n": 100, "selection_rate": 0.40,
             "recall": 0.70, "precision": 0.60, "disparity_ratio": 0.90},
            {"attribute": "sex", "grp": "M", "n": 120, "selection_rate": 0.44,
             "recall": 0.72, "precision": 0.61, "disparity_ratio": 1.00},
        ])
        results = db.get_latest_run_results(mv["id"])
        assert {r["grp"] for r in results} == {"F", "M"}
        assert all(r["run_id"] == run_id for r in results)
    finally:
        if run_id:  # fairness_results cascade on run delete
            svc.table("fairness_runs").delete().eq("id", run_id).execute()
        svc.table("model_versions").delete().eq("semver", semver).execute()


def test_macro_indicators_roundtrip(svc):
    source = f"it_test_{uuid.uuid4().hex[:8]}"
    try:
        db.upsert_indicators([
            {"source": source, "indicator": "unrate",
             "period": "2026-05-01", "value": 4.0},
            {"source": source, "indicator": "unrate",
             "period": "2026-06-01", "value": 4.2},
        ])
        # re-upsert same PK with a new value: no duplicate, value updated
        db.upsert_indicators([
            {"source": source, "indicator": "unrate",
             "period": "2026-06-01", "value": 4.3},
        ])
        rows = db.get_indicators(source, "unrate")
        assert [r["value"] for r in rows] == [4.0, 4.3]

        recent = db.get_indicators(source, "unrate", since="2026-06-01")
        assert [r["value"] for r in recent] == [4.3]
    finally:
        svc.table("macro_indicators").delete().eq("source", source).execute()


def test_feature_flag_roundtrip(svc):
    key = f"it_test_flag_{uuid.uuid4().hex[:8]}"
    try:
        assert db.is_enabled(key) is False          # absent -> default
        assert db.is_enabled(key, default=True) is True

        db.set_flag(key, True, note="integration test")
        assert db.is_enabled(key) is True

        db.set_flag(key, False)
        assert db.is_enabled(key, default=True) is False
    finally:
        svc.table("feature_flags").delete().eq("key", key).execute()


def test_audit_log_roundtrip(svc):
    row_id = None
    try:
        row = db.log_action(None, "it_test_action", "it_test_entity",
                            entity_id="e-1", detail={"k": "v"})
        row_id = row["id"]
        assert row["action"] == "it_test_action"
        assert row["detail"] == {"k": "v"}
        assert row["actor_id"] is None
    finally:
        if row_id is not None:
            svc.table("audit_logs").delete().eq("id", row_id).execute()

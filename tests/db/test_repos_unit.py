"""Unit tests for src.db repos against a fake Supabase client (no network).

The fake records every .table(...) query chain; each .execute() pops the next
queued result. Assertions check table names, chained ops, and payloads.
"""
from __future__ import annotations

import pytest

from src.db import (audit_repo, fairness_repo, flags_repo, macro_repo,
                    models_repo, monitoring_repo)


class _Result:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, client, table):
        self._client = client
        self.table = table
        self.ops = []  # [(method, args, kwargs)]

    def __getattr__(self, name):  # insert/select/upsert/update/eq/gte/order/limit
        def op(*args, **kwargs):
            self.ops.append((name, args, kwargs))
            return self
        return op

    def execute(self):
        self._client.calls.append(self)
        return _Result(self._client.results.pop(0) if self._client.results else [])

    def op_names(self):
        return [n for n, _, _ in self.ops]

    def arg(self, method):
        """First positional arg of the first `method` op in the chain."""
        return next(a[0] for n, a, _ in self.ops if n == method)


class FakeClient:
    def __init__(self, results=None):
        self.results = list(results or [])  # one entry per execute()
        self.calls = []  # executed _FakeQuery objects, in order

    def table(self, name):
        return _FakeQuery(self, name)


# --- models_repo -----------------------------------------------------------

def test_register_model_version_builds_insert():
    fake = FakeClient(results=[[{"id": "u1", "semver": "1.2.3"}]])
    row = models_repo.register_model_version(
        "1.2.3", "xgboost", {"auc": 0.78}, "uci-default-2026", 0.42,
        client=fake)
    call = fake.calls[0]
    assert call.table == "model_versions"
    assert call.arg("insert") == {
        "semver": "1.2.3", "algo": "xgboost", "metrics": {"auc": 0.78},
        "trained_on": "uci-default-2026", "threshold": 0.42, "stage": "dev"}
    assert row == {"id": "u1", "semver": "1.2.3"}


def test_get_model_version_returns_none_when_missing():
    fake = FakeClient(results=[[]])
    assert models_repo.get_model_version("9.9.9", client=fake) is None
    call = fake.calls[0]
    assert call.table == "model_versions"
    assert ("eq", ("semver", "9.9.9"), {}) in call.ops


def test_get_champion_returns_row():
    fake = FakeClient(results=[[{"semver": "1.0.0", "stage": "champion"}]])
    assert models_repo.get_champion(client=fake)["semver"] == "1.0.0"
    assert ("eq", ("stage", "champion"), {}) in fake.calls[0].ops


def test_get_champion_returns_none_when_absent():
    fake = FakeClient(results=[[]])
    assert models_repo.get_champion(client=fake) is None


def test_promote_model_rejects_invalid_stage():
    with pytest.raises(ValueError, match="invalid stage"):
        models_repo.promote_model("1.0.0", "production", client=FakeClient())


def test_promote_to_champion_demotes_current_champion():
    fake = FakeClient(results=[
        [{"semver": "1.0.0", "stage": "champion"}],  # get_champion
        [],                                          # demote update
        [{"semver": "2.0.0", "stage": "champion"}],  # promote update
        [{"id": 1}],                                 # audit insert
    ])
    row = models_repo.promote_model("2.0.0", "champion", client=fake)
    assert row["semver"] == "2.0.0"

    demote, promote, audit = fake.calls[1], fake.calls[2], fake.calls[3]
    assert demote.table == "model_versions"
    assert demote.arg("update") == {"stage": "retired"}
    assert ("eq", ("semver", "1.0.0"), {}) in demote.ops
    assert promote.arg("update") == {"stage": "champion"}
    assert ("eq", ("semver", "2.0.0"), {}) in promote.ops
    assert audit.table == "audit_logs"
    assert audit.arg("insert")["detail"] == {
        "to_stage": "champion", "demoted": "1.0.0"}


def test_promote_to_non_champion_stage_skips_demotion():
    fake = FakeClient(results=[
        [{"semver": "2.0.0", "stage": "staging"}],  # promote update
        [{"id": 1}],                                # audit insert
    ])
    models_repo.promote_model("2.0.0", "staging", client=fake)
    assert len(fake.calls) == 2  # no get_champion, no demote
    audit = fake.calls[1]
    assert audit.table == "audit_logs"
    assert audit.arg("insert")["action"] == "promote_model"


def test_promote_unknown_semver_raises():
    fake = FakeClient(results=[[]])  # update matched no rows
    with pytest.raises(ValueError, match="not found"):
        models_repo.promote_model("0.0.0", "staging", client=fake)


# --- monitoring_repo --------------------------------------------------------

def test_record_metric_upserts_pk_payload():
    fake = FakeClient()
    monitoring_repo.record_metric("2026-07-01T00:00:00Z", "psi", 0.03,
                                  client=fake)
    call = fake.calls[0]
    assert call.table == "monitoring_metrics"
    assert call.arg("upsert") == {
        "period": "2026-07-01T00:00:00Z", "metric": "psi", "value": 0.03}


def test_record_metrics_batch_upserts():
    rows = [{"period": "2026-07-01T00:00:00Z", "metric": "psi", "value": 0.03},
            {"period": "2026-07-02T00:00:00Z", "metric": "psi", "value": 0.04}]
    fake = FakeClient()
    monitoring_repo.record_metrics(rows, client=fake)
    assert fake.calls[0].arg("upsert") == rows


def test_get_metrics_filters_and_orders():
    fake = FakeClient(results=[[{"metric": "psi", "value": 0.03}]])
    out = monitoring_repo.get_metrics("psi", since="2026-07-01T00:00:00Z",
                                      client=fake)
    call = fake.calls[0]
    assert ("eq", ("metric", "psi"), {}) in call.ops
    assert ("gte", ("period", "2026-07-01T00:00:00Z"), {}) in call.ops
    assert ("order", ("period",), {}) in call.ops
    assert out == [{"metric": "psi", "value": 0.03}]


def test_get_metrics_without_since_omits_gte():
    fake = FakeClient(results=[[]])
    monitoring_repo.get_metrics("psi", client=fake)
    assert "gte" not in fake.calls[0].op_names()


# --- fairness_repo ----------------------------------------------------------

def test_create_fairness_run_returns_id():
    fake = FakeClient(results=[[{"id": "run-1"}]])
    assert fairness_repo.create_fairness_run("mv-1", client=fake) == "run-1"
    call = fake.calls[0]
    assert call.table == "fairness_runs"
    assert call.arg("insert") == {"model_version_id": "mv-1"}


def test_add_fairness_results_injects_run_id():
    results = [{"attribute": "sex", "grp": "F", "n": 100,
                "selection_rate": 0.4, "recall": 0.7, "precision": 0.6,
                "disparity_ratio": 0.9}]
    fake = FakeClient()
    fairness_repo.add_fairness_results("run-1", results, client=fake)
    call = fake.calls[0]
    assert call.table == "fairness_results"
    assert call.arg("insert") == [{"run_id": "run-1", **results[0]}]


def test_get_latest_run_results_uses_newest_run():
    fake = FakeClient(results=[
        [{"id": "run-2"}],                       # latest fairness_runs
        [{"run_id": "run-2", "grp": "F"}],       # its results
    ])
    out = fairness_repo.get_latest_run_results("mv-1", client=fake)
    runs, res = fake.calls
    assert runs.table == "fairness_runs"
    assert ("order", ("run_at",), {"desc": True}) in runs.ops
    assert res.table == "fairness_results"
    assert ("eq", ("run_id", "run-2"), {}) in res.ops
    assert out == [{"run_id": "run-2", "grp": "F"}]


def test_get_latest_run_results_empty_when_no_runs():
    fake = FakeClient(results=[[]])
    assert fairness_repo.get_latest_run_results("mv-1", client=fake) == []
    assert len(fake.calls) == 1  # no second query


# --- macro_repo --------------------------------------------------------------

def test_upsert_indicators_batch():
    rows = [{"source": "fred", "indicator": "unrate",
             "period": "2026-06-01", "value": 4.1}]
    fake = FakeClient()
    macro_repo.upsert_indicators(rows, client=fake)
    call = fake.calls[0]
    assert call.table == "macro_indicators"
    assert call.arg("upsert") == rows


def test_get_indicators_filters_source_indicator_since():
    fake = FakeClient(results=[[]])
    macro_repo.get_indicators("fred", "unrate", since="2026-01-01",
                              client=fake)
    ops = fake.calls[0].ops
    assert ("eq", ("source", "fred"), {}) in ops
    assert ("eq", ("indicator", "unrate"), {}) in ops
    assert ("gte", ("period", "2026-01-01"), {}) in ops


# --- audit_repo ---------------------------------------------------------------

def test_log_action_payload_and_detail_default():
    fake = FakeClient(results=[[{"id": 7}]])
    row = audit_repo.log_action("user-1", "set_flag", "feature_flag",
                                entity_id="fred_connector", client=fake)
    call = fake.calls[0]
    assert call.table == "audit_logs"
    assert call.arg("insert") == {
        "actor_id": "user-1", "action": "set_flag",
        "entity_type": "feature_flag", "entity_id": "fred_connector",
        "detail": {}}
    assert row == {"id": 7}


# --- flags_repo ----------------------------------------------------------------

def test_is_enabled_returns_default_when_flag_absent():
    assert flags_repo.is_enabled("nope", client=FakeClient(results=[[]])) is False
    assert flags_repo.is_enabled("nope", default=True,
                                 client=FakeClient(results=[[]])) is True


def test_is_enabled_reads_flag_row():
    fake = FakeClient(results=[[{"enabled": True}]])
    assert flags_repo.is_enabled("fred_connector", client=fake) is True
    call = fake.calls[0]
    assert call.table == "feature_flags"
    assert ("eq", ("key", "fred_connector"), {}) in call.ops


def test_set_flag_upserts_full_state():
    fake = FakeClient()
    flags_repo.set_flag("fred_connector", True, note="stage 6 gate",
                        client=fake)
    call = fake.calls[0]
    assert call.table == "feature_flags"
    assert call.arg("upsert") == {
        "key": "fred_connector", "enabled": True, "note": "stage 6 gate"}

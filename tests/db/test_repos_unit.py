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


# --- Stateful fake: models table state so we can assert cross-write effects
#     (e.g. that a failed promote never touches the incumbent champion).

class _StatefulQuery:
    def __init__(self, store, table):
        self._store = store
        self.table = table
        self._filters = []          # [(op, col, val)]
        self._mode = None
        self._payload = None
        self._order = None
        self._desc = False
        self._limit = None

    def select(self, *a):
        self._mode = "select"
        return self

    def insert(self, payload):
        self._mode, self._payload = "insert", payload
        return self

    def update(self, payload):
        self._mode, self._payload = "update", payload
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        return self

    def neq(self, col, val):
        self._filters.append(("neq", col, val))
        return self

    def limit(self, n):
        self._limit = n
        return self

    def order(self, col, desc=False):
        self._order, self._desc = col, desc
        return self

    def _match(self, row):
        for op, col, val in self._filters:
            if op == "eq" and row.get(col) != val:
                return False
            if op == "neq" and row.get(col) == val:
                return False
        return True

    def execute(self):
        rows = self._store.tables.setdefault(self.table, [])
        if self._mode == "insert":
            items = self._payload if isinstance(self._payload, list) else [self._payload]
            added = []
            for p in items:
                r = dict(p)
                r.setdefault("id", len(rows) + 1)
                rows.append(r)
                added.append(dict(r))
            return _Result(added)
        matched = [r for r in rows if self._match(r)]
        if self._mode == "update":
            for r in matched:
                r.update(self._payload)
            return _Result([dict(r) for r in matched])
        if self._order:
            matched = sorted(matched, key=lambda r: r.get(self._order) or "",
                             reverse=self._desc)
        if self._limit is not None:
            matched = matched[:self._limit]
        return _Result([dict(r) for r in matched])


class StatefulClient:
    def __init__(self, tables):
        self.tables = {k: [dict(r) for r in v] for k, v in tables.items()}

    def table(self, name):
        return _StatefulQuery(self, name)


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
    fake = StatefulClient({"model_versions": [
        {"semver": "1.0.0", "stage": "champion"},
        {"semver": "2.0.0", "stage": "staging"},
    ]})
    row = models_repo.promote_model("2.0.0", "champion", approved_by="gov-1",
                                    client=fake)
    assert row["semver"] == "2.0.0"

    by_semver = {r["semver"]: r["stage"] for r in fake.tables["model_versions"]}
    assert by_semver == {"1.0.0": "retired", "2.0.0": "champion"}
    audit = fake.tables["audit_logs"][0]
    assert audit["action"] == "promote_model"
    assert audit["detail"] == {"to_stage": "champion", "approved_by": "gov-1",
                               "demoted": ["1.0.0"]}


def test_promote_to_champion_without_approval_is_refused():
    # Governance gate: champion promotion with no approver is refused up-front,
    # before any write -> incumbent untouched, no audit side effects.
    fake = StatefulClient({"model_versions": [
        {"semver": "1.0.0", "stage": "champion"},
        {"semver": "2.0.0", "stage": "staging"},
    ]})
    with pytest.raises(ValueError, match="governance approval"):
        models_repo.promote_model("2.0.0", "champion", client=fake)

    by_semver = {r["semver"]: r["stage"] for r in fake.tables["model_versions"]}
    assert by_semver == {"1.0.0": "champion", "2.0.0": "staging"}
    assert fake.tables.get("audit_logs", []) == []


def test_promote_to_champion_with_approval_sets_approved_by():
    fake = StatefulClient({"model_versions": [
        {"semver": "1.0.0", "stage": "champion"},
        {"semver": "2.0.0", "stage": "staging"},
    ]})
    row = models_repo.promote_model("2.0.0", "champion", approved_by="gov-1",
                                    client=fake)
    assert row["stage"] == "champion"
    assert row["approved_by"] == "gov-1"

    rows = {r["semver"]: r for r in fake.tables["model_versions"]}
    assert rows["2.0.0"]["stage"] == "champion"
    assert rows["2.0.0"]["approved_by"] == "gov-1"
    assert rows["1.0.0"]["stage"] == "retired"
    audit = fake.tables["audit_logs"][0]
    assert audit["action"] == "promote_model"
    assert audit["detail"]["approved_by"] == "gov-1"


def test_promote_nonexistent_semver_to_champion_leaves_incumbent():
    # Fix 1: a typo'd/nonexistent semver must NOT retire the incumbent champion
    # (previously the demote happened before the existence check -> zero champions).
    fake = StatefulClient({"model_versions": [
        {"semver": "1.0.0", "stage": "champion"},
    ]})
    with pytest.raises(ValueError, match="not found"):
        models_repo.promote_model("9.9.9-typo", "champion",
                                  approved_by="gov-1", client=fake)

    # Incumbent untouched, and no audit/write side effects occurred.
    assert fake.tables["model_versions"] == [
        {"semver": "1.0.0", "stage": "champion"}]
    assert fake.tables.get("audit_logs", []) == []


def test_promote_to_non_champion_stage_skips_demotion():
    fake = StatefulClient({"model_versions": [
        {"semver": "1.0.0", "stage": "champion"},
        {"semver": "2.0.0", "stage": "dev"},
    ]})
    row = models_repo.promote_model("2.0.0", "staging", client=fake)
    assert row["stage"] == "staging"
    # Champion left alone; audit records the promotion.
    by_semver = {r["semver"]: r["stage"] for r in fake.tables["model_versions"]}
    assert by_semver == {"1.0.0": "champion", "2.0.0": "staging"}
    audit = fake.tables["audit_logs"][0]
    assert audit["action"] == "promote_model"
    assert "demoted" not in audit["detail"]


def test_promote_unknown_semver_raises():
    fake = StatefulClient({"model_versions": []})
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
        [{"id": "run-2"}, {"id": "run-1"}],      # runs newest-first
        [{"run_id": "run-2", "grp": "F"}],       # newest run has results
    ])
    out = fairness_repo.get_latest_run_results("mv-1", client=fake)
    runs, res = fake.calls
    assert runs.table == "fairness_runs"
    assert ("order", ("run_at",), {"desc": True}) in runs.ops
    assert res.table == "fairness_results"
    assert ("eq", ("run_id", "run-2"), {}) in res.ops
    assert out == [{"run_id": "run-2", "grp": "F"}]


def test_get_latest_run_results_skips_empty_newest_run():
    # Fix 2: newest run has NO results -> fall back to the prior run with results.
    fake = FakeClient(results=[
        [{"id": "run-2"}, {"id": "run-1"}],      # runs newest-first
        [],                                      # run-2 (newest) empty
        [{"run_id": "run-1", "grp": "F"}],       # run-1 has results
    ])
    out = fairness_repo.get_latest_run_results("mv-1", client=fake)
    assert out == [{"run_id": "run-1", "grp": "F"}]
    assert ("eq", ("run_id", "run-2"), {}) in fake.calls[1].ops
    assert ("eq", ("run_id", "run-1"), {}) in fake.calls[2].ops


def test_get_latest_run_results_empty_when_no_runs():
    fake = FakeClient(results=[[]])
    assert fairness_repo.get_latest_run_results("mv-1", client=fake) == []
    assert len(fake.calls) == 1  # no per-run queries


def test_get_latest_run_results_empty_when_no_run_has_results():
    fake = FakeClient(results=[
        [{"id": "run-2"}, {"id": "run-1"}],      # runs newest-first
        [],                                      # run-2 empty
        [],                                      # run-1 empty
    ])
    assert fairness_repo.get_latest_run_results("mv-1", client=fake) == []


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

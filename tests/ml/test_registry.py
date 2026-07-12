"""Unit tests for src.ml.registry with a fake mlflow + fake db client.

No real mlflow server and no network: mlflow is injected into sys.modules and
the DB call goes through a fake client that records the insert payload.
"""
from __future__ import annotations

import sys

import pytest

from src.ml import registry


# --- fake mlflow -------------------------------------------------------------

class _FakeRunInfo:
    def __init__(self, run_id):
        self.run_id = run_id


class _FakeRun:
    def __init__(self, run_id):
        self.info = _FakeRunInfo(run_id)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeMlflow:
    def __init__(self, run_id="run-abc123"):
        self.run_id = run_id
        self.tracking_uri = None
        self.experiment = None
        self.params = {}
        self.metrics = {}
        self.artifacts = []

    def set_tracking_uri(self, uri):
        self.tracking_uri = uri

    def set_experiment(self, name):
        self.experiment = name

    def start_run(self):
        return _FakeRun(self.run_id)

    def log_params(self, params):
        self.params.update(params)

    def log_metrics(self, metrics):
        self.metrics.update(metrics)

    def log_artifact(self, path):
        self.artifacts.append(path)


# --- fake db client ----------------------------------------------------------

class _Result:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, client, table):
        self._client = client
        self.table = table
        self.ops = []

    def __getattr__(self, name):
        def op(*args, **kwargs):
            self.ops.append((name, args, kwargs))
            return self
        return op

    def execute(self):
        self._client.calls.append(self)
        return _Result([{"id": "mv-1"}])

    def arg(self, method):
        return next(a[0] for n, a, _ in self.ops if n == method)


class FakeClient:
    def __init__(self):
        self.calls = []

    def table(self, name):
        return _FakeQuery(self, name)


def test_log_training_run_logs_params_metrics_artifact(monkeypatch):
    fake = FakeMlflow(run_id="run-xyz")
    monkeypatch.setitem(sys.modules, "mlflow", fake)

    run_id = registry.log_training_run(
        params={"model_type": "xgboost", "n_train": 100},
        metrics={"auc_roc": 0.81, "recall": 0.6},
        artifact_path="models/model.pkl",
    )

    assert run_id == "run-xyz"
    assert fake.experiment == registry.EXPERIMENT_NAME
    assert fake.tracking_uri == registry._tracking_uri()
    assert fake.params == {"model_type": "xgboost", "n_train": 100}
    assert fake.metrics == {"auc_roc": 0.81, "recall": 0.6}
    assert fake.artifacts == ["models/model.pkl"]


def test_log_training_run_skips_artifact_when_none(monkeypatch):
    fake = FakeMlflow()
    monkeypatch.setitem(sys.modules, "mlflow", fake)

    registry.log_training_run(params={}, metrics={"auc_roc": 0.7},
                              artifact_path=None)
    assert fake.artifacts == []


def test_register_from_training_threads_run_id_into_metrics():
    client = FakeClient()
    row = registry.register_from_training(
        semver="1.4.0",
        algo="xgboost",
        metrics={"auc_roc": 0.81},
        trained_on="uci-default-2026",
        threshold=0.37,
        run_id="run-xyz",
        client=client,
    )

    assert row == {"id": "mv-1"}
    call = client.calls[0]
    assert call.table == "model_versions"
    payload = call.arg("insert")
    assert payload["semver"] == "1.4.0"
    assert payload["algo"] == "xgboost"
    assert payload["threshold"] == 0.37
    assert payload["trained_on"] == "uci-default-2026"
    assert payload["stage"] == "staging"  # default stage for registration
    # run_id lives INSIDE metrics under the documented key (no new column).
    assert payload["metrics"] == {
        "auc_roc": 0.81, registry.RUN_ID_METRIC_KEY: "run-xyz"}

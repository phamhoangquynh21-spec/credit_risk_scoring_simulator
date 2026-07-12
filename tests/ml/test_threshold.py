"""Tests for the cost-sensitive threshold optimiser (Stage 3.4)."""
from __future__ import annotations

import numpy as np
import pytest

from src.ml import threshold


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
        return _Result([{"semver": "1.4.0", "threshold": 0.3}])

    def arg(self, method):
        return next(a[0] for n, a, _ in self.ops if n == method)


class FakeClient:
    def __init__(self):
        self.calls = []

    def table(self, name):
        return _FakeQuery(self, name)


@pytest.fixture
def imbalanced_scores():
    """Imbalanced synthetic set (~15% positives) with a usable probability signal."""
    rng = np.random.RandomState(1)
    n = 2000
    y = (rng.uniform(size=n) < 0.15).astype(int)
    # Positives score higher on average, but with overlap.
    proba = np.clip(np.where(y == 1,
                             rng.normal(0.55, 0.2, n),
                             rng.normal(0.30, 0.2, n)), 0, 1)
    return y, proba


def test_fn_heavy_cost_pushes_threshold_below_half(imbalanced_scores):
    y, proba = imbalanced_scores
    t = threshold.optimize_threshold(y, proba)  # FN_COST=5, FP_COST=1
    assert t < 0.5, f"expected threshold < 0.5 with FN=5xFP, got {t}"
    print(f"chosen threshold = {t}")


def test_equal_costs_threshold_not_forced_low(imbalanced_scores):
    y, proba = imbalanced_scores
    t_equal = threshold.optimize_threshold(y, proba, fn_cost=1, fp_cost=1)
    t_fn = threshold.optimize_threshold(y, proba, fn_cost=5, fp_cost=1)
    # Heavier FN penalty never raises the threshold above the equal-cost choice.
    assert t_fn <= t_equal


def test_persist_threshold_updates_model_version():
    fake = FakeClient()
    row = threshold.persist_threshold("1.4.0", 0.3, client=fake)

    call = fake.calls[0]
    assert call.table == "model_versions"
    assert call.arg("update") == {"threshold": 0.3}
    assert ("eq", ("semver", "1.4.0"), {}) in call.ops
    assert row["semver"] == "1.4.0"

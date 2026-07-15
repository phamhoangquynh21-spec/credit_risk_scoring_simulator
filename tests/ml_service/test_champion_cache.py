"""The champion cache must never outlive a governance-approved promotion.

Regression cover for a real governance hole: get_champion was cached for the
process lifetime, so an approved promotion kept scoring on the retired model
(and its old threshold) until someone restarted the service.
"""
from __future__ import annotations

import pytest

import services.ml.persistence as persistence


class _FakeQuery:
    def __init__(self, state):
        self._state = state

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        self._state["reads"] += 1
        return type("R", (), {"data": list(self._state["rows"])})()


class _FakeClient:
    def __init__(self, state):
        self._state = state

    def table(self, name):
        assert name == "model_versions"
        return _FakeQuery(self._state)


@pytest.fixture
def champ_state(monkeypatch):
    """Fake DB holding the current champion row; counts reads."""
    state = {"rows": [{"id": "mv-1", "semver": "1.0.0", "threshold": 0.5}], "reads": 0}
    monkeypatch.setattr(persistence, "service_client", lambda: _FakeClient(state))
    persistence.invalidate_champion_cache()
    yield state
    persistence.invalidate_champion_cache()


def test_champion_is_cached_within_the_ttl(champ_state):
    """Hot paths must not hit the DB on every request."""
    assert persistence.get_champion()["semver"] == "1.0.0"
    assert persistence.get_champion()["semver"] == "1.0.0"
    assert champ_state["reads"] == 1


def test_promotion_is_picked_up_after_ttl_without_restart(champ_state, monkeypatch):
    """THE BUG: a promotion used to need a service restart to take effect."""
    assert persistence.get_champion()["threshold"] == 0.5
    # Governance promotes a new champion in the DB (e.g. via a script or
    # another instance) — no restart, no in-process invalidation.
    champ_state["rows"] = [{"id": "mv-2", "semver": "1.1.0-tuned", "threshold": 0.34}]
    monkeypatch.setattr(persistence, "CHAMPION_CACHE_TTL_SECONDS", 0)  # TTL elapses
    champ = persistence.get_champion()
    assert champ["semver"] == "1.1.0-tuned"
    assert champ["threshold"] == 0.34


def test_invalidate_forces_an_immediate_reread(champ_state):
    """Explicit bust (used by the promote route) switches over at once."""
    assert persistence.get_champion()["semver"] == "1.0.0"
    champ_state["rows"] = [{"id": "mv-2", "semver": "1.1.0-tuned", "threshold": 0.34}]
    persistence.invalidate_champion_cache()
    assert persistence.get_champion()["semver"] == "1.1.0-tuned"
    assert champ_state["reads"] == 2


def test_no_champion_raises_and_is_not_cached(champ_state):
    """A transient empty result must not be cached as the champion."""
    champ_state["rows"] = []
    with pytest.raises(Exception):
        persistence.get_champion()
    champ_state["rows"] = [{"id": "mv-1", "semver": "1.0.0", "threshold": 0.5}]
    assert persistence.get_champion()["semver"] == "1.0.0"

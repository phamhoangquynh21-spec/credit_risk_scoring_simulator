import services.ml.routers.models as models_router
from services.ml.auth import Principal, get_principal
from services.ml.main import create_app
from fastapi.testclient import TestClient


def _client(monkeypatch, role, fake_promote):
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal("gov-1", role)
    monkeypatch.setattr(models_router.db, "promote_model", fake_promote)
    return TestClient(app)


def test_promote_forbidden_for_analyst(monkeypatch):
    def _should_not_run(*a, **k):
        raise AssertionError("promote_model must not be reached for analyst")
    r = _client(monkeypatch, "analyst", _should_not_run).post(
        "/api/v1/models/1.2.0/promote", json={"to_stage": "champion"})
    assert r.status_code == 403


def test_promote_champion_passes_approved_by(monkeypatch):
    seen = {}

    def fake_promote(semver, to_stage, approved_by=None, client=None):
        seen.update(semver=semver, to_stage=to_stage, approved_by=approved_by)
        return {"semver": semver, "stage": to_stage, "approved_by": approved_by}

    r = _client(monkeypatch, "governance", fake_promote).post(
        "/api/v1/models/1.2.0/promote", json={"to_stage": "champion"})
    assert r.status_code == 200
    assert seen["approved_by"] == "gov-1"      # the calling principal's id
    assert seen["to_stage"] == "champion"
    assert r.json()["approved_by"] == "gov-1"


def test_promote_surfaces_gate_error_as_400(monkeypatch):
    def fake_promote(semver, to_stage, approved_by=None, client=None):
        raise ValueError("model version '9.9.9' not found")

    r = _client(monkeypatch, "governance", fake_promote).post(
        "/api/v1/models/9.9.9/promote", json={"to_stage": "champion"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "promotion_rejected"

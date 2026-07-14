import services.ml.routers.audit as audit_router
from services.ml.auth import Principal, get_principal
from services.ml.main import create_app
from fastapi.testclient import TestClient

_ROWS = [
    {"id": 2, "actor_id": None, "action": "promote_model",
     "entity_type": "model_versions", "entity_id": "1.2.0",
     "detail": {"to_stage": "champion"}, "created_at": "2026-07-13T00:00:00Z"},
    {"id": 1, "actor_id": None, "action": "promote_model",
     "entity_type": "model_versions", "entity_id": "1.1.0",
     "detail": {"to_stage": "staging"}, "created_at": "2026-07-12T00:00:00Z"},
]


def _client(monkeypatch, role):
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal("user-1", role)
    monkeypatch.setattr(audit_router, "_recent_events", lambda limit: _ROWS)
    return TestClient(app)


def test_audit_forbidden_for_analyst(monkeypatch):
    r = _client(monkeypatch, "analyst").get("/api/v1/audit/events")
    assert r.status_code == 403


def test_audit_json_for_governance(monkeypatch):
    r = _client(monkeypatch, "governance").get("/api/v1/audit/events")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert body["events"][0]["action"] == "promote_model"


def test_audit_csv_format(monkeypatch):
    r = _client(monkeypatch, "compliance").get(
        "/api/v1/audit/events?format=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "action" in r.text.splitlines()[0]      # header row

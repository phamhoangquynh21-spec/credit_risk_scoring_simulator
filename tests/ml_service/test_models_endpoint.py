import services.ml.routers.models as models_router
from services.ml.auth import Principal, get_principal


def test_models_current(client, monkeypatch):
    monkeypatch.setattr(models_router, "get_champion",
                        lambda: {"id": "m1", "semver": "1.0.0-real-uci",
                                 "threshold": 0.5})
    client.app.dependency_overrides[get_principal] = lambda: Principal("user-1", "analyst")
    r = client.get("/api/v1/models/current")
    assert r.status_code == 200
    body = r.json()
    assert body["semver"] == "1.0.0-real-uci"
    assert body["algo"] == "xgboost"          # from the loaded bundle
    assert "auc_roc" in body["metrics"]

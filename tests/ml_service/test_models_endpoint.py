import services.ml.routers.models as models_router


def test_models_current(client, monkeypatch):
    monkeypatch.setattr(models_router, "get_champion",
                        lambda: {"id": "m1", "semver": "1.0.0-real-uci",
                                 "threshold": 0.5})
    r = client.get("/api/v1/models/current")
    assert r.status_code == 200
    body = r.json()
    assert body["semver"] == "1.0.0-real-uci"
    assert body["algo"] == "xgboost"          # from the loaded bundle
    assert "auc_roc" in body["metrics"]

import services.ml.auth as auth
import services.ml.routers.predict as predict_router
from services.ml.auth import Principal, get_principal
from services.ml.main import create_app
from fastapi.testclient import TestClient


def _valid_applicant():
    return {"limit_bal": 120000, "sex": 2, "education": 2, "marriage": 1, "age": 35,
            "pay_0": 0, "pay_2": 0, "pay_3": 0, "pay_4": 0, "pay_5": 0, "pay_6": 0,
            "bill_amt1": 5000, "bill_amt2": 4000, "bill_amt3": 3000,
            "bill_amt4": 2000, "bill_amt5": 1000, "bill_amt6": 500,
            "pay_amt1": 2000, "pay_amt2": 2000, "pay_amt3": 1000,
            "pay_amt4": 1000, "pay_amt5": 500, "pay_amt6": 500}


def _client_with_auth(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal("user-1", "analyst")
    # Persist + champion are stubbed so the endpoint test does not hit network.
    monkeypatch.setattr(predict_router, "save_prediction",
                        lambda *a, **k: "pred-123")
    monkeypatch.setattr(predict_router, "get_champion",
                        lambda: {"id": "m1", "semver": "1.0.0-real-uci",
                                 "threshold": 0.5})
    return TestClient(app)


def test_predict_requires_auth():
    c = TestClient(create_app())
    r = c.post("/api/v1/predict", json=_valid_applicant())
    assert r.status_code == 401


def test_predict_returns_scored_response(monkeypatch):
    c = _client_with_auth(monkeypatch)
    r = c.post("/api/v1/predict", json=_valid_applicant())
    assert r.status_code == 200
    body = r.json()
    assert body["risk_band"] in {"Low", "Medium", "High"}
    assert 0 <= body["risk_score"] <= 100
    assert body["prediction_id"] == "pred-123"
    assert body["model_version"]
    # Stage 2.1 additive fields: threshold + decision-support recommendation.
    assert body["threshold_used"] == 0.5
    assert body["recommendation"] in {"approve", "decline"}
    expected = "decline" if body["probability"] >= 0.5 else "approve"
    assert body["recommendation"] == expected


def test_predict_rejects_bad_schema(monkeypatch):
    c = _client_with_auth(monkeypatch)
    bad = _valid_applicant(); bad["age"] = -5
    r = c.post("/api/v1/predict", json=bad)
    assert r.status_code == 422

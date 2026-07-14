import services.ml.routers.explain as explain_router
from services.ml.auth import Principal, get_principal
from services.ml.main import create_app
from src.ml.reason_codes import CONTRIBUTION_DISCLAIMER
from fastapi.testclient import TestClient


def _applicant():
    return {"limit_bal": 50000, "sex": 1, "education": 3, "marriage": 2, "age": 24,
            "pay_0": 3, "pay_2": 2, "pay_3": 2, "pay_4": 1, "pay_5": 0, "pay_6": 0,
            "bill_amt1": 48000, "bill_amt2": 47000, "bill_amt3": 46000,
            "bill_amt4": 45000, "bill_amt5": 44000, "bill_amt6": 43000,
            "pay_amt1": 1000, "pay_amt2": 1000, "pay_amt3": 1000,
            "pay_amt4": 1000, "pay_amt5": 1000, "pay_amt6": 1000}


def _client(monkeypatch=None):
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal("user-1", "analyst")
    if monkeypatch is not None:
        monkeypatch.setattr(explain_router, "get_champion",
                            lambda: {"id": "m1", "semver": "1.0.0-real-uci",
                                     "threshold": 0.5})
    return TestClient(app)


def test_explain_requires_auth():
    r = TestClient(create_app()).post("/api/v1/explain", json=_applicant())
    assert r.status_code == 401


def test_explain_returns_top_factors(monkeypatch):
    r = _client(monkeypatch).post("/api/v1/explain", json=_applicant())
    assert r.status_code == 200
    body = r.json()
    assert body["risk_band"] in {"Low", "Medium", "High"}
    assert 1 <= len(body["top_factors"]) <= 5
    assert body["top_factors"][0]["direction"] in {"increases", "decreases"}
    # Stage 2.2 additive fields: reason codes + mandatory non-causal disclaimer.
    assert body["disclaimer"] == CONTRIBUTION_DISCLAIMER
    assert len(body["reason_codes"]) == len(body["top_factors"])
    assert body["reason_codes"][0]["direction"] in {"increases", "decreases"}

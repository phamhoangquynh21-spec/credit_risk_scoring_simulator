from services.ml.auth import Principal, get_principal
from services.ml.main import create_app
from fastapi.testclient import TestClient


def _applicant():
    return {"limit_bal": 50000, "sex": 1, "education": 3, "marriage": 2, "age": 24,
            "pay_0": 3, "pay_2": 2, "pay_3": 2, "pay_4": 1, "pay_5": 0, "pay_6": 0,
            "bill_amt1": 48000, "bill_amt2": 47000, "bill_amt3": 46000,
            "bill_amt4": 45000, "bill_amt5": 44000, "bill_amt6": 43000,
            "pay_amt1": 1000, "pay_amt2": 1000, "pay_amt3": 1000,
            "pay_amt4": 1000, "pay_amt5": 1000, "pay_amt6": 1000}


def _client():
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal("user-1", "analyst")
    return TestClient(app)


def test_explain_requires_auth():
    r = TestClient(create_app()).post("/api/v1/explain", json=_applicant())
    assert r.status_code == 401


def test_explain_returns_top_factors():
    r = _client().post("/api/v1/explain", json=_applicant())
    assert r.status_code == 200
    body = r.json()
    assert body["risk_band"] in {"Low", "Medium", "High"}
    assert 1 <= len(body["top_factors"]) <= 5
    assert body["top_factors"][0]["direction"] in {"increases", "decreases"}

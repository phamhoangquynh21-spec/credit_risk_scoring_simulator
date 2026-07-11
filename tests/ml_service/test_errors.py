from fastapi.testclient import TestClient

from services.ml.auth import Principal, get_principal
from services.ml.main import create_app


def _valid_applicant(age=35):
    return {"limit_bal": 120000, "sex": 2, "education": 2, "marriage": 1, "age": age,
            "pay_0": 0, "pay_2": 0, "pay_3": 0, "pay_4": 0, "pay_5": 0, "pay_6": 0,
            "bill_amt1": 5000, "bill_amt2": 4000, "bill_amt3": 3000,
            "bill_amt4": 2000, "bill_amt5": 1000, "bill_amt6": 500,
            "pay_amt1": 2000, "pay_amt2": 2000, "pay_amt3": 1000,
            "pay_amt4": 1000, "pay_amt5": 500, "pay_amt6": 500}


def _client_with_auth():
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal("user-1", "analyst")
    return TestClient(app)


def test_validation_error_uses_error_envelope():
    c = _client_with_auth()
    bad = _valid_applicant()
    bad["age"] = -5
    r = c.post("/api/v1/predict", json=bad)
    assert r.status_code == 422
    body = r.json()
    assert "detail" not in body
    assert body["error"]["code"] == "validation_error"


def test_validation_error_envelope_has_request_id():
    c = _client_with_auth()
    bad = _valid_applicant()
    bad["age"] = -5
    r = c.post("/api/v1/predict", json=bad, headers={"x-request-id": "req-123"})
    assert r.status_code == 422
    assert r.json()["error"]["request_id"] == "req-123"

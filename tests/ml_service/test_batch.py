import services.ml.routers.predict as predict_router
from services.ml.auth import Principal, get_principal
from services.ml.main import create_app
from fastapi.testclient import TestClient


def _applicant(age=35):
    return {"limit_bal": 120000, "sex": 2, "education": 2, "marriage": 1, "age": age,
            "pay_0": 0, "pay_2": 0, "pay_3": 0, "pay_4": 0, "pay_5": 0, "pay_6": 0,
            "bill_amt1": 5000, "bill_amt2": 4000, "bill_amt3": 3000,
            "bill_amt4": 2000, "bill_amt5": 1000, "bill_amt6": 500,
            "pay_amt1": 2000, "pay_amt2": 2000, "pay_amt3": 1000,
            "pay_amt4": 1000, "pay_amt5": 500, "pay_amt6": 500}


def _client(monkeypatch, existing=None):
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal("user-1", "analyst")
    saved = []
    monkeypatch.setattr(predict_router, "find_existing",
                        lambda uid, h: (existing or {}).get(h))
    def fake_save(uid, feats, scored, factors, portfolio_id=None):
        pid = f"pred-{len(saved)}"; saved.append(pid); return pid
    monkeypatch.setattr(predict_router, "save_prediction", fake_save)
    return TestClient(app), saved


def test_batch_scores_all(monkeypatch):
    c, saved = _client(monkeypatch)
    r = c.post("/api/v1/predict/batch",
               json={"applicants": [_applicant(30), _applicant(40)]})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert len(body["results"]) == 2
    assert len(saved) == 2                    # two new inserts


def test_batch_idempotent_reuses_existing(monkeypatch):
    from services.ml.logging_config import input_hash
    from services.ml.schemas import Applicant
    a = _applicant(30)
    # Pre-seed one applicant's hash as already-persisted. Hash must be computed
    # over the same representation the route uses (applicant.model_dump(),
    # post pydantic type-coercion), not the raw request dict, since e.g.
    # limit_bal is int here but coerces to float on validation.
    h = input_hash(Applicant(**a).model_dump())
    c, saved = _client(monkeypatch, existing={h: "pred-existing"})
    r = c.post("/api/v1/predict/batch", json={"applicants": [a]},
               headers={"Idempotency-Key": "abc"})
    assert r.status_code == 200
    assert r.json()["results"][0]["prediction_id"] == "pred-existing"
    assert saved == []                        # no new insert for the existing row


def test_batch_echoes_idempotency_key_header(monkeypatch):
    c, saved = _client(monkeypatch)
    r = c.post("/api/v1/predict/batch",
               json={"applicants": [_applicant(30)]},
               headers={"Idempotency-Key": "my-key-123"})
    assert r.status_code == 200
    assert r.headers["Idempotency-Key"] == "my-key-123"


def test_batch_without_idempotency_key_has_no_header(monkeypatch):
    c, saved = _client(monkeypatch)
    r = c.post("/api/v1/predict/batch",
               json={"applicants": [_applicant(30)]})
    assert r.status_code == 200
    assert "Idempotency-Key" not in r.headers

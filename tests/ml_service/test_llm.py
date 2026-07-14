import services.ml.routers.llm as llm_router
from services.ml.auth import Principal, get_principal
from services.ml.main import create_app
from src.llm.memo import GroundingError
from src.ml.reason_codes import CONTRIBUTION_DISCLAIMER
from fastapi.testclient import TestClient


def _applicant():
    return {"limit_bal": 50000, "sex": 1, "education": 3, "marriage": 2, "age": 24,
            "pay_0": 3, "pay_2": 2, "pay_3": 2, "pay_4": 1, "pay_5": 0, "pay_6": 0,
            "bill_amt1": 48000, "bill_amt2": 47000, "bill_amt3": 46000,
            "bill_amt4": 45000, "bill_amt5": 44000, "bill_amt6": 43000,
            "pay_amt1": 1000, "pay_amt2": 1000, "pay_amt3": 1000,
            "pay_amt4": 1000, "pay_amt5": 1000, "pay_amt6": 1000}


def _client(monkeypatch, role="analyst", persist=True):
    """Client with champion stubbed. When persist=True the persistence seam is
    stubbed to succeed offline; individual tests override it as needed."""
    app = create_app()
    app.dependency_overrides[get_principal] = lambda: Principal("user-1", role)
    monkeypatch.setattr(llm_router, "get_champion",
                        lambda: {"id": "m1", "semver": "1.0.0-real-uci",
                                 "threshold": 0.5})
    if persist:
        monkeypatch.setattr(llm_router, "save_prediction",
                            lambda *a, **k: "pred-abc")
        monkeypatch.setattr(llm_router, "persist_memo",
                            lambda memo, pid, **k: {"review_status": "draft"})
    return TestClient(app)


def test_credit_memo_requires_auth():
    r = TestClient(create_app()).post(
        "/api/v1/llm-reports/credit-memo", json=_applicant())
    assert r.status_code == 401


def test_credit_memo_falls_back_without_key(monkeypatch):
    # No ANTHROPIC_API_KEY -> deterministic template fallback, still grounded.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = _client(monkeypatch).post(
        "/api/v1/llm-reports/credit-memo", json=_applicant())
    assert r.status_code == 200
    body = r.json()
    assert body["fallback_used"] is True
    assert body["provider"] == "template"
    assert body["grounded"] is True
    assert body["review_status"] == "draft"
    assert CONTRIBUTION_DISCLAIMER in body["memo_text"]


def test_credit_memo_persists_memo_with_prediction_id(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(llm_router, "save_prediction", lambda *a, **k: "pred-xyz")
    seen = {}

    def fake_persist(memo, pid, **k):
        seen.update(pid=pid, memo=memo)
        return {"review_status": "draft"}

    monkeypatch.setattr(llm_router, "persist_memo", fake_persist)
    r = _client(monkeypatch, persist=False).post(
        "/api/v1/llm-reports/credit-memo", json=_applicant())
    assert r.status_code == 200
    body = r.json()
    assert seen["pid"] == "pred-xyz"                 # persist_memo got the pid
    assert seen["memo"]["memo_text"] == body["memo_text"]
    assert body["prediction_id"] == "pred-xyz"
    assert body["review_status"] == "draft"


def test_credit_memo_survives_persistence_failure(monkeypatch):
    # Persistence unavailable (offline / DB down) must NOT break memo generation.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def boom(*a, **k):
        raise RuntimeError("supabase down")

    monkeypatch.setattr(llm_router, "save_prediction", boom)
    r = _client(monkeypatch, persist=False).post(
        "/api/v1/llm-reports/credit-memo", json=_applicant())
    assert r.status_code == 200
    body = r.json()
    assert body["prediction_id"] is None
    assert CONTRIBUTION_DISCLAIMER in body["memo_text"]


def test_credit_memo_grounding_error_falls_back(monkeypatch):
    # A live provider returning ungrounded text raises GroundingError; the
    # endpoint must fall back to the template, not 500.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    calls = {"n": 0}
    real_generate = llm_router.generate_memo

    def fake_generate(inputs, provider):
        calls["n"] += 1
        if provider is not None:
            raise GroundingError("memo rejected: not grounded")
        return real_generate(inputs, None)      # template path

    monkeypatch.setattr(llm_router, "generate_memo", fake_generate)
    r = _client(monkeypatch).post(
        "/api/v1/llm-reports/credit-memo", json=_applicant())
    assert r.status_code == 200
    body = r.json()
    assert calls["n"] == 2                       # provider attempt + fallback
    assert body["fallback_used"] is True
    assert CONTRIBUTION_DISCLAIMER in body["memo_text"]

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

import services.ml.auth as auth
from services.ml.auth import get_principal, Principal
from services.ml.errors import AppError, app_error_handler


def _app():
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)

    @app.get("/whoami")
    def whoami(p: Principal = Depends(get_principal)):
        return {"user_id": p.user_id, "role": p.role}

    return app


def test_missing_token_is_401():
    c = TestClient(_app())
    r = c.get("/whoami")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_valid_token_returns_principal(monkeypatch):
    monkeypatch.setattr(auth, "verify_token",
                        lambda token: ("user-123", "analyst"))
    c = TestClient(_app())
    r = c.get("/whoami", headers={"Authorization": "Bearer good"})
    assert r.status_code == 200
    assert r.json() == {"user_id": "user-123", "role": "analyst"}


def test_invalid_token_is_401(monkeypatch):
    def boom(token):
        raise AppError("unauthorized", "bad token", 401)
    monkeypatch.setattr(auth, "verify_token", boom)
    c = TestClient(_app())
    r = c.get("/whoami", headers={"Authorization": "Bearer bad"})
    assert r.status_code == 401

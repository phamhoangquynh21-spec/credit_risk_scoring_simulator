import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

import services.ml.auth as auth
from services.ml.auth import get_principal, require_role, Principal
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


def _app_with_role(role: str):
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)

    @app.get("/manager-only")
    def manager_only(p: Principal = Depends(require_role("manager"))):
        return {"user_id": p.user_id, "role": p.role}

    app.dependency_overrides[get_principal] = lambda: Principal(
        user_id="user-123", role=role)
    return app


def test_require_role_denies_role_not_in_set():
    c = TestClient(_app_with_role("analyst"))
    r = c.get("/manager-only")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_require_role_allows_admin_bypass():
    c = TestClient(_app_with_role("admin"))
    r = c.get("/manager-only")
    assert r.status_code == 200
    assert r.json() == {"user_id": "user-123", "role": "admin"}


def test_require_role_allows_matching_role():
    c = TestClient(_app_with_role("manager"))
    r = c.get("/manager-only")
    assert r.status_code == 200
    assert r.json() == {"user_id": "user-123", "role": "manager"}

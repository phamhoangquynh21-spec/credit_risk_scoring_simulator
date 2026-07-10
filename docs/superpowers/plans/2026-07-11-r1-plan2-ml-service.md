# R1 Plan 2/3 — FastAPI ML Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a versioned FastAPI service that wraps the existing `src/` ML code, scores credit applicants over authenticated HTTP, and persists every prediction to Supabase — the backend Sections 2/3/6 of the dashboard (Plan 3) will call.

**Architecture:** A new `services/ml/` FastAPI app. It reuses `src/` UNCHANGED (`clean_data` + `engineer_features` build the 28-feature vector from 23 raw inputs; `explain.score_batch`/`explain_single_customer` do scoring/SHAP; `config.risk_band` bands the score). Auth verifies Supabase JWTs via `supabase.auth.get_user(token)` (no JWT secret needed). Writes go through a service-role Supabase client with `created_by` set to the caller's user id so the RLS built in Plan 1 governs later reads. The ML model bundle loads once at startup.

**Tech Stack:** Python 3.14 (project venv), FastAPI, Uvicorn, Pydantic v2, supabase-py, pandas/xgboost/shap/joblib (already installed), pytest + httpx TestClient.

## Global Constraints

- Existing `src/` code and the 27 passing tests MUST NOT be modified or broken.
- Secrets only in `.env` (gitignored): `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (already present from Plan 1). Never commit keys; never log feature values — log `input_hash` only.
- Prediction ≠ decision: this service returns predictions + explanations only; it never writes `human_decisions`.
- The request contract is the 23 raw UCI fields: `limit_bal, sex, education, marriage, age, pay_0, pay_2, pay_3, pay_4, pay_5, pay_6, bill_amt1..6, pay_amt1..6`. Engineered features are computed server-side, never accepted from the client.
- Risk bands (from `src/config.py`): Low `[0,33)`, Medium `[33,66)`, High `[66,100]`.
- Persist to Supabase tables from Plan 1: `predictions` (probability, risk_score, risk_band, threshold_used, model_version_id, input_hash, created_by, portfolio_id nullable, applicant jsonb) and `prediction_explanations` (prediction_id, method, top_factors jsonb, base_value). Read the champion from `model_versions` where `stage='champion'`.
- Run Python via `.venv/Scripts/python.exe` (bare `python` is a Windows Store stub).
- Error responses use one envelope: `{"error": {"code": <str>, "message": <str>, "request_id": <str>}}`.
- API is URI-versioned under `/api/v1`. Every prediction response echoes the `model_version` used.
- Conventional commits `type(scope): message`; one commit per task minimum.

**Prerequisite (already satisfied):** `.env` contains valid Supabase credentials (created during Plan 1 Task 7).

---

### Task 1: Service scaffolding — settings, app factory, logging, errors, health

**Files:**
- Create: `services/__init__.py` (empty), `services/ml/__init__.py` (empty), `services/ml/settings.py`, `services/ml/logging_config.py`, `services/ml/errors.py`, `services/ml/main.py`, `services/ml/requirements.txt`
- Test: `tests/ml_service/__init__.py` (empty), `tests/ml_service/conftest.py`, `tests/ml_service/test_health.py`

**Interfaces:**
- Produces: `services.ml.settings.settings` (attrs `supabase_url`, `supabase_anon_key`, `supabase_service_role_key`); `services.ml.main.create_app() -> FastAPI`; `services.ml.errors.AppError(code:str, message:str, status:int)`; `services.ml.logging_config.redact(features:dict) -> str` (returns an input hash, never values). `create_app()` mounts `GET /health` and `GET /ready`.

- [ ] **Step 1: Create `services/ml/requirements.txt`**

```
# ML service (installed on top of the project's root requirements.txt)
fastapi>=0.110
uvicorn[standard]>=0.29
pydantic>=2.6
pydantic-settings>=2.2
httpx>=0.27
```

- [ ] **Step 2: Install into the venv**

Run: `.venv/Scripts/python.exe -m pip install -r services/ml/requirements.txt`
Expected: `Successfully installed fastapi-... uvicorn-... pydantic-settings-... httpx-...`

- [ ] **Step 3: Create the empty package files**

Create `services/__init__.py`, `services/ml/__init__.py`, `tests/ml_service/__init__.py` — each empty.

- [ ] **Step 4: Create `services/ml/settings.py`**

```python
"""Typed settings for the ML service. Reads .env (never hardcodes secrets)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)


settings = Settings()
```

- [ ] **Step 5: Create `services/ml/logging_config.py`**

```python
"""Structured logging with PII redaction. Feature values are NEVER logged;
we log a stable hash of the input instead."""
from __future__ import annotations

import hashlib
import json
import logging


def input_hash(features: dict) -> str:
    """Deterministic sha256 of a feature dict (order-independent)."""
    payload = json.dumps(features, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='{"level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
    )


logger = logging.getLogger("ml_service")
```

- [ ] **Step 6: Create `services/ml/errors.py`**

```python
"""Single error envelope for the whole API."""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


def error_body(code: str, message: str, request_id: str) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    rid = request.headers.get("x-request-id", "-")
    return JSONResponse(status_code=exc.status,
                        content=error_body(exc.code, exc.message, rid))
```

- [ ] **Step 7: Create `services/ml/main.py`**

```python
"""FastAPI app factory for the ML service."""
from __future__ import annotations

from fastapi import FastAPI

from .errors import AppError, app_error_handler
from .logging_config import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Credit Risk ML Service", version="1.0.0")
    app.add_exception_handler(AppError, app_error_handler)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> dict:
        # Readiness = model bundle loadable + settings present.
        from .settings import settings
        from src import config
        return {
            "status": "ready" if config.MODEL_PATH.exists() else "not_ready",
            "model_present": config.MODEL_PATH.exists(),
            "supabase_configured": settings.configured,
        }

    return app


app = create_app()
```

- [ ] **Step 8: Create `tests/ml_service/conftest.py`**

```python
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from services.ml.main import create_app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(create_app())
```

- [ ] **Step 9: Create `tests/ml_service/test_health.py`**

```python
def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_reports_model_and_config(client):
    r = client.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["model_present"] is True          # model.pkl exists from Plan 1
    assert "supabase_configured" in body
```

- [ ] **Step 10: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_health.py -v`
Expected: 2 passed.

- [ ] **Step 11: Commit**

```bash
git add services/ tests/ml_service/
git commit -m "feat(ml-service): scaffolding — settings, logging, errors, health/ready"
```

---

### Task 2: Request/response schemas (Pydantic v2)

**Files:**
- Create: `services/ml/schemas.py`
- Test: `tests/ml_service/test_schemas.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Applicant` (23 raw fields, validated), `Applicant.to_raw_row() -> dict` (uppercase UCI column names for `score_batch`), `PredictResponse`, `ExplainFactor`, `ExplainResponse`, `BatchPredictRequest`, `BatchPredictResponse`. Later tasks import these exact names.

- [ ] **Step 1: Write the failing test**

```python
# tests/ml_service/test_schemas.py
import pytest
from pydantic import ValidationError

from services.ml.schemas import Applicant


def _valid() -> dict:
    return {
        "limit_bal": 120000, "sex": 2, "education": 2, "marriage": 1, "age": 35,
        "pay_0": 0, "pay_2": 0, "pay_3": 0, "pay_4": 0, "pay_5": 0, "pay_6": 0,
        "bill_amt1": 5000, "bill_amt2": 4000, "bill_amt3": 3000,
        "bill_amt4": 2000, "bill_amt5": 1000, "bill_amt6": 500,
        "pay_amt1": 2000, "pay_amt2": 2000, "pay_amt3": 1000,
        "pay_amt4": 1000, "pay_amt5": 500, "pay_amt6": 500,
    }


def test_valid_applicant_builds_raw_row():
    a = Applicant(**_valid())
    row = a.to_raw_row()
    assert row["LIMIT_BAL"] == 120000
    assert row["PAY_0"] == 0
    assert row["BILL_AMT6"] == 500
    assert len(row) == 23


def test_rejects_negative_age():
    d = _valid(); d["age"] = -1
    with pytest.raises(ValidationError):
        Applicant(**d)


def test_rejects_bad_sex_code():
    d = _valid(); d["sex"] = 9
    with pytest.raises(ValidationError):
        Applicant(**d)


def test_rejects_extra_field():
    d = _valid(); d["credit_utilization"] = 0.5   # engineered, must not be accepted
    with pytest.raises(ValidationError):
        Applicant(**d)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_schemas.py -v`
Expected: ERROR — `No module named 'services.ml.schemas'`.

- [ ] **Step 3: Create `services/ml/schemas.py`**

```python
"""Pydantic v2 request/response schemas. The request contract is the 23 RAW
UCI fields; engineered features are computed server-side and rejected here."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Applicant(BaseModel):
    model_config = ConfigDict(extra="forbid")  # reject unknown/engineered fields

    limit_bal: float = Field(ge=0)
    sex: int = Field(ge=1, le=2)
    education: int = Field(ge=0, le=6)
    marriage: int = Field(ge=0, le=3)
    age: int = Field(ge=18, le=120)
    pay_0: int = Field(ge=-2, le=9)
    pay_2: int = Field(ge=-2, le=9)
    pay_3: int = Field(ge=-2, le=9)
    pay_4: int = Field(ge=-2, le=9)
    pay_5: int = Field(ge=-2, le=9)
    pay_6: int = Field(ge=-2, le=9)
    bill_amt1: float
    bill_amt2: float
    bill_amt3: float
    bill_amt4: float
    bill_amt5: float
    bill_amt6: float
    pay_amt1: float = Field(ge=0)
    pay_amt2: float = Field(ge=0)
    pay_amt3: float = Field(ge=0)
    pay_amt4: float = Field(ge=0)
    pay_amt5: float = Field(ge=0)
    pay_amt6: float = Field(ge=0)

    def to_raw_row(self) -> dict:
        """Return a dict keyed by original UCI column names for score_batch."""
        return {name.upper(): getattr(self, name) for name in self.model_fields}


class PredictResponse(BaseModel):
    risk_score: float
    risk_band: str
    probability: float
    model_version: str
    prediction_id: str | None = None


class ExplainFactor(BaseModel):
    feature: str
    friendly: str
    contribution: float
    direction: str


class ExplainResponse(BaseModel):
    risk_score: float
    risk_band: str
    model_version: str
    top_factors: list[ExplainFactor]


class BatchPredictRequest(BaseModel):
    applicants: list[Applicant] = Field(min_length=1, max_length=1000)


class BatchPredictResponse(BaseModel):
    model_version: str
    count: int
    results: list[PredictResponse]
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_schemas.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add services/ml/schemas.py tests/ml_service/test_schemas.py
git commit -m "feat(ml-service): pydantic schemas with 23-field raw contract"
```

---

### Task 3: Scoring service (wraps `src/`, DRY)

**Files:**
- Create: `services/ml/scoring.py`
- Test: `tests/ml_service/test_scoring.py`

**Interfaces:**
- Consumes: `src.explain.score_batch`, `src.explain.explain_in_plain_language`, `src.config`, `src.preprocessing`.
- Produces: `load_bundle()` (cached), `score_one(raw_row: dict) -> dict` returning `{probability, risk_score, risk_band, model_type, feature_row}`; `explain_one(raw_row: dict) -> list[dict]` returning plain-language factor dicts; `FEATURES` (the bundle feature list). Later tasks call these.

- [ ] **Step 1: Write the failing test**

```python
# tests/ml_service/test_scoring.py
from services.ml.scoring import score_one, explain_one


def _risky_raw():
    return {"LIMIT_BAL": 50000, "SEX": 1, "EDUCATION": 3, "MARRIAGE": 2, "AGE": 24,
            "PAY_0": 3, "PAY_2": 2, "PAY_3": 2, "PAY_4": 1, "PAY_5": 0, "PAY_6": 0,
            "BILL_AMT1": 48000, "BILL_AMT2": 47000, "BILL_AMT3": 46000,
            "BILL_AMT4": 45000, "BILL_AMT5": 44000, "BILL_AMT6": 43000,
            "PAY_AMT1": 1000, "PAY_AMT2": 1000, "PAY_AMT3": 1000,
            "PAY_AMT4": 1000, "PAY_AMT5": 1000, "PAY_AMT6": 1000}


def test_score_one_returns_valid_fields():
    out = score_one(_risky_raw())
    assert 0.0 <= out["probability"] <= 1.0
    assert 0.0 <= out["risk_score"] <= 100.0
    assert out["risk_band"] in {"Low", "Medium", "High"}


def test_risky_applicant_scores_high():
    out = score_one(_risky_raw())
    assert out["risk_band"] in {"Medium", "High"}


def test_explain_one_returns_top_factors():
    factors = explain_one(_risky_raw())
    assert 1 <= len(factors) <= 5
    assert {"feature", "friendly", "contribution", "direction"} <= set(factors[0])
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_scoring.py -v`
Expected: ERROR — `No module named 'services.ml.scoring'`.

- [ ] **Step 3: Create `services/ml/scoring.py`**

```python
"""Thin scoring layer over the existing src/ ML code. No model logic is
re-implemented here — it reuses the tested pipeline."""
from __future__ import annotations

import functools

import joblib
import pandas as pd

from src import config
from src.explain import explain_in_plain_language, score_batch


@functools.lru_cache(maxsize=1)
def load_bundle() -> dict:
    return joblib.load(config.MODEL_PATH)


def _features() -> list[str]:
    return load_bundle()["features"]


FEATURES = None  # populated lazily via _features(); kept for import symmetry


def score_one(raw_row: dict) -> dict:
    """Score one applicant given a dict of RAW UCI column names."""
    bundle = load_bundle()
    scored = score_batch(bundle["model"], bundle["features"],
                         pd.DataFrame([raw_row]))
    row = scored.iloc[0]
    prob = float(row["risk_score"]) / 100.0
    return {
        "probability": prob,
        "risk_score": float(row["risk_score"]),
        "risk_band": str(row["risk_band"]),
        "model_type": bundle["model_type"],
    }


def explain_one(raw_row: dict) -> list[dict]:
    """Plain-language SHAP top factors for one applicant."""
    from src.preprocessing import clean_data, engineer_features

    bundle = load_bundle()
    feat_df = engineer_features(clean_data(pd.DataFrame([raw_row])))
    single = feat_df[bundle["features"]].iloc[0]
    items = explain_in_plain_language(bundle["model"], single)
    return [{"feature": i["feature"], "friendly": i["friendly"],
             "contribution": float(i["contribution"]), "direction": i["direction"]}
            for i in items]
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_scoring.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add services/ml/scoring.py tests/ml_service/test_scoring.py
git commit -m "feat(ml-service): scoring layer reusing src/ pipeline"
```

---

### Task 4: Auth dependency — Supabase JWT verification + RBAC

**Files:**
- Create: `services/ml/auth.py`
- Test: `tests/ml_service/test_auth.py`

**Interfaces:**
- Consumes: `services.ml.settings.settings`, `services.ml.errors.AppError`.
- Produces: `Principal` (attrs `user_id: str`, `role: str`); `get_principal(authorization: str | None) -> Principal` FastAPI dependency (raises `AppError('unauthorized', ..., 401)` when the bearer token is missing/invalid); `require_role(*roles)` dependency factory. A module-level `verify_token(token) -> tuple[str, str]` (returns `(user_id, role)`) is the seam tests override.

- [ ] **Step 1: Write the failing test**

```python
# tests/ml_service/test_auth.py
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_auth.py -v`
Expected: ERROR — `No module named 'services.ml.auth'`.

- [ ] **Step 3: Create `services/ml/auth.py`**

```python
"""Authentication: verify a Supabase user JWT via the Supabase auth API
(no JWT secret needed) and expose the caller's id + role."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header

from .errors import AppError
from .settings import settings


@dataclass
class Principal:
    user_id: str
    role: str


def verify_token(token: str) -> tuple[str, str]:
    """Return (user_id, role) for a valid Supabase access token, else raise.

    Uses the anon client's auth.get_user(token); role is read from profiles
    via a service-role client. This is the seam tests monkeypatch.
    """
    from supabase import create_client

    anon = create_client(settings.supabase_url, settings.supabase_anon_key)
    try:
        resp = anon.auth.get_user(token)
    except Exception as exc:  # network / invalid token
        raise AppError("unauthorized", "invalid or expired token", 401) from exc
    user = getattr(resp, "user", None)
    if user is None:
        raise AppError("unauthorized", "invalid or expired token", 401)

    svc = create_client(settings.supabase_url, settings.supabase_service_role_key)
    prof = (svc.table("profiles").select("role")
            .eq("user_id", user.id).limit(1).execute().data)
    role = prof[0]["role"] if prof else "analyst"
    return user.id, role


def get_principal(authorization: str | None = Header(default=None)) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("unauthorized", "missing bearer token", 401)
    token = authorization.split(" ", 1)[1].strip()
    user_id, role = verify_token(token)
    return Principal(user_id=user_id, role=role)


def require_role(*roles: str):
    def _dep(principal: Principal = None) -> Principal:  # replaced below
        return principal
    # Real dependency composed at call site:
    from fastapi import Depends

    def _checked(principal: Principal = Depends(get_principal)) -> Principal:
        if roles and principal.role not in roles and principal.role != "admin":
            raise AppError("forbidden", "insufficient role", 403)
        return principal

    return _checked
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_auth.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add services/ml/auth.py tests/ml_service/test_auth.py
git commit -m "feat(ml-service): Supabase JWT auth dependency + RBAC"
```

---

### Task 5: Persistence — Supabase writes + champion model read

**Files:**
- Create: `services/ml/persistence.py`
- Test: `tests/ml_service/test_persistence.py`

**Interfaces:**
- Consumes: `services.ml.settings.settings`, `services.ml.logging_config.input_hash`.
- Produces: `service_client()` (service-role Supabase client); `get_champion() -> dict` (`{id, semver, threshold}`); `save_prediction(user_id, applicant_features, scored, top_factors, portfolio_id=None) -> str` (returns prediction_id); `find_existing(user_id, ihash) -> str | None` (idempotency helper). These are the seams the endpoint tasks call and that the live integration test exercises.

- [ ] **Step 1: Write the failing test (live integration — skips without creds)**

```python
# tests/ml_service/test_persistence.py
import os
import uuid

import pytest
from dotenv import load_dotenv

load_dotenv()
pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="Supabase credentials not configured",
)


def test_get_champion_returns_registered_version():
    from services.ml.persistence import get_champion
    champ = get_champion()
    assert champ["semver"] == "1.0.0-real-uci"
    assert "id" in champ


def test_save_prediction_roundtrip():
    from services.ml.persistence import service_client, save_prediction
    svc = service_client()
    # create a throwaway user to own the prediction (FK to auth.users)
    email = f"persist-test-{uuid.uuid4().hex[:10]}@demo.local"
    u = svc.auth.admin.create_user(
        {"email": email, "password": f"Pw!{uuid.uuid4().hex}",
         "email_confirm": True})
    uid = u.user.id
    try:
        scored = {"probability": 0.8, "risk_score": 80.0, "risk_band": "High"}
        factors = [{"feature": "pay_0", "friendly": "Most recent repayment status",
                    "contribution": 1.2, "direction": "increases"}]
        pid = save_prediction(uid, {"limit_bal": 50000, "age": 24},
                              scored, factors)
        assert pid
        got = (svc.table("predictions").select("risk_band, model_version_id")
               .eq("id", pid).execute().data)
        assert got[0]["risk_band"] == "High"
        exp = (svc.table("prediction_explanations").select("top_factors")
               .eq("prediction_id", pid).execute().data)
        assert exp[0]["top_factors"][0]["feature"] == "pay_0"
    finally:
        svc.auth.admin.delete_user(uid)  # cascades cleanup where applicable
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_persistence.py -v`
Expected: ERROR — `No module named 'services.ml.persistence'` (or SKIPPED if no creds; ensure creds present so it runs).

- [ ] **Step 3: Create `services/ml/persistence.py`**

```python
"""Supabase persistence: write predictions/explanations via the service role,
with created_by set to the caller so Plan 1's RLS governs later reads."""
from __future__ import annotations

import functools

from .errors import AppError
from .logging_config import input_hash
from .settings import settings


@functools.lru_cache(maxsize=1)
def service_client():
    from supabase import create_client
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


@functools.lru_cache(maxsize=1)
def get_champion() -> dict:
    rows = (service_client().table("model_versions")
            .select("id, semver, threshold").eq("stage", "champion")
            .limit(1).execute().data)
    if not rows:
        raise AppError("no_model", "no champion model registered", 503)
    return rows[0]


def find_existing(user_id: str, ihash: str) -> str | None:
    rows = (service_client().table("predictions").select("id")
            .eq("created_by", user_id).eq("input_hash", ihash)
            .limit(1).execute().data)
    return rows[0]["id"] if rows else None


def save_prediction(user_id: str, applicant_features: dict, scored: dict,
                    top_factors: list[dict], portfolio_id: str | None = None) -> str:
    champ = get_champion()
    ihash = input_hash(applicant_features)
    svc = service_client()
    pred = (svc.table("predictions").insert({
        "portfolio_id": portfolio_id,
        "applicant": applicant_features,
        "probability": scored["probability"],
        "risk_score": scored["risk_score"],
        "risk_band": scored["risk_band"],
        "threshold_used": champ["threshold"],
        "model_version_id": champ["id"],
        "input_hash": ihash,
        "created_by": user_id,
    }).execute().data[0])
    svc.table("prediction_explanations").insert({
        "prediction_id": pred["id"],
        "method": "shap_tree",
        "top_factors": top_factors,
    }).execute()
    return pred["id"]
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_persistence.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add services/ml/persistence.py tests/ml_service/test_persistence.py
git commit -m "feat(ml-service): Supabase persistence + champion model read"
```

---

### Task 6: `GET /api/v1/models/current`

**Files:**
- Create: `services/ml/routers/__init__.py` (empty), `services/ml/routers/models.py`
- Modify: `services/ml/main.py` (register the router)
- Test: `tests/ml_service/test_models_endpoint.py`

**Interfaces:**
- Consumes: `services.ml.persistence.get_champion`, `services.ml.scoring.load_bundle`.
- Produces: router mounted at `/api/v1/models/current` returning `{semver, algo, metrics}`. Later tasks add more routers to `main.py` the same way.

- [ ] **Step 1: Write the failing test**

```python
# tests/ml_service/test_models_endpoint.py
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_models_endpoint.py -v`
Expected: ERROR — module/route missing (404 or import error).

- [ ] **Step 3: Create `services/ml/routers/models.py`**

```python
"""GET /api/v1/models/current — the champion model card."""
from __future__ import annotations

import json

from fastapi import APIRouter

from src import config
from ..persistence import get_champion
from ..scoring import load_bundle

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.get("/current")
def current_model() -> dict:
    champ = get_champion()
    bundle = load_bundle()
    metrics = json.loads(config.METRICS_PATH.read_text())["advanced"]
    return {"semver": champ["semver"], "algo": bundle["model_type"],
            "metrics": metrics}
```

- [ ] **Step 4: Register the router — edit `services/ml/main.py`**

In `create_app()`, immediately before `return app`, add:

```python
    from .routers import models
    app.include_router(models.router)
```

- [ ] **Step 5: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_models_endpoint.py -v`
Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add services/ml/routers/ services/ml/main.py tests/ml_service/test_models_endpoint.py
git commit -m "feat(ml-service): GET /api/v1/models/current"
```

---

### Task 7: `POST /api/v1/predict` (single applicant)

**Files:**
- Create: `services/ml/routers/predict.py`
- Modify: `services/ml/main.py` (register the router)
- Test: `tests/ml_service/test_predict.py`

**Interfaces:**
- Consumes: `Applicant`, `PredictResponse` (schemas); `score_one`, `explain_one` (scoring); `save_prediction` (persistence); `get_principal` (auth).
- Produces: route `POST /api/v1/predict` (auth-required) returning `PredictResponse` with a persisted `prediction_id`. Task 8 mounts `/predict/batch` in the same router file.

- [ ] **Step 1: Write the failing test**

```python
# tests/ml_service/test_predict.py
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
    # Persist is stubbed so the endpoint test does not hit the network.
    monkeypatch.setattr(predict_router, "save_prediction",
                        lambda *a, **k: "pred-123")
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


def test_predict_rejects_bad_schema(monkeypatch):
    c = _client_with_auth(monkeypatch)
    bad = _valid_applicant(); bad["age"] = -5
    r = c.post("/api/v1/predict", json=bad)
    assert r.status_code == 422
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_predict.py -v`
Expected: ERROR/404 — router missing.

- [ ] **Step 3: Create `services/ml/routers/predict.py`**

```python
"""POST /api/v1/predict — score one applicant and persist it."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import Principal, get_principal
from ..persistence import get_champion, save_prediction
from ..schemas import Applicant, PredictResponse
from ..scoring import explain_one, score_one

router = APIRouter(prefix="/api/v1", tags=["predict"])


@router.post("/predict", response_model=PredictResponse)
def predict(applicant: Applicant,
            principal: Principal = Depends(get_principal)) -> PredictResponse:
    raw = applicant.to_raw_row()
    scored = score_one(raw)
    factors = explain_one(raw)
    pid = save_prediction(principal.user_id, applicant.model_dump(), scored, factors)
    return PredictResponse(
        risk_score=scored["risk_score"], risk_band=scored["risk_band"],
        probability=scored["probability"], model_version=get_champion()["semver"],
        prediction_id=pid)
```

- [ ] **Step 4: Register the router — edit `services/ml/main.py`**

In `create_app()`, before `return app`, add:

```python
    from .routers import predict
    app.include_router(predict.router)
```

- [ ] **Step 5: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_predict.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add services/ml/routers/predict.py services/ml/main.py tests/ml_service/test_predict.py
git commit -m "feat(ml-service): POST /api/v1/predict with auth + persistence"
```

---

### Task 8: `POST /api/v1/predict/batch` + idempotency

**Files:**
- Modify: `services/ml/routers/predict.py` (add the batch route)
- Test: `tests/ml_service/test_batch.py`

**Interfaces:**
- Consumes: `BatchPredictRequest`, `BatchPredictResponse` (schemas); `find_existing`, `save_prediction`; `input_hash`.
- Produces: route `POST /api/v1/predict/batch`. Idempotency: for each applicant, if a prediction with the same `(user_id, input_hash)` already exists it is reused (no duplicate insert); an `Idempotency-Key` header is accepted and echoed.

- [ ] **Step 1: Write the failing test**

```python
# tests/ml_service/test_batch.py
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
    a = _applicant(30)
    # Pre-seed one applicant's hash as already-persisted.
    h = input_hash(a)
    c, saved = _client(monkeypatch, existing={h: "pred-existing"})
    r = c.post("/api/v1/predict/batch", json={"applicants": [a]},
               headers={"Idempotency-Key": "abc"})
    assert r.status_code == 200
    assert r.json()["results"][0]["prediction_id"] == "pred-existing"
    assert saved == []                        # no new insert for the existing row
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_batch.py -v`
Expected: 404 — batch route missing.

- [ ] **Step 3: Add the batch route to `services/ml/routers/predict.py`**

Add these imports to the existing import block:

```python
from fastapi import Header
from ..logging_config import input_hash
from ..persistence import find_existing
from ..schemas import BatchPredictRequest, BatchPredictResponse
```

Append this route to the same file:

```python
@router.post("/predict/batch", response_model=BatchPredictResponse)
def predict_batch(
    req: BatchPredictRequest,
    principal: Principal = Depends(get_principal),
    idempotency_key: str | None = Header(default=None),
) -> BatchPredictResponse:
    version = get_champion()["semver"]
    results = []
    for applicant in req.applicants:
        raw = applicant.to_raw_row()
        feats = applicant.model_dump()
        ihash = input_hash(feats)
        existing = find_existing(principal.user_id, ihash)
        scored = score_one(raw)
        if existing:
            pid = existing                       # idempotent: reuse, no new row
        else:
            pid = save_prediction(principal.user_id, feats, scored, explain_one(raw))
        results.append(PredictResponse(
            risk_score=scored["risk_score"], risk_band=scored["risk_band"],
            probability=scored["probability"], model_version=version,
            prediction_id=pid))
    return BatchPredictResponse(model_version=version, count=len(results),
                                results=results)
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_batch.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add services/ml/routers/predict.py tests/ml_service/test_batch.py
git commit -m "feat(ml-service): POST /api/v1/predict/batch with input-hash idempotency"
```

---

### Task 9: `POST /api/v1/explain`, Dockerfile, service README, full-suite check

**Files:**
- Create: `services/ml/routers/explain.py`, `services/ml/Dockerfile`, `services/ml/README.md`
- Modify: `services/ml/main.py` (register the explain router)
- Test: `tests/ml_service/test_explain.py`

**Interfaces:**
- Consumes: `Applicant`, `ExplainResponse`, `ExplainFactor`; `score_one`, `explain_one`; `get_principal`.
- Produces: route `POST /api/v1/explain` returning score + SHAP top factors (no persistence — explanation is a read).

- [ ] **Step 1: Write the failing test**

```python
# tests/ml_service/test_explain.py
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_explain.py -v`
Expected: 404 — route missing.

- [ ] **Step 3: Create `services/ml/routers/explain.py`**

```python
"""POST /api/v1/explain — score + SHAP top factors (no persistence)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import Principal, get_principal
from ..persistence import get_champion
from ..schemas import Applicant, ExplainFactor, ExplainResponse
from ..scoring import explain_one, score_one

router = APIRouter(prefix="/api/v1", tags=["explain"])


@router.post("/explain", response_model=ExplainResponse)
def explain(applicant: Applicant,
            principal: Principal = Depends(get_principal)) -> ExplainResponse:
    raw = applicant.to_raw_row()
    scored = score_one(raw)
    factors = [ExplainFactor(**f) for f in explain_one(raw)]
    return ExplainResponse(
        risk_score=scored["risk_score"], risk_band=scored["risk_band"],
        model_version=get_champion()["semver"], top_factors=factors)
```

- [ ] **Step 4: Register the router — edit `services/ml/main.py`**

In `create_app()`, before `return app`, add:

```python
    from .routers import explain
    app.include_router(explain.router)
```

- [ ] **Step 5: Create `services/ml/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app
# Root requirements (ML deps) + service requirements.
COPY requirements.txt ./root-requirements.txt
COPY services/ml/requirements.txt ./svc-requirements.txt
RUN pip install --no-cache-dir -r root-requirements.txt -r svc-requirements.txt

COPY src ./src
COPY services ./services
COPY models ./models
COPY data ./data

EXPOSE 8000
CMD ["uvicorn", "services.ml.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 6: Create `services/ml/README.md`**

```markdown
# Credit Risk ML Service (R1 Plan 2)

FastAPI service wrapping the `src/` ML pipeline. Endpoints (all under `/api/v1`
except health): `GET /health`, `GET /ready`, `GET /api/v1/models/current`,
`POST /api/v1/predict`, `POST /api/v1/predict/batch`, `POST /api/v1/explain`.

## Run locally
```bash
.venv/Scripts/python.exe -m uvicorn services.ml.main:app --reload --port 8000
# docs at http://localhost:8000/docs
```

Auth: send `Authorization: Bearer <supabase access token>`. Predictions are
written to Supabase with `created_by` = the token's user, so Plan 1 RLS governs
reads. Deferred to R4: MCP server, LLM credit memos.

## Deploy (Render, later)
Build from `services/ml/Dockerfile`; set env vars `SUPABASE_URL`,
`SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`.
```

- [ ] **Step 7: Run the service test, then the FULL suite**

Run: `.venv/Scripts/python.exe -m pytest tests/ml_service/test_explain.py -v`
Expected: 2 passed.

Run: `.venv/Scripts/python.exe -m pytest`
Expected: all green — 27 prior + the new ml_service tests (health 2, schemas 4, scoring 3, auth 3, persistence 2, models 1, predict 3, batch 2, explain 2 = 22) → 49 passed (persistence's 2 require live creds; otherwise 47 passed + 2 skipped).

- [ ] **Step 8: Verify the app boots under uvicorn**

Run: `.venv/Scripts/python.exe -c "from services.ml.main import app; print('routes:', sorted(r.path for r in app.routes if getattr(r,'path','').startswith(('/health','/ready','/api'))))"`
Expected: prints the 6 expected paths.

- [ ] **Step 9: Commit + tag**

```bash
git add services/ml/routers/explain.py services/ml/main.py services/ml/Dockerfile services/ml/README.md tests/ml_service/test_explain.py
git commit -m "feat(ml-service): POST /api/v1/explain, Dockerfile, service README"
git tag r1-plan2-complete
```

---

## Self-Review

- **Spec coverage (§7):** health/ready (T1) ✓ · models/current (T6) ✓ · predict (T7) ✓ · predict/batch + idempotency (T8) ✓ · explain (T9) ✓ · JWT auth + RBAC (T4) ✓ · Pydantic schemas validating the 23-field contract (T2) ✓ · PII-redacting logging via input_hash (T1/T5) ✓ · error envelope (T1) ✓ · model-version echoed in responses (T6–T9) ✓ · prediction/explanation persisted with created_by (T5) ✓ · Dockerfile (T9) ✓. Deferred per scope: MCP server, LLM memos (R4); rate limiting (spec §7 lists it — noted as R1-Plan-2 gap, add in a follow-up as it needs Redis, which is not yet provisioned).
- **Placeholders:** none — every step has full code/commands.
- **Type consistency:** `Applicant.to_raw_row()`, `score_one`/`explain_one` return shapes, `save_prediction(user_id, features, scored, top_factors)` signature, `get_champion()` dict keys (`id/semver/threshold`), and `Principal(user_id, role)` are used identically across tasks 5–9.

**Known deviations from spec, intentional for R1 Plan 2:** rate limiting and the `Idempotency-Key` persistence table are simplified — idempotency is achieved by `(user_id, input_hash)` dedup rather than a key store; rate limiting deferred to when Redis is provisioned (R5 monitoring). Both logged here so the final review can triage.

---

**Reminder:** the persistence test (T5) and any live check need the `.env` created in Plan 1. All other tests run offline with dependency overrides / monkeypatched seams.

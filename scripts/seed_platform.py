"""Seed the Supabase project: demo users, demo portfolio, model registry, flags.

Idempotent: safe to re-run (skips users/portfolio that already exist).
Requires .env with SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DEMO_PASSWORD.

Security note: the demo portfolio is owned by a dedicated non-login service
account (`svc-demo-owner@demo.local`), not by `demo-analyst`. `pf_delete_own`
has no is_demo guard, so a visitor logging into the demo-analyst account
could otherwise delete the public demo portfolio.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config  # noqa: E402

load_dotenv()
URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]  # server-side only
DEMO_PASSWORD = os.environ["DEMO_PASSWORD"]

DEMO_USERS = [
    ("demo-analyst@demo.local", "Demo Analyst", "analyst"),
    ("demo-manager@demo.local", "Demo Manager", "manager"),
    ("demo-compliance@demo.local", "Demo Compliance", "compliance"),
    ("demo-executive@demo.local", "Demo Executive", "executive"),
]
# Dedicated non-login owner for the public demo portfolio. Not a DEMO_USERS
# entry: it must never be surfaced as a demo login.
SVC_DEMO_OWNER_EMAIL = "svc-demo-owner@demo.local"
SVC_DEMO_OWNER_NAME = "Service Demo Owner"
DEMO_PORTFOLIO = "UCI Taiwan 30k (demo)"
CHUNK = 1000

sb = create_client(URL, KEY)


def _list_existing_users() -> dict[str, str]:
    """Return {email: id} for all existing auth users.

    supabase-py's admin.list_users() may return a plain list of User objects
    rather than an object with a `.users` attribute, depending on version.
    Handle both shapes.
    """
    res = sb.auth.admin.list_users()
    users = getattr(res, "users", res)
    return {u.email: u.id for u in users}


def _create_user(email: str, name: str) -> str:
    """Create an auth user, returning its id. Tolerates "already exists"."""
    try:
        res = sb.auth.admin.create_user({
            "email": email, "password": DEMO_PASSWORD,
            "email_confirm": True,
            "user_metadata": {"display_name": name},
        })
        return res.user.id
    except Exception:
        # Idempotency guard: another run (or a race) already created it.
        existing = _list_existing_users()
        if email in existing:
            return existing[email]
        raise


def ensure_demo_users() -> dict[str, str]:
    existing = _list_existing_users()
    ids = {}
    for email, name, role in DEMO_USERS:
        if email in existing:
            ids[email] = existing[email]
        else:
            ids[email] = _create_user(email, name)
        sb.table("profiles").update(
            {"role": role, "is_demo": True, "display_name": name}
        ).eq("user_id", ids[email]).execute()
        print(f"demo user ready: {email} ({role})")
    return ids


def ensure_svc_demo_owner() -> str:
    """Create (or find) the non-login service account that owns the demo
    portfolio. Never added to DEMO_USERS."""
    existing = _list_existing_users()
    if SVC_DEMO_OWNER_EMAIL in existing:
        owner_id = existing[SVC_DEMO_OWNER_EMAIL]
    else:
        owner_id = _create_user(SVC_DEMO_OWNER_EMAIL, SVC_DEMO_OWNER_NAME)
    sb.table("profiles").update(
        {"display_name": SVC_DEMO_OWNER_NAME}
    ).eq("user_id", owner_id).execute()
    print(f"service demo owner ready: {SVC_DEMO_OWNER_EMAIL}")
    return owner_id


def ensure_demo_portfolio(owner_id: str) -> None:
    found = (sb.table("portfolios").select("id")
             .eq("name", DEMO_PORTFOLIO).execute().data)
    if found:
        print("demo portfolio already seeded")
        return
    df = pd.read_csv(config.RAW_CSV)
    pf = (sb.table("portfolios").insert({
        "owner_id": owner_id, "name": DEMO_PORTFOLIO,
        "is_demo": True, "row_count": len(df),
    }).execute().data[0])
    rows = [{"portfolio_id": pf["id"], "row_index": i,
             "features": r._asdict() if hasattr(r, "_asdict") else r}
            for i, r in enumerate(df.to_dict(orient="records"))]
    for i in range(0, len(rows), CHUNK):
        sb.table("portfolio_rows").insert(rows[i:i + CHUNK]).execute()
        print(f"  rows {i + len(rows[i:i + CHUNK]):,}/{len(rows):,}")
    print(f"demo portfolio seeded: {len(rows):,} real rows")


def ensure_model_version() -> None:
    if sb.table("model_versions").select("id").eq(
            "semver", "1.0.0-real-uci").execute().data:
        print("model version already registered")
        return
    metrics = json.loads(Path(config.METRICS_PATH).read_text())
    sb.table("model_versions").insert({
        "semver": "1.0.0-real-uci",
        "algo": metrics["model_type"],
        "stage": "champion",
        "metrics": metrics["advanced"],
        "trained_on": "UCI Default of Credit Card Clients (real, 30k)",
        "threshold": 0.5,
    }).execute()
    print("model version 1.0.0-real-uci registered as champion")


def ensure_flags() -> None:
    for key in ("llm_features", "uploads", "signup"):
        sb.table("feature_flags").upsert(
            {"key": key, "enabled": True}).execute()
    print("feature flags ensured")


if __name__ == "__main__":
    ids = ensure_demo_users()
    svc_owner_id = ensure_svc_demo_owner()
    ensure_demo_portfolio(svc_owner_id)
    ensure_model_version()
    ensure_flags()
    print("SEED COMPLETE")

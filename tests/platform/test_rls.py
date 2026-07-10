"""RLS penetration tests — run against the live Supabase project.

Skipped automatically when .env credentials are absent (e.g. CI without
secrets). These tests are the security acceptance gate of spec section 12.
"""
from __future__ import annotations

import os
import uuid

import pytest
from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("SUPABASE_URL")
ANON = os.getenv("SUPABASE_ANON_KEY")
SERVICE = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

pytestmark = pytest.mark.skipif(
    not (URL and ANON and SERVICE),
    reason="Supabase credentials not configured",
)


@pytest.fixture(scope="module")
def clients():
    from supabase import create_client

    admin = create_client(URL, SERVICE)
    users, sessions = [], []
    for _ in range(2):
        email = f"rls-test-{uuid.uuid4().hex[:10]}@demo.local"
        pw = f"Pw!{uuid.uuid4().hex[:12]}"
        u = admin.auth.admin.create_user(
            {"email": email, "password": pw, "email_confirm": True})
        users.append(u.user.id)
        c = create_client(URL, ANON)
        c.auth.sign_in_with_password({"email": email, "password": pw})
        sessions.append(c)
    yield admin, sessions[0], sessions[1]
    for uid in users:
        admin.auth.admin.delete_user(uid)


def test_user_cannot_read_another_users_portfolio(clients):
    _, user_a, user_b = clients
    pf = user_a.table("portfolios").insert(
        {"owner_id": user_a.auth.get_user().user.id,
         "name": "private-A"}).execute().data[0]
    user_a.table("portfolio_rows").insert(
        {"portfolio_id": pf["id"], "row_index": 0,
         "features": {"limit_bal": 50000}}).execute()

    stolen = user_b.table("portfolio_rows").select("*").eq(
        "portfolio_id", pf["id"]).execute().data
    assert stolen == []  # RLS: B sees nothing of A's data

    stolen_pf = user_b.table("portfolios").select("*").eq(
        "id", pf["id"]).execute().data
    assert stolen_pf == []


def test_user_cannot_insert_into_another_users_portfolio(clients):
    _, user_a, user_b = clients
    pf = user_a.table("portfolios").insert(
        {"owner_id": user_a.auth.get_user().user.id,
         "name": "private-A2"}).execute().data[0]
    with pytest.raises(Exception):
        user_b.table("portfolio_rows").insert(
            {"portfolio_id": pf["id"], "row_index": 0,
             "features": {}}).execute()


def test_demo_portfolio_is_world_readable(clients):
    _, user_a, _ = clients
    demo = user_a.table("portfolios").select("id").eq(
        "is_demo", True).execute().data
    assert len(demo) >= 1


def test_client_cannot_update_predictions(clients):
    # predictions are append-only for client roles (UPDATE revoked)
    _, user_a, _ = clients
    with pytest.raises(Exception):
        user_a.table("predictions").update(
            {"risk_score": 0}).eq("input_hash", "nonexistent").execute()


def test_user_cannot_escalate_own_role(clients):
    _, user_a, _ = clients
    uid = user_a.auth.get_user().user.id
    with pytest.raises(Exception):
        user_a.table("profiles").update(
            {"role": "admin"}).eq("user_id", uid).execute()


# --- Additions covering security fixes from migrations 0003_1 and 0003_2 ---

def test_user_cannot_forge_prediction_in_another_users_portfolio(clients):
    # 0003_1 FIX 2: pred_insert_own now requires the target portfolio (if
    # any) to belong to the caller. A client could previously forge a
    # prediction row pointed at someone else's portfolio.
    admin, user_a, user_b = clients
    pf = user_a.table("portfolios").insert(
        {"owner_id": user_a.auth.get_user().user.id,
         "name": "private-A3"}).execute().data[0]

    mv = user_b.table("model_versions").select("id").limit(1).execute().data
    assert mv, "expected at least one seeded model_versions row"
    model_version_id = mv[0]["id"]
    b_id = user_b.auth.get_user().user.id

    def _base_row(portfolio_id, input_hash):
        return {
            "portfolio_id": portfolio_id,
            "created_by": b_id,
            "probability": 0.5,
            "risk_score": 50,
            "risk_band": "Medium",
            "threshold_used": 0.5,
            "model_version_id": model_version_id,
            "input_hash": input_hash,
        }

    forged = None
    try:
        forged = user_b.table("predictions").insert(
            _base_row(pf["id"], f"forged-{uuid.uuid4().hex}")).execute().data
    except Exception:
        forged = None
    assert not forged  # rejected: either raised, or PostgREST filtered it to []

    # Tightening must not over-block: an ad-hoc (portfolio-less) prediction
    # owned by the caller should still succeed.
    # predictions.created_by has no ON DELETE CASCADE (unlike portfolios), so
    # this row must always be cleaned up via the service role — even if the
    # assertion below fails — or the fixture's teardown (deleting the auth
    # user) would fail with an FK restrict violation and leak the user.
    adhoc_id = None
    try:
        adhoc = user_b.table("predictions").insert(
            _base_row(None, f"adhoc-{uuid.uuid4().hex}")).execute().data
        if adhoc:
            adhoc_id = adhoc[0]["id"]
        assert len(adhoc) == 1
    finally:
        if adhoc_id is not None:
            admin.table("predictions").delete().eq("id", adhoc_id).execute()


def test_client_cannot_write_api_keys(clients):
    # 0003_1 FIX 1: keys_insert_own / keys_update_own were dropped — clients
    # could previously self-escalate `scopes` via a direct insert/update.
    admin, user_a, _ = clients
    uid = user_a.auth.get_user().user.id
    inserted = None
    try:
        inserted = user_a.table("api_keys").insert(
            {"user_id": uid, "key_hash": "x", "scopes": ["admin:*"]}
        ).execute().data
    except Exception:
        inserted = None
    assert not inserted

    # Also confirm UPDATE is denied. Insert a row via the service-role admin
    # client (clients cannot insert, per above), then attempt a client-side
    # update and confirm — via a service-role read — that it did not take
    # effect. PostgREST under RLS can either raise on the UPDATE or silently
    # affect zero rows, so both outcomes are accepted here.
    key_id = None
    try:
        seeded = admin.table("api_keys").insert(
            {"user_id": uid, "key_hash": "seed-hash", "scopes": ["read:only"]}
        ).execute().data
        key_id = seeded[0]["id"]

        update_raised = False
        try:
            user_a.table("api_keys").update(
                {"scopes": ["admin:*"]}).eq("id", key_id).execute()
        except Exception:
            update_raised = True

        after = admin.table("api_keys").select("scopes").eq(
            "id", key_id).execute().data
        assert update_raised or after[0]["scopes"] == ["read:only"]
    finally:
        if key_id is not None:
            admin.table("api_keys").delete().eq("id", key_id).execute()


def test_client_cannot_delete_demo_portfolio(clients):
    # 0003_2: pf_delete_own now requires is_demo = false. Double protection
    # here since user_a isn't even the owner of the demo portfolio.
    admin, user_a, _ = clients
    demo = user_a.table("portfolios").select("id").eq(
        "is_demo", True).limit(1).execute().data
    assert demo, "expected at least one seeded demo portfolio"
    demo_id = demo[0]["id"]

    try:
        user_a.table("portfolios").delete().eq("id", demo_id).execute()
    except Exception:
        pass

    still_there = admin.table("portfolios").select("id").eq(
        "id", demo_id).execute().data
    assert len(still_there) == 1

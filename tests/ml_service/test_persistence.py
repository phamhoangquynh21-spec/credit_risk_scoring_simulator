import os
import uuid

import pytest
from dotenv import load_dotenv

load_dotenv()
pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="Supabase credentials not configured",
)


def test_get_champion_returns_the_registered_champion():
    """Assert the contract, not a hardcoded semver: a governance-approved
    promotion legitimately changes which version is champion, and a test must
    not break because production did the thing it is designed to do."""
    from services.ml.persistence import get_champion, service_client
    champ = get_champion()
    assert {"id", "semver", "threshold"} <= set(champ)
    assert isinstance(champ["threshold"], (int, float))
    live = (service_client().table("model_versions").select("semver")
            .eq("stage", "champion").execute().data)
    assert champ["semver"] in {r["semver"] for r in live}


def test_save_prediction_roundtrip():
    from services.ml.persistence import service_client, save_prediction
    svc = service_client()
    # create a throwaway user to own the prediction (FK to auth.users)
    email = f"persist-test-{uuid.uuid4().hex[:10]}@demo.local"
    u = svc.auth.admin.create_user(
        {"email": email, "password": f"Pw!{uuid.uuid4().hex}",
         "email_confirm": True})
    uid = u.user.id
    pid = None
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
        # predictions.created_by is ON DELETE SET NULL (not cascade), so the
        # prediction row must be deleted explicitly or it orphans in the live DB.
        if pid:
            svc.table("predictions").delete().eq("id", pid).execute()  # prediction_explanations cascades
        svc.auth.admin.delete_user(uid)

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


# Cached for the process lifetime: promoting a new champion in the DB requires
# a service restart to take effect in R1 (no runtime cache-bust path yet).
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

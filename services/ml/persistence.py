"""Supabase persistence: write predictions/explanations via the service role,
with created_by set to the caller so Plan 1's RLS governs later reads."""
from __future__ import annotations

import functools
import time

from .errors import AppError
from .logging_config import input_hash
from .settings import settings


@functools.lru_cache(maxsize=1)
def service_client():
    from supabase import create_client
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


# The champion changes at runtime whenever governance approves a promotion, so
# it must NOT be cached for the process lifetime — an approved promotion that
# only takes effect on restart is a governance hole (the service keeps scoring
# with a retired model and its old threshold). Cache briefly instead: the TTL
# bounds how long a retired champion can still be served, and `promote` busts
# this instance explicitly. Promotions made outside the API (scripts, another
# instance) converge within the TTL without any coordination.
CHAMPION_CACHE_TTL_SECONDS = 30

_champion: dict | None = None
_champion_read_at: float = 0.0


def get_champion() -> dict:
    global _champion, _champion_read_at
    now = time.monotonic()
    if _champion is not None and (now - _champion_read_at) < CHAMPION_CACHE_TTL_SECONDS:
        return _champion
    rows = (service_client().table("model_versions")
            .select("id, semver, threshold").eq("stage", "champion")
            .limit(1).execute().data)
    if not rows:
        raise AppError("no_model", "no champion model registered", 503)
    _champion = rows[0]
    _champion_read_at = now
    return _champion


def invalidate_champion_cache() -> None:
    """Drop the cached champion so the next read re-queries immediately.

    Called after a promotion so the approving instance switches at once; other
    instances pick the new champion up within CHAMPION_CACHE_TTL_SECONDS.
    """
    global _champion, _champion_read_at
    _champion = None
    _champion_read_at = 0.0


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

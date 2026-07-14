"""GET /api/v1/models/current — the champion model card."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel

import src.db as db
from src import config

from ..auth import Principal, get_principal, require_role
from ..errors import AppError
from ..persistence import get_champion
from ..scoring import load_bundle

router = APIRouter(prefix="/api/v1/models", tags=["models"])


class PromoteRequest(BaseModel):
    to_stage: str


@router.get("/current")
def current_model(principal: Principal = Depends(get_principal)) -> dict:
    champ = get_champion()
    bundle = load_bundle()
    metrics = json.loads(config.METRICS_PATH.read_text())["advanced"]
    return {"semver": champ["semver"], "algo": bundle["model_type"],
            "metrics": metrics}


@router.post("/{semver}/promote")
def promote(semver: str, body: PromoteRequest,
            principal: Principal = Depends(require_role("governance"))) -> dict:
    """Promote a model version to a new lifecycle stage. Governance-gated at the
    route; the src.db gate independently refuses champion promotion without an
    approver. approved_by is stamped with the calling governance principal."""
    try:
        row = db.promote_model(semver, body.to_stage,
                               approved_by=principal.user_id)
    except ValueError as exc:
        # e.g. invalid stage, unknown semver, or champion without approval.
        raise AppError("promotion_rejected", str(exc), 400) from exc
    return {"semver": semver, "stage": row["stage"], "approved_by": principal.user_id}

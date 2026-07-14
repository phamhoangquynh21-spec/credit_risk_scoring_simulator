"""POST /api/v1/explain — score + SHAP top factors (no persistence)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from src.ml.reason_codes import build_explanation_payload

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
    raw_factors = explain_one(raw)
    factors = [ExplainFactor(**f) for f in raw_factors]
    # Governed reason codes + mandatory non-causal disclaimer (Stage 3.5).
    payload = build_explanation_payload(
        [(f["feature"], f["contribution"]) for f in raw_factors])
    return ExplainResponse(
        risk_score=scored["risk_score"], risk_band=scored["risk_band"],
        model_version=get_champion()["semver"], top_factors=factors,
        reason_codes=payload["reason_codes"], disclaimer=payload["disclaimer"])

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

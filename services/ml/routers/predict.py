"""POST /api/v1/predict — score one applicant and persist it."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Response

from ..auth import Principal, get_principal
from ..logging_config import input_hash
from ..persistence import find_existing, get_champion, save_prediction
from ..schemas import Applicant, BatchPredictRequest, BatchPredictResponse, PredictResponse
from ..scoring import explain_one, score_one

router = APIRouter(prefix="/api/v1", tags=["predict"])


def _recommendation(probability: float, threshold: float) -> str:
    """Decision-support recommendation, NOT an automated decision: 'decline'
    when the predicted default probability meets/exceeds the champion's
    threshold, else 'approve'. The human analyst makes the final call."""
    return "decline" if probability >= threshold else "approve"


@router.post("/predict", response_model=PredictResponse)
def predict(applicant: Applicant,
            principal: Principal = Depends(get_principal)) -> PredictResponse:
    raw = applicant.to_raw_row()
    scored = score_one(raw)
    factors = explain_one(raw)
    pid = save_prediction(principal.user_id, applicant.model_dump(), scored, factors)
    champ = get_champion()
    threshold = champ["threshold"]
    return PredictResponse(
        risk_score=scored["risk_score"], risk_band=scored["risk_band"],
        probability=scored["probability"], model_version=champ["semver"],
        prediction_id=pid, threshold_used=threshold,
        recommendation=_recommendation(scored["probability"], threshold))


@router.post("/predict/batch", response_model=BatchPredictResponse)
def predict_batch(
    req: BatchPredictRequest,
    response: Response,
    principal: Principal = Depends(get_principal),
    idempotency_key: str | None = Header(default=None),
) -> BatchPredictResponse:
    champ = get_champion()
    version = champ["semver"]
    threshold = champ["threshold"]
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
            prediction_id=pid, threshold_used=threshold,
            recommendation=_recommendation(scored["probability"], threshold)))
    if idempotency_key is not None:
        response.headers["Idempotency-Key"] = idempotency_key
    return BatchPredictResponse(model_version=version, count=len(results),
                                results=results)

"""POST /api/v1/llm-reports/credit-memo — grounded credit memo for an applicant.

Scores the applicant, builds whitelisted structured memo inputs, and calls the
Stage 5.4 grounded-memo generator. A live LLM memo needs the `anthropic` package
plus ANTHROPIC_API_KEY; without them the generator falls back to a deterministic,
by-construction-grounded template, so this endpoint works out of the box.
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends

from src.llm import build_memo_inputs, generate_memo, persist_memo
from src.llm.memo import GroundingError
from src.llm.provider import AnthropicProvider

from ..auth import Principal, get_principal
from ..persistence import get_champion, save_prediction
from ..schemas import Applicant
from ..scoring import explain_one, score_one

router = APIRouter(prefix="/api/v1/llm-reports", tags=["llm"])

log = logging.getLogger("ml_service")


@router.post("/credit-memo")
def credit_memo(applicant: Applicant,
                principal: Principal = Depends(get_principal)) -> dict:
    raw = applicant.to_raw_row()
    scored = score_one(raw)
    raw_factors = explain_one(raw)
    champ = get_champion()
    inputs = build_memo_inputs(
        probability=scored["probability"],
        risk_score=scored["risk_score"],
        risk_band=scored["risk_band"],
        threshold_used=champ["threshold"],
        model_version=champ["semver"],
        top_factors=[(f["feature"], f["contribution"]) for f in raw_factors],
        application_fields=applicant.model_dump(),
    )
    # Live memos need the anthropic SDK + key; otherwise generate_memo falls
    # back to the deterministic template (fallback_used=True). A live provider
    # can return ungrounded text -> GroundingError; fall back to the template
    # rather than surfacing a 500.
    provider = AnthropicProvider() if os.getenv("ANTHROPIC_API_KEY") else None
    try:
        memo = generate_memo(inputs, provider)
    except GroundingError:
        log.warning("provider memo failed grounding; using template fallback")
        memo = generate_memo(inputs, None)

    # Persist the human-review/provenance record: save a prediction row so the
    # memo has a prediction_id to attach to, then persist the memo to
    # llm_reports (review_status='draft'). Persistence must never break memo
    # generation, so a failure (offline / DB down) only logs and still returns
    # the generated memo.
    prediction_id = None
    review_status = "draft"
    try:
        prediction_id = save_prediction(
            principal.user_id, applicant.model_dump(), scored, raw_factors)
        row = persist_memo(memo, prediction_id)
        review_status = row.get("review_status", "draft")
    except Exception as exc:  # persistence unavailable: memo still returned
        log.warning("credit-memo persistence failed: %s", exc)

    return {
        "prediction_id": prediction_id,
        "memo_text": memo["memo_text"],
        "provider": memo["provider"],
        "model": memo["model"],
        "grounded": memo["grounded"],
        "fallback_used": memo["fallback_used"],
        "review_status": review_status,
    }

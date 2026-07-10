"""GET /api/v1/models/current — the champion model card."""
from __future__ import annotations

import json

from fastapi import APIRouter

from src import config
from ..persistence import get_champion
from ..scoring import load_bundle

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.get("/current")
def current_model() -> dict:
    champ = get_champion()
    bundle = load_bundle()
    metrics = json.loads(config.METRICS_PATH.read_text())["advanced"]
    return {"semver": champ["semver"], "algo": bundle["model_type"],
            "metrics": metrics}

"""Tool logic for the credit-risk MCP server.

These are plain functions (with Pydantic input models) so they are unit-testable
without the `mcp` SDK installed. `server.py` wraps them with FastMCP. Everything
here is READ-ONLY and calls only the tested `src/` ML core — no writes, no
network beyond Supabase reads, no re-implemented model logic.

Scoring/explain/memo work offline from the committed `models/model.pkl`.
Registry/monitoring tools need Supabase credentials (`.env`); when they are
absent the tool returns a clear, actionable message instead of raising.
"""
from __future__ import annotations

import functools
import json

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from src import config
from src.explain import explain_in_plain_language, score_batch
from src.ml.reason_codes import build_explanation_payload

# Raw UCI field names in the order the model expects them (snake_case here;
# mapped to the model's UPPERCASE raw columns by ApplicantInput.to_raw()).
_PAY = ["pay_0", "pay_2", "pay_3", "pay_4", "pay_5", "pay_6"]
_BILL = [f"bill_amt{i}" for i in range(1, 7)]
_PAYAMT = [f"pay_amt{i}" for i in range(1, 7)]


class ApplicantInput(BaseModel):
    """A credit-card applicant in the raw UCI schema (23 fields)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    limit_bal: float = Field(..., description="Credit limit in NT dollars", ge=0)
    sex: int = Field(..., description="1=male, 2=female", ge=1, le=2)
    education: int = Field(..., description="1=grad school,2=university,3=high school,4=other", ge=0, le=6)
    marriage: int = Field(..., description="1=married,2=single,3=other", ge=0, le=3)
    age: int = Field(..., description="Age in years", ge=18, le=120)
    pay_0: int = Field(..., description="Repayment status last month (-2..9; -1=paid duly, 1-8=months late)", ge=-2, le=9)
    pay_2: int = Field(..., ge=-2, le=9, description="Repayment status 2 months ago")
    pay_3: int = Field(..., ge=-2, le=9, description="Repayment status 3 months ago")
    pay_4: int = Field(..., ge=-2, le=9, description="Repayment status 4 months ago")
    pay_5: int = Field(..., ge=-2, le=9, description="Repayment status 5 months ago")
    pay_6: int = Field(..., ge=-2, le=9, description="Repayment status 6 months ago")
    bill_amt1: float = Field(..., description="Bill statement amount, most recent month")
    bill_amt2: float = 0.0
    bill_amt3: float = 0.0
    bill_amt4: float = 0.0
    bill_amt5: float = 0.0
    bill_amt6: float = 0.0
    pay_amt1: float = Field(0.0, description="Amount paid, most recent month", ge=0)
    pay_amt2: float = Field(0.0, ge=0)
    pay_amt3: float = Field(0.0, ge=0)
    pay_amt4: float = Field(0.0, ge=0)
    pay_amt5: float = Field(0.0, ge=0)
    pay_amt6: float = Field(0.0, ge=0)

    def to_raw(self) -> dict:
        """Return a dict keyed by the UPPERCASE UCI column names the model uses."""
        return {name.upper(): getattr(self, name) for name in self.__class__.model_fields}


@functools.lru_cache(maxsize=1)
def _bundle() -> dict:
    import joblib
    return joblib.load(config.MODEL_PATH)


def _try_champion() -> dict | None:
    """Return the champion model_version row, or None if Supabase is unreachable."""
    try:
        from src.db import get_champion
        return get_champion()
    except Exception:
        return None


def _no_db_message(what: str) -> dict:
    return {
        "error": "supabase_unavailable",
        "message": (f"{what} requires Supabase credentials. Set SUPABASE_URL and "
                    "SUPABASE_SERVICE_ROLE_KEY in the environment (.env) to enable "
                    "registry/monitoring tools. Scoring/explain/memo tools work "
                    "offline from the local model."),
    }


# --- Tool implementations (each returns a JSON string) ----------------------

def score_applicant(params: ApplicantInput) -> str:
    """Score one applicant: probability of next-month default, 0-100 risk score,
    Low/Medium/High band, and — when the registry is reachable — the cost-tuned
    threshold and an approve/decline recommendation (decision-support only)."""
    raw = params.to_raw()
    b = _bundle()
    scored = score_batch(b["model"], b["features"], pd.DataFrame([raw]))
    row = scored.iloc[0]
    prob = float(row["risk_score"]) / 100.0
    result = {
        "probability": prob,
        "risk_score": float(row["risk_score"]),
        "risk_band": str(row["risk_band"]),
        "model_type": b["model_type"],
        "disclaimer": "Decision-support only; a human makes the credit decision.",
    }
    champ = _try_champion()
    if champ and champ.get("threshold") is not None:
        t = float(champ["threshold"])
        result["model_version"] = champ.get("semver")
        result["threshold_used"] = t
        result["recommendation"] = "decline" if prob >= t else "approve"
    return json.dumps(result, indent=2)


def explain_applicant(params: ApplicantInput) -> str:
    """Explain an applicant's score: SHAP top factors mapped to analyst-ready
    reason codes, with the mandatory 'contribution, not causation' disclaimer."""
    from src.preprocessing import clean_data, engineer_features

    raw = params.to_raw()
    b = _bundle()
    feat_df = engineer_features(clean_data(pd.DataFrame([raw])))
    single = feat_df[b["features"]].iloc[0]
    items = explain_in_plain_language(b["model"], single)
    top_factors = [
        {"feature": i["feature"], "friendly": i["friendly"],
         "contribution": float(i["contribution"]), "direction": i["direction"]}
        for i in items
    ]
    # build_explanation_payload / to_reason_codes consume (feature, contribution) pairs.
    factor_pairs = [(i["feature"], float(i["contribution"])) for i in items]
    payload = build_explanation_payload(factor_pairs)
    payload["top_factors"] = top_factors
    return json.dumps(payload, indent=2)


def generate_memo(params: ApplicantInput) -> str:
    """Generate a grounded credit memo for an applicant. Uses the configured LLM
    provider when available, otherwise a deterministic template. The memo is
    grounded in the structured score + factors and always carries the
    decision-support disclaimer; it is not a credit decision."""
    from src.llm.memo import build_memo_inputs, generate_memo as _gen

    scored = json.loads(score_applicant(params))
    explained = json.loads(explain_applicant(params))
    # The memo pipeline consumes (feature, contribution) pairs, not the display dicts.
    factor_pairs = [(f["feature"], f["contribution"]) for f in explained["top_factors"]]
    inputs = build_memo_inputs(
        probability=scored["probability"],
        risk_score=scored["risk_score"],
        risk_band=scored["risk_band"],
        threshold_used=scored.get("threshold_used"),
        model_version=scored.get("model_version"),
        top_factors=factor_pairs,
        application_fields=params.model_dump(),
    )
    memo = _gen(inputs, provider=None)  # template fallback; never calls the network
    return json.dumps(memo, indent=2)


def get_champion() -> str:
    """Return the current champion model version (semver, algo, stage, threshold,
    metrics, approver). Requires Supabase credentials."""
    champ = _try_champion()
    if champ is None:
        return json.dumps(_no_db_message("Reading the champion model"), indent=2)
    return json.dumps(champ, indent=2, default=str)


def get_model_card(semver: str) -> str:
    """Return the Markdown model card for a model version (identity, metrics,
    decision-support disclaimer, per-group fairness vs the 0.8 rule).
    Requires Supabase credentials."""
    try:
        from src.ml.model_card import generate_model_card
        return generate_model_card(semver)
    except ValueError as exc:
        return json.dumps({"error": "not_found", "message": str(exc)}, indent=2)
    except Exception:
        return json.dumps(_no_db_message("Generating a model card"), indent=2)


def recent_drift(metric: str, limit: int = 20) -> str:
    """Return recent monitoring points for a drift/quality metric
    (e.g. 'drift_psi.limit_bal'). Requires Supabase credentials."""
    try:
        from src.db import get_metrics
        rows = get_metrics(metric)[-limit:]
        return json.dumps({"metric": metric, "points": rows}, indent=2, default=str)
    except Exception:
        return json.dumps(_no_db_message("Reading drift metrics"), indent=2)


def list_data_sources() -> str:
    """Return the data-source / connector registry (what's live-and-free vs
    gated behind a license/contract). Reads the committed docs/data_sources.md."""
    doc = config.PROJECT_ROOT / "docs" / "data_sources.md"
    if not doc.exists():
        return json.dumps({"error": "not_found", "message": "docs/data_sources.md is missing"}, indent=2)
    return doc.read_text(encoding="utf-8")

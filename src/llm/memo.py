"""Grounded LLM credit memos (Stage 5.4).

Hallucination guardrails, in order: the prompt is built ONLY from a fixed set
of structured inputs (ALLOWED_INPUT_KEYS); application fields are PII-redacted
before anything leaves the process; provider output is post-validated so every
number and feature-name token in the memo traces back to the inputs
(GroundingError otherwise); and a deterministic template fallback (same
plain-language wording as src.explain) keeps memos flowing when no provider is
configured or the provider errors. Every memo ends with the non-causal
CONTRIBUTION_DISCLAIMER plus a human-review line, and persists to llm_reports
where a review-status gate controls external use.
"""
from __future__ import annotations

import json
import re

from src import db
from src.ml.reason_codes import (CONTRIBUTION_DISCLAIMER,
                                 build_explanation_payload)

ALLOWED_INPUT_KEYS = {
    "probability", "risk_score", "risk_band", "threshold_used",
    "model_version", "top_factors", "application_fields", "policy_text",
}

PII_KEYS = {"name", "email", "phone", "address", "dob", "national_id"}

HUMAN_REVIEW_LINE = "Decision-support only; human review required."

_SYSTEM_PROMPT = (
    "You are drafting an internal credit-risk memo for a loan analyst. "
    "Use ONLY the structured inputs in the user message; do not introduce any "
    "number, feature name or applicant fact that is not present in them. "
    "Write short, plain business English."
)

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_FEATURE_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+")


class GroundingError(ValueError):
    """Provider memo referenced numbers/features absent from the inputs."""


def build_memo_inputs(**kwargs) -> dict:
    """Whitelist-validate memo inputs and PII-redact application_fields.

    Only ALLOWED_INPUT_KEYS are accepted; anything else raises ValueError so a
    stray applicant field can never leak into a prompt.
    """
    unknown = sorted(set(kwargs) - ALLOWED_INPUT_KEYS)
    if unknown:
        raise ValueError(
            "unknown memo input key(s): " + ", ".join(unknown)
            + "; allowed: " + ", ".join(sorted(ALLOWED_INPUT_KEYS)))
    inputs = dict(kwargs)
    if isinstance(inputs.get("application_fields"), dict):
        inputs["application_fields"] = redact(inputs["application_fields"])
    return inputs


def redact(fields: dict) -> dict:
    """Strip PII keys (case-insensitive) from an application-fields dict."""
    return {k: v for k, v in fields.items() if k.lower() not in PII_KEYS}


def _serialize(inputs: dict) -> str:
    return json.dumps(inputs, default=str, sort_keys=True)


def validate_grounding(memo_text: str, inputs: dict) -> list[str]:
    """Return memo tokens with no source in the inputs (empty = grounded).

    Numeric tokens must appear verbatim in the serialized inputs (or equal one
    of its numbers); snake_case feature-name tokens must appear as substrings.
    """
    serialized = _serialize(inputs)
    allowed_numbers = set(_NUMBER_RE.findall(serialized))
    allowed_floats = {float(n) for n in allowed_numbers}
    violations = []
    for token in _NUMBER_RE.findall(memo_text):
        if token not in allowed_numbers and float(token) not in allowed_floats:
            violations.append(token)
    lowered = serialized.lower()
    for token in _FEATURE_RE.findall(memo_text):
        if token.lower() not in lowered:
            violations.append(token)
    return list(dict.fromkeys(violations))


def _fmt(value) -> str:
    """Format numbers exactly as json.dumps does, so the template memo's
    tokens match the serialized inputs and always pass validate_grounding."""
    return json.dumps(value)


def template_memo(inputs: dict) -> str:
    """Deterministic fallback memo built purely from the structured inputs,
    using the same plain-language wording as src.explain."""
    lines = ["Credit memo (auto-generated template)."]
    if inputs.get("model_version") is not None:
        lines.append(f"Model version {inputs['model_version']}.")
    if inputs.get("probability") is not None:
        lines.append("Estimated probability of default: "
                     f"{_fmt(inputs['probability'])}.")
    if inputs.get("risk_score") is not None:
        band = (f" ({inputs['risk_band']} risk band)"
                if inputs.get("risk_band") else "")
        lines.append(f"Risk score: {_fmt(inputs['risk_score'])}{band}.")
    if inputs.get("threshold_used") is not None:
        lines.append(f"Decision threshold used: {_fmt(inputs['threshold_used'])}.")
    payload = build_explanation_payload(inputs.get("top_factors") or [])
    for code in payload["reason_codes"]:
        lines.append(
            f"{code['label']} ({code['feature']}) {code['direction']} the "
            f"default risk (contribution {_fmt(code['contribution'])}).")
    if inputs.get("policy_text"):
        lines.append(f"Policy note: {inputs['policy_text']}")
    return "\n".join(lines)


def _build_prompt(inputs: dict) -> dict:
    """Prompt built ONLY from the structured inputs (plus fixed instructions);
    reason codes come from the governed src.ml.reason_codes payload."""
    body = dict(inputs)
    body["explanation"] = build_explanation_payload(
        inputs.get("top_factors") or [])
    return {"system": _SYSTEM_PROMPT,
            "user": json.dumps(body, default=str, sort_keys=True)}


def _with_footer(text: str) -> str:
    return (text.rstrip() + "\n\n" + CONTRIBUTION_DISCLAIMER + "\n"
            + HUMAN_REVIEW_LINE)


def generate_memo(inputs: dict, provider=None) -> dict:
    """Generate a grounded credit memo.

    provider=None or any provider exception -> template fallback (never raises
    for provider errors). Provider output failing validate_grounding raises
    GroundingError listing the ungrounded tokens. Every memo ends with the
    contribution disclaimer + human-review line. Returns {memo_text, provider,
    model, grounded, fallback_used} plus prompt/structured_inputs for
    persist_memo.
    """
    inputs = build_memo_inputs(**inputs)  # re-validate + redact defensively
    prompt = _build_prompt(inputs)
    provider_name, model_name, fallback_used = "template", "template", False
    if provider is None:
        text = template_memo(inputs)
        fallback_used = True
    else:
        try:
            text = provider.complete(prompt["system"], prompt["user"])
        except Exception:  # provider/network/SDK failure -> deterministic path
            text = template_memo(inputs)
            fallback_used = True
        else:
            violations = validate_grounding(text, inputs)
            if violations:
                raise GroundingError(
                    "memo rejected: token(s) not grounded in the structured "
                    "inputs: " + ", ".join(violations))
            provider_name = getattr(provider, "name", type(provider).__name__)
            model_name = getattr(provider, "model", "unknown")
    return {
        "memo_text": _with_footer(text),
        "provider": provider_name,
        "model": model_name,
        "grounded": True,  # provider text validated; fallback is grounded by construction
        "fallback_used": fallback_used,
        "prompt": prompt,
        "structured_inputs": inputs,
    }


def persist_memo(memo: dict, prediction_id, client=None) -> dict:
    """Insert a generate_memo() result into llm_reports and return the row.

    Columns match migration 0003 exactly. review_status starts at 'draft' —
    the migration's pending-human-review state (its check constraint allows
    only draft/reviewed/rejected); external use is gated until a reviewer
    flips it to 'reviewed'.
    """
    client = client or db.get_service_client()
    return client.table("llm_reports").insert({
        "prediction_id": prediction_id,
        "provider": memo["provider"],
        "model_name": memo["model"],
        "prompt": memo["prompt"],
        "structured_inputs": memo["structured_inputs"],
        "output_text": memo["memo_text"],
        "source_fields": sorted(memo["structured_inputs"].keys()),
        "redacted": True,
        "review_status": "draft",
    }).execute().data[0]

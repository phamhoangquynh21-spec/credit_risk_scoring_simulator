"""Grounded LLM credit memos (Stage 5.4).

Hallucination guardrails, in order: the prompt is built ONLY from a fixed set
of structured inputs (ALLOWED_INPUT_KEYS); application fields are PII-redacted
(recursively) before anything leaves the process; provider output is
post-validated by ``validate_grounding`` and a deterministic template fallback
(same plain-language wording as src.explain) keeps memos flowing when no
provider is configured or the provider fails. Every memo ends with the
non-causal CONTRIBUTION_DISCLAIMER plus a human-review line, and persists to
llm_reports where a review-status gate controls external use.

IMPORTANT — what the grounding check is and is NOT: ``validate_grounding`` is a
LAYERED HEURISTIC defense (numeric-token + feature-name + decision-directive
checks), NOT a guarantee of factual correctness. It can catch invented numbers,
invented feature names, and decision/review-countermanding language, but it
cannot verify that fluent, digit-free prose is truthful. The AUTHORITATIVE
control is that every memo persists with ``review_status='draft'`` and is gated
behind mandatory human review before any external use.
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
_SNAKE_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+")
_CAMEL_RE = re.compile(r"[a-z]+(?:[A-Z][a-z0-9]+)+")

# Decision directives / review-countermanding language. A memo EXPLAINS the
# score; per the locked product design the HUMAN reviewer makes the decision, so
# any of these (case-insensitive substrings/stems) in provider output is
# invalid. Stems (waiv/overrid) catch inflected forms (waiving, overriding).
_DIRECTIVE_TERMS = (
    "recommend approv", "recommend declin", "approve the", "decline the",
    "deny the", "waiv", "overrid", "skip review", "bypass review", "guarantee",
)


class GroundingError(ValueError):
    """Provider memo referenced numbers/features absent from the inputs, or used
    decision-directive / review-countermanding language."""


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
    """Strip PII keys (case-insensitive) from an application-fields dict,
    recursing into nested dicts so PII can't hide one level down (e.g.
    ``{"contact": {"email": ...}}``)."""
    cleaned = {}
    for k, v in fields.items():
        if k.lower() in PII_KEYS:
            continue
        cleaned[k] = redact(v) if isinstance(v, dict) else v
    return cleaned


def _serialize(inputs: dict) -> str:
    return json.dumps(inputs, default=str, sort_keys=True)


def validate_grounding(memo_text: str, inputs: dict) -> list[str]:
    """Return grounding violations in ``memo_text`` (empty list = passes).

    A LAYERED HEURISTIC, not a correctness guarantee (see module docstring).
    Three checks:
      1. numeric tokens must appear verbatim in the serialized inputs (or equal
         one of its numbers);
      2. feature-name tokens (snake_case AND camelCase) must appear as
         substrings of the serialized inputs — invented feature names are
         flagged;
      3. decision-directive / review-countermanding terms (see
         ``_DIRECTIVE_TERMS``) are flagged regardless of the inputs — the memo
         explains, the human decides.
    It cannot detect fabricated but digit-free, directive-free prose; the
    authoritative control is mandatory human review (review_status='draft').
    """
    serialized = _serialize(inputs)
    allowed_numbers = set(_NUMBER_RE.findall(serialized))
    allowed_floats = {float(n) for n in allowed_numbers}
    violations = []
    for token in _NUMBER_RE.findall(memo_text):
        if token not in allowed_numbers and float(token) not in allowed_floats:
            violations.append(token)
    lowered = serialized.lower()
    for regex in (_SNAKE_RE, _CAMEL_RE):
        for token in regex.findall(memo_text):
            if token.lower() not in lowered:
                violations.append(token)
    lowered_memo = memo_text.lower()
    for term in _DIRECTIVE_TERMS:
        if term in lowered_memo:
            violations.append(term)
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

    provider=None, any provider exception, or an empty/non-string provider
    response -> deterministic template fallback (never raises for provider
    failures, never persists a contentless memo). A non-empty provider response
    that fails validate_grounding raises GroundingError listing the violations
    (invented numbers/features or decision-directive language). Every memo ends
    with the contribution disclaimer + human-review line. Returns {memo_text,
    provider, model, grounded, fallback_used} plus prompt/structured_inputs for
    persist_memo. ``grounded`` reflects that the returned text passed the
    heuristic checks (or is the by-construction-grounded template) — it is not a
    factual-correctness claim; human review remains mandatory.
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
            text = None
        if not isinstance(text, str) or not text.strip():
            # None / non-str / empty / whitespace-only == provider failure.
            text = template_memo(inputs)
            fallback_used = True
        else:
            violations = validate_grounding(text, inputs)
            if violations:
                raise GroundingError(
                    "memo rejected: not grounded in the structured inputs / "
                    "used decision-directive language: " + ", ".join(violations))
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

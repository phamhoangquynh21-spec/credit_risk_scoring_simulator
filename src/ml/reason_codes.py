"""Reason codes + language guard (Stage 3.5).

Maps SHAP top factors (feature, signed contribution) to analyst-ready reason
codes, and wraps them in an explanation payload that ALWAYS carries the
non-causal disclaimer. The disclaimer is a concrete constant so a guard test can
fail the build if it is ever removed.
"""
from __future__ import annotations

from ..explain import FRIENDLY_NAMES

CONTRIBUTION_DISCLAIMER = (
    "These are feature contributions to the model score, not proof of causation."
)


def to_reason_codes(top_factors) -> list[dict]:
    """Map (feature, signed_contribution) pairs to analyst-ready reason codes.

    Each code carries a human label (from explain.FRIENDLY_NAMES where known),
    the direction it pushes default risk (↑/↓) and the magnitude of impact.
    """
    codes = []
    for feature, contribution in top_factors:
        contribution = float(contribution)
        raises_risk = contribution > 0
        codes.append({
            "feature": feature,
            "label": FRIENDLY_NAMES.get(feature, feature),
            "direction": "increases" if raises_risk else "decreases",
            "arrow": "↑" if raises_risk else "↓",
            "contribution": contribution,
            "magnitude": abs(contribution),
        })
    return codes


def build_explanation_payload(top_factors) -> dict:
    """Return the explanation payload, always including the disclaimer.

    The ``disclaimer`` key is mandatory: downstream (API/report) surfaces rely on
    it, and the guard test asserts its presence.
    """
    return {
        "reason_codes": to_reason_codes(top_factors),
        "disclaimer": CONTRIBUTION_DISCLAIMER,
    }

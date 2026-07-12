"""Tests for reason codes + the language guard (Stage 3.5)."""
from __future__ import annotations

from src.ml import reason_codes
from src.ml.reason_codes import CONTRIBUTION_DISCLAIMER, build_explanation_payload


# Mirrors explain.explain_single_customer output: (feature, signed contribution).
TOP_FACTORS = [
    ("pay_0", 0.42),
    ("credit_utilization", 0.18),
    ("limit_bal", -0.25),
    ("age", -0.05),
]


def test_to_reason_codes_maps_direction_label_magnitude():
    codes = reason_codes.to_reason_codes(TOP_FACTORS)
    assert len(codes) == len(TOP_FACTORS)

    pay_0 = codes[0]
    assert pay_0["feature"] == "pay_0"
    assert pay_0["label"] == "Most recent repayment status"  # friendly name
    assert pay_0["direction"] == "increases"
    assert pay_0["arrow"] == "↑"
    assert pay_0["magnitude"] == 0.42

    limit = next(c for c in codes if c["feature"] == "limit_bal")
    assert limit["direction"] == "decreases"
    assert limit["arrow"] == "↓"
    assert limit["magnitude"] == 0.25


def test_unknown_feature_falls_back_to_raw_name():
    codes = reason_codes.to_reason_codes([("mystery_feature", 0.1)])
    assert codes[0]["label"] == "mystery_feature"


def test_payload_always_contains_disclaimer():
    payload = build_explanation_payload(TOP_FACTORS)
    assert "reason_codes" in payload
    # GUARD: this assertion must FAIL if the disclaimer is ever removed.
    assert payload["disclaimer"] == CONTRIBUTION_DISCLAIMER
    assert "not proof of causation" in payload["disclaimer"]


def test_payload_disclaimer_present_even_with_no_factors():
    payload = build_explanation_payload([])
    assert payload["reason_codes"] == []
    assert payload["disclaimer"] == CONTRIBUTION_DISCLAIMER

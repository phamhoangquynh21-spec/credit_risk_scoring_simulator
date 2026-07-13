"""Grounded-memo tests (offline: FakeProvider + fake Supabase client)."""
from __future__ import annotations

import pytest

from src.llm import memo
from src.llm.memo import (ALLOWED_INPUT_KEYS, PII_KEYS, GroundingError,
                          build_memo_inputs, generate_memo, persist_memo,
                          redact, template_memo, validate_grounding)
from src.ml.reason_codes import CONTRIBUTION_DISCLAIMER


class FakeProvider:
    """Canned-text provider; optionally raises to simulate outages."""

    name = "fake"
    model = "fake-model-1"

    def __init__(self, text=None, error=None):
        self._text = text
        self._error = error
        self.calls = []

    def complete(self, system, user):
        self.calls.append((system, user))
        if self._error is not None:
            raise self._error
        return self._text


def _inputs():
    return build_memo_inputs(
        probability=0.72,
        risk_score=72.5,
        risk_band="High",
        threshold_used=0.42,
        model_version="1.2.0",
        top_factors=[["pay_0", 0.31], ["credit_utilization", -0.15]],
        application_fields={"limit_bal": 20000, "age": 45,
                           "name": "Jane Doe", "email": "jane@example.com"},
        policy_text="Scores above the threshold are referred for manual review.",
    )


# --- input whitelist + redaction ---------------------------------------------

def test_build_memo_inputs_rejects_unknown_keys():
    with pytest.raises(ValueError, match="ssn"):
        build_memo_inputs(probability=0.5, ssn="123-45-6789")


def test_redaction_strips_pii_keys():
    fields = {"limit_bal": 20000, "Name": "Jane Doe", "email": "j@x.com",
              "phone": "555-1234", "address": "1 Main St",
              "dob": "1981-01-01", "national_id": "A1234567", "age": 45}
    cleaned = redact(fields)
    assert cleaned == {"limit_bal": 20000, "age": 45}
    assert not set(k.lower() for k in cleaned) & PII_KEYS


def test_build_memo_inputs_redacts_application_fields():
    inputs = _inputs()
    assert set(inputs["application_fields"]) == {"limit_bal", "age"}
    assert set(inputs) <= ALLOWED_INPUT_KEYS


# --- grounding ----------------------------------------------------------------

def test_ungrounded_memo_rejected():
    # Provider invents a number (99999) and a feature (debt_to_income_ratio).
    provider = FakeProvider(
        text="Applicant income is 99999 and debt_to_income_ratio is elevated.")
    with pytest.raises(GroundingError) as excinfo:
        generate_memo(_inputs(), provider=provider)
    assert "99999" in str(excinfo.value)
    assert "debt_to_income_ratio" in str(excinfo.value)


def test_grounded_provider_memo_accepted():
    provider = FakeProvider(
        text="Probability of default is 0.72 (score 72.5, High band, "
             "threshold 0.42), driven by pay_0 and credit_utilization.")
    out = generate_memo(_inputs(), provider=provider)
    assert out["fallback_used"] is False
    assert out["grounded"] is True
    assert (out["provider"], out["model"]) == ("fake", "fake-model-1")
    assert "driven by pay_0" in out["memo_text"]
    # Prompt was built only from the structured inputs (PII never present).
    system, user = provider.calls[0]
    assert "Jane" not in user and "jane@example.com" not in user


def test_validate_grounding_passes_template_memo():
    inputs = _inputs()
    assert validate_grounding(template_memo(inputs), inputs) == []


def test_validate_grounding_lists_each_violation_once():
    violations = validate_grounding("fico_score 812 and fico_score 812 again",
                                    _inputs())
    assert violations == ["812", "fico_score"]


# --- fallback -----------------------------------------------------------------

def test_no_provider_uses_template_fallback():
    out = generate_memo(_inputs(), provider=None)
    assert out["fallback_used"] is True
    assert (out["provider"], out["model"]) == ("template", "template")
    assert "Most recent repayment status (pay_0) increases the default risk" \
        in out["memo_text"]
    assert "Credit utilisation (credit_utilization) decreases the default risk" \
        in out["memo_text"]


def test_provider_error_falls_back_without_raising():
    provider = FakeProvider(error=ConnectionError("API down"))
    out = generate_memo(_inputs(), provider=provider)  # must not raise
    assert out["fallback_used"] is True
    assert (out["provider"], out["model"]) == ("template", "template")
    assert CONTRIBUTION_DISCLAIMER in out["memo_text"]


# --- disclaimer guard -----------------------------------------------------------

def test_memo_always_contains_disclaimer():
    """Guard: FAILS if the disclaimer/human-review footer is ever removed."""
    grounded_provider = FakeProvider(text="Risk score 72.5 for this applicant.")
    for out in (generate_memo(_inputs(), provider=None),
                generate_memo(_inputs(), provider=grounded_provider),
                generate_memo(_inputs(),
                              provider=FakeProvider(error=RuntimeError("boom")))):
        assert CONTRIBUTION_DISCLAIMER in out["memo_text"]
        assert out["memo_text"].rstrip().endswith(
            "Decision-support only; human review required.")


# --- persistence (fake Supabase client, same pattern as tests/db) ---------------

class _Result:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, client, table):
        self._client = client
        self.table = table
        self.ops = []

    def __getattr__(self, name):
        def op(*args, **kwargs):
            self.ops.append((name, args, kwargs))
            return self
        return op

    def execute(self):
        self._client.calls.append(self)
        return _Result(self._client.results.pop(0) if self._client.results else [])

    def arg(self, method):
        return next(a[0] for n, a, _ in self.ops if n == method)


class FakeClient:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.calls = []

    def table(self, name):
        return _FakeQuery(self, name)


def test_persist_memo_payload_matches_llm_reports_columns():
    out = generate_memo(_inputs(), provider=None)
    fake = FakeClient(results=[[{"id": "rep-1"}]])
    row = persist_memo(out, "pred-1", client=fake)

    call = fake.calls[0]
    assert call.table == "llm_reports"
    payload = call.arg("insert")
    # Exact insertable column set from supabase/migrations/0003 llm_reports
    # (id/created_by/created_at are DB defaults).
    assert set(payload) == {"prediction_id", "provider", "model_name",
                            "prompt", "structured_inputs", "output_text",
                            "source_fields", "redacted", "review_status"}
    assert payload["prediction_id"] == "pred-1"
    assert payload["provider"] == "template"
    assert payload["model_name"] == "template"
    assert payload["prompt"] == out["prompt"]
    assert payload["structured_inputs"] == out["structured_inputs"]
    assert payload["output_text"] == out["memo_text"]
    assert payload["source_fields"] == sorted(out["structured_inputs"].keys())
    assert payload["redacted"] is True
    # Pending-human-review default (0003 check allows draft/reviewed/rejected).
    assert payload["review_status"] == "draft"
    assert row == {"id": "rep-1"}

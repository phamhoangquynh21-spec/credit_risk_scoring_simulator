"""Tests for the credit-risk MCP tools.

Scoring/explain/memo run offline from the committed models/model.pkl. Registry/
monitoring tools are credential-gated (skip cleanly without Supabase creds).
The `mcp` SDK is not required — only mcp_server.tools is exercised here.
"""
from __future__ import annotations

import json
import os

import pytest

from mcp_server import tools

_HAS_DB = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

# A representative applicant (moderate risk profile).
_APPLICANT = tools.ApplicantInput(
    limit_bal=120000, sex=2, education=2, marriage=1, age=35,
    pay_0=0, pay_2=0, pay_3=0, pay_4=0, pay_5=0, pay_6=0,
    bill_amt1=39000, bill_amt2=34000, bill_amt3=31000,
    bill_amt4=29000, bill_amt5=15000, bill_amt6=12000,
    pay_amt1=2000, pay_amt2=1500, pay_amt3=1200,
    pay_amt4=1000, pay_amt5=1000, pay_amt6=800,
)


def test_score_applicant_offline():
    result = json.loads(tools.score_applicant(_APPLICANT))
    assert 0.0 <= result["probability"] <= 1.0
    assert 0.0 <= result["risk_score"] <= 100.0
    assert result["risk_band"] in {"Low", "Medium", "High"}
    assert "decision-support" in result["disclaimer"].lower()


def test_explain_applicant_offline():
    payload = json.loads(tools.explain_applicant(_APPLICANT))
    assert payload["reason_codes"]
    assert payload["top_factors"]
    assert "causation" in payload["disclaimer"].lower()


def test_generate_memo_uses_template_fallback_offline():
    memo = json.loads(tools.generate_memo(_APPLICANT))
    assert memo["fallback_used"] is True          # no provider configured
    assert memo["memo_text"].strip()
    assert "human review required" in memo["memo_text"].lower()


def test_list_data_sources_returns_registry():
    text = tools.list_data_sources()
    # docs/data_sources.md mirrors the connector table.
    assert "RBA" in text or "connector" in text.lower()


def test_applicant_input_rejects_unknown_field():
    with pytest.raises(Exception):
        tools.ApplicantInput(limit_bal=1000, sex=1, education=1, marriage=1, age=30,
                             pay_0=0, pay_2=0, pay_3=0, pay_4=0, pay_5=0, pay_6=0,
                             bill_amt1=0, pay_amt1=0, bogus_field=1)


def test_get_champion_without_db_returns_actionable_message(monkeypatch):
    monkeypatch.setattr(tools, "_try_champion", lambda: None)
    result = json.loads(tools.get_champion())
    assert result["error"] == "supabase_unavailable"
    assert "SUPABASE_URL" in result["message"]


@pytest.mark.skipif(not _HAS_DB, reason="needs Supabase credentials")
def test_get_champion_live():
    result = json.loads(tools.get_champion())
    assert "semver" in result and "threshold" in result


@pytest.mark.skipif(not _HAS_DB, reason="needs Supabase credentials")
def test_score_applicant_live_includes_threshold_and_recommendation():
    result = json.loads(tools.score_applicant(_APPLICANT))
    assert "threshold_used" in result
    assert result["recommendation"] in {"approve", "decline"}

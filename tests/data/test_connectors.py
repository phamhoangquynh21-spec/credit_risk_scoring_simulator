"""Offline tests for macro connectors (RBA/ABS/APRA) and the HMDA loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.data.connectors import abs as abs_
from src.data.connectors import apra, hmda, rba

from .fakes import FakeClient

FIXTURES = Path(__file__).parent / "fixtures"


# --- RBA --------------------------------------------------------------------

def test_rba_parse_yields_indicator_rows():
    rows = rba.parse(FIXTURES / "rba_sample.csv")
    assert {"source": "RBA", "indicator": "BHFDDIT",
            "period": "2025-12-31", "value": 188.5} in rows
    assert {"source": "RBA", "indicator": "BHFADIT",
            "period": "2026-03-31", "value": 932.7} in rows
    assert all(r["source"] == "RBA" for r in rows)
    assert len(rows) == 4  # 2 periods x 2 series


def test_rba_ingest_upserts_parsed_rows():
    fake = FakeClient()
    rows = rba.ingest(FIXTURES / "rba_sample.csv", client=fake)
    call = fake.calls[0]
    assert call.table == "macro_indicators"
    assert call.arg("upsert") == rows
    assert all(r["source"] == "RBA" for r in call.arg("upsert"))


# --- APRA -------------------------------------------------------------------

def test_apra_parse_melts_indicator_columns():
    rows = apra.parse(FIXTURES / "apra_sample.csv")
    assert {"source": "APRA", "indicator": "housing_loans_total",
            "period": "2026-02-01", "value": 2145300.0} in rows
    assert len(rows) == 4  # 2 periods x 2 indicators


def test_apra_ingest_upserts():
    fake = FakeClient()
    rows = apra.ingest(FIXTURES / "apra_sample.csv", client=fake)
    assert fake.calls[0].table == "macro_indicators"
    assert fake.calls[0].arg("upsert") == rows


# --- ABS --------------------------------------------------------------------

def test_abs_parse_reads_sdmx_csv():
    rows = abs_.parse(FIXTURES / "abs_sample.csv")
    assert rows == [
        {"source": "ABS", "indicator": "Unemployment rate",
         "period": "2026-02-01", "value": 4.1},
        {"source": "ABS", "indicator": "Unemployment rate",
         "period": "2026-03-01", "value": 4.2},
    ]


def test_abs_ingest_from_fixture_upserts(monkeypatch):
    # Parsing a supplied file needs no key; a fake client keeps it offline.
    monkeypatch.delenv(abs_.API_KEY_ENV, raising=False)
    fake = FakeClient()
    rows = abs_.ingest(FIXTURES / "abs_sample.csv", client=fake)
    assert fake.calls[0].arg("upsert") == rows


def test_abs_fetch_without_key_fails_loudly(monkeypatch):
    monkeypatch.delenv(abs_.API_KEY_ENV, raising=False)
    with pytest.raises(RuntimeError, match=abs_.API_KEY_ENV):
        abs_.fetch()


def test_abs_ingest_without_source_or_key_fails_loudly(monkeypatch):
    monkeypatch.delenv(abs_.API_KEY_ENV, raising=False)
    with pytest.raises(RuntimeError, match=abs_.API_KEY_ENV):
        abs_.ingest(client=FakeClient())


# --- HMDA -------------------------------------------------------------------

def test_hmda_load_normalises_demographics_and_outcomes():
    df = hmda.load(FIXTURES / "hmda_sample.csv")
    assert {"sex", "race", "ethnicity", "action_taken",
            "originated", "denied"} <= set(df.columns)
    assert len(df) == 4
    # Row 2 (denied application) -> denied=1, originated=0.
    denied = df[df["denied"] == 1]
    assert set(denied["action_taken"].tolist()) == {3}
    assert (df["originated"] + df["denied"] <= 1).all()


def test_hmda_load_missing_columns_raises(tmp_path):
    bad = tmp_path / "bad_hmda.csv"
    bad.write_text("foo,bar\n1,2\n")
    with pytest.raises(ValueError, match="missing expected columns"):
        hmda.load(bad)

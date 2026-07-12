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
    assert {"source": "APRA", "indicator": "household_deposits_total",
            "period": "2026-02-01", "value": 1523400.0} in rows
    # 2 periods x 2 numeric indicators; the descriptive institution_type column
    # is non-numeric and skipped, not crashed on.
    assert len(rows) == 4
    assert not any(r["indicator"] == "institution_type" for r in rows)


def test_apra_parse_handles_thousands_separator():
    rows = apra.parse(FIXTURES / "apra_sample.csv")
    # "1,234.5" in the fixture must parse to 1234.5, not abort ingest.
    assert {"source": "APRA", "indicator": "housing_loans_total",
            "period": "2026-02-01", "value": 1234.5} in rows


def test_apra_ingest_upserts():
    fake = FakeClient()
    rows = apra.ingest(FIXTURES / "apra_sample.csv", client=fake)
    assert fake.calls[0].table == "macro_indicators"
    assert fake.calls[0].arg("upsert") == rows


# --- ABS --------------------------------------------------------------------

def test_abs_parse_reads_sdmx_csv():
    rows = abs_.parse(FIXTURES / "abs_sample.csv")
    assert all(r["source"] == "ABS" for r in rows)
    # indicator composes MEASURE + every other dimension (DATAFLOW, SEX, AGE).
    assert {"source": "ABS", "indicator": "Unemployment rate.ABS:LF.Male.15-24",
            "period": "2026-02-01", "value": 9.1} in rows
    assert len(rows) == 4  # 2 groups x 2 periods


def test_abs_parse_multidimensional_series_do_not_collide():
    # Two SEX groups share the same MEASURE + TIME_PERIOD; they must produce
    # DISTINCT (source, indicator, period) keys, not collapse onto one PK.
    rows = abs_.parse(FIXTURES / "abs_sample.csv")
    feb = [r for r in rows if r["period"] == "2026-02-01"]
    keys = {(r["source"], r["indicator"], r["period"]) for r in feb}
    assert len(feb) == 2
    assert len(keys) == 2  # no collision
    assert {r["value"] for r in feb} == {9.1, 8.4}


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
    assert len(df) == 5
    # Denied applications -> denied=1, originated=0.
    denied = df[df["denied"] == 1]
    assert set(denied["action_taken"].dropna().tolist()) == {3}
    assert (df["originated"] + df["denied"] <= 1).all()


def test_hmda_load_survives_missing_action_taken():
    # A row with an NA action_taken must not abort the load (nullable Int64);
    # it maps to 0 on both outcomes.
    df = hmda.load(FIXTURES / "hmda_sample.csv")
    na_row = df[df["action_taken"].isna()]
    assert len(na_row) == 1
    assert na_row["originated"].iloc[0] == 0
    assert na_row["denied"].iloc[0] == 0


def test_hmda_load_missing_columns_raises(tmp_path):
    bad = tmp_path / "bad_hmda.csv"
    bad.write_text("foo,bar\n1,2\n")
    with pytest.raises(ValueError, match="missing expected columns"):
        hmda.load(bad)

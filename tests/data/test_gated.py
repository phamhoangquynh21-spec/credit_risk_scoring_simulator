"""Offline tests for gated connectors: disabled by default, fail loudly."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.data.connectors.gated import (BureauSource, FreddieMacSource,
                                       OpenBankingSource, _GatedSource)

from .fakes import FakeClient

FIXTURES = Path(__file__).parent / "fixtures"
EXTRACT = FIXTURES / "gated_extract_sample.csv"

ALL_GATED = [FreddieMacSource, BureauSource, OpenBankingSource]

# Fake flags client states: absent row -> is_enabled default False (OFF).
FLAG_OFF = lambda: FakeClient(results=[[]])
FLAG_ON = lambda: FakeClient(results=[[{"enabled": True}]])


@pytest.mark.parametrize("cls", ALL_GATED)
def test_disabled_by_default_names_flag_and_approval(cls):
    src = cls(path=EXTRACT, flags_client=FLAG_OFF())
    with pytest.raises(RuntimeError) as exc:
        src.load()
    msg = str(exc.value)
    assert cls.FLAG_KEY in msg
    assert "disabled" in msg
    # Names the external approval gate.
    assert cls.APPROVAL.split()[0].lower() in msg.lower()


@pytest.mark.parametrize("cls", ALL_GATED)
def test_enabled_without_creds_fails_loudly(cls, monkeypatch):
    for var in cls.REQUIRED_ENV:
        monkeypatch.delenv(var, raising=False)
    src = cls(path=EXTRACT, flags_client=FLAG_ON())
    with pytest.raises(RuntimeError, match="credentials are|missing"):
        src.load()


@pytest.mark.parametrize("cls", ALL_GATED)
def test_enabled_with_creds_loads_frame(cls, monkeypatch):
    for var in cls.REQUIRED_ENV:
        monkeypatch.setenv(var, "dummy")
    src = cls(path=EXTRACT, flags_client=FLAG_ON())
    df = src.load()
    assert len(df) == 2
    assert "borrower_id" in df.columns


@pytest.mark.parametrize("cls", ALL_GATED)
def test_flag_defaults_off(cls):
    # With no flag row present, the gate must read as OFF (default deny).
    from src.db import is_enabled
    assert is_enabled(cls.FLAG_KEY, client=FakeClient(results=[[]])) is False


def test_gated_flag_keys_are_the_documented_three():
    keys = {c.FLAG_KEY for c in ALL_GATED}
    assert keys == {"freddie_enabled", "bureau_enabled", "openbanking_enabled"}


def test_base_gated_is_abstract_via_subclasses_only():
    # Sanity: subclasses set the required contract attributes.
    for cls in ALL_GATED:
        assert issubclass(cls, _GatedSource)
        assert cls.FLAG_KEY and cls.REQUIRED_ENV and cls.APPROVAL

"""Offline tests for the DataSource interface (SyntheticSource, CsvSource)."""
from __future__ import annotations

from pathlib import Path

import pytest

from src import config
from src.data import RAW_COLUMNS, CsvSource, SyntheticSource

FIXTURES = Path(__file__).parent / "fixtures"


def test_synthetic_source_schema_and_shape():
    df = SyntheticSource(n=250, seed=7).load()
    assert list(df.columns) == RAW_COLUMNS
    assert len(df) == 250
    # Genuine raw schema: dotted target present, values are 0/1.
    assert set(df["default.payment.next.month"].unique()) <= {0, 1}


def test_synthetic_source_is_deterministic():
    a = SyntheticSource(n=100, seed=1).load()
    b = SyntheticSource(n=100, seed=1).load()
    assert a.equals(b)


def test_csv_source_loads_fixture():
    df = CsvSource(FIXTURES / "raw_uci_sample.csv").load()
    assert list(df.columns) == RAW_COLUMNS
    assert len(df) == 3


def test_csv_source_reads_real_uci_file():
    # Deliverable: must read the committed real-UCI file unchanged.
    df = CsvSource(config.RAW_CSV).load()
    assert list(df.columns) == RAW_COLUMNS
    assert len(df) == 30_000


def test_csv_source_wrong_schema_raises_helpful_error(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b,c\n1,2,3\n")
    with pytest.raises(ValueError, match="raw-UCI-schema"):
        CsvSource(bad).load()


def test_csv_source_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        CsvSource(FIXTURES / "does_not_exist.csv").load()

"""APRA statistics connector (free, public, no key).

APRA publishes tidy statistical CSVs with a ``Period`` column and one column per
indicator. We melt every non-Period column into macro_indicators rows.

Attribution: Australian Prudential Regulation Authority statistics.
"""
from __future__ import annotations

import io

import pandas as pd

from ...db import upsert_indicators
from . import to_float, to_iso_period

SOURCE = "APRA"
PERIOD_COL = "Period"
# Example: Monthly authorised deposit-taking institution statistics (no key).
FETCH_URL = "https://www.apra.gov.au/sites/default/files/monthly_adi_statistics.csv"


def parse(path_or_bytes) -> list[dict]:
    """Parse an APRA wide CSV (Period + indicator columns) into rows."""
    buf = io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, (bytes, bytearray)) else path_or_bytes
    df = pd.read_csv(buf, dtype=str)
    if PERIOD_COL not in df.columns:
        raise ValueError(f"APRA: expected a '{PERIOD_COL}' column, got {list(df.columns)}")

    rows: list[dict] = []
    for _, r in df.iterrows():
        period = to_iso_period(r[PERIOD_COL])
        for indicator in df.columns:
            if indicator == PERIOD_COL:
                continue
            value = to_float(r[indicator])
            if value is None:  # blank / descriptive / non-numeric column -> skip
                continue
            rows.append({"source": SOURCE, "indicator": str(indicator),
                         "period": period, "value": value})
    return rows


def fetch() -> bytes:
    """Download the live APRA statistics CSV (no credential required)."""
    import requests

    resp = requests.get(FETCH_URL, timeout=120)
    resp.raise_for_status()
    return resp.content


def ingest(path_or_bytes=None, client=None) -> list[dict]:
    """Parse (fetching live if no source given) then upsert to macro_indicators."""
    rows = parse(path_or_bytes if path_or_bytes is not None else fetch())
    upsert_indicators(rows, client=client)
    return rows

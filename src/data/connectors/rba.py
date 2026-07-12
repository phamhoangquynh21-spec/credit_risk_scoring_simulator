"""RBA statistical-tables connector (free, public, no key).

RBA CSV tables carry a metadata block, then a row whose first cell is
``Series ID`` naming each column's series, then dated observation rows. We key
off the ``Series ID`` row for indicator codes and treat any later row with a
parseable date in column 0 as data.

Attribution: Reserve Bank of Australia statistical tables.
"""
from __future__ import annotations

import io

import pandas as pd

from ...db import upsert_indicators
from . import to_float, to_iso_period

SOURCE = "RBA"
# Example: F-series household finances table (no key required to download).
FETCH_URL = "https://www.rba.gov.au/statistics/tables/csv/e2-data.csv"


def parse(path_or_bytes) -> list[dict]:
    """Parse an RBA statistical-table CSV into macro_indicators rows."""
    buf = io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, (bytes, bytearray)) else path_or_bytes
    raw = pd.read_csv(buf, header=None, dtype=str)

    id_rows = raw.index[raw[0].astype(str).str.strip() == "Series ID"]
    if len(id_rows) == 0:
        raise ValueError("RBA: no 'Series ID' header row found in table")
    id_row = id_rows[0]
    series_ids = raw.iloc[id_row, 1:].tolist()

    rows: list[dict] = []
    for _, r in raw.iloc[id_row + 1:].iterrows():
        try:
            period = to_iso_period(r[0])
        except (ValueError, TypeError):
            continue  # metadata / blank line, not an observation
        for col, indicator in enumerate(series_ids, start=1):
            if indicator is None or pd.isna(indicator):
                continue
            value = to_float(r[col])
            if value is None:  # blank / descriptive / non-numeric cell -> skip
                continue
            rows.append({"source": SOURCE, "indicator": str(indicator).strip(),
                         "period": period, "value": value})
    return rows


def fetch() -> bytes:
    """Download the live RBA CSV table (no credential required)."""
    import requests

    resp = requests.get(FETCH_URL, timeout=120)
    resp.raise_for_status()
    return resp.content


def ingest(path_or_bytes=None, client=None) -> list[dict]:
    """Parse (fetching live if no source given) then upsert to macro_indicators."""
    rows = parse(path_or_bytes if path_or_bytes is not None else fetch())
    upsert_indicators(rows, client=client)
    return rows

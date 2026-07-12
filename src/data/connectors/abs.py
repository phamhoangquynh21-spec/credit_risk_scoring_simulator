"""ABS Data API connector (free, requires a registered API key to *fetch*).

Parsing an already-downloaded ABS SDMX-CSV file needs no key; only the live
``fetch()`` (and ``ingest()`` when it must fetch) requires ``ABS_API_KEY``. The
SDMX-CSV format carries a measure column, a ``TIME_PERIOD`` and an ``OBS_VALUE``.

Attribution: Australian Bureau of Statistics Data API (per API terms of use).
Free key: register at https://api.gov.au / ABS Data API portal.
"""
from __future__ import annotations

import io
import os

import pandas as pd

from ...db import upsert_indicators
from . import to_float, to_iso_period

SOURCE = "ABS"
API_KEY_ENV = "ABS_API_KEY"
MEASURE_COL = "MEASURE"
PERIOD_COL = "TIME_PERIOD"
VALUE_COL = "OBS_VALUE"
FETCH_URL = "https://api.data.abs.gov.au/data"


def _require_key() -> str:
    key = os.environ.get(API_KEY_ENV)
    if not key:
        raise RuntimeError(
            f"ABS connector needs the {API_KEY_ENV} environment variable. "
            f"Register for a free ABS Data API key and set {API_KEY_ENV} before "
            "fetching live data."
        )
    return key


def parse(path_or_bytes) -> list[dict]:
    """Parse an ABS SDMX-CSV file into macro_indicators rows (no key needed).

    ABS series are multi-dimensional: the same MEASURE at the same TIME_PERIOD
    can appear for many SEX/AGE/REGION groups. To avoid collapsing distinct
    series onto one (source, indicator, period) key (which would silently drop
    rows), ``indicator`` is a composite of MEASURE plus every other dimension
    column's value.
    """
    buf = io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, (bytes, bytearray)) else path_or_bytes
    df = pd.read_csv(buf, dtype=str)
    for col in (MEASURE_COL, PERIOD_COL, VALUE_COL):
        if col not in df.columns:
            raise ValueError(f"ABS: expected column '{col}', got {list(df.columns)}")

    # Dimension columns = everything except the period and observation value.
    # MEASURE leads the composite key; remaining dimensions follow in column order.
    dim_cols = [MEASURE_COL] + [c for c in df.columns
                                if c not in (MEASURE_COL, PERIOD_COL, VALUE_COL)]

    rows: list[dict] = []
    for _, r in df.iterrows():
        value = to_float(r[VALUE_COL])
        if value is None:
            continue
        indicator = ".".join(str(r[c]) for c in dim_cols)
        rows.append({"source": SOURCE, "indicator": indicator,
                     "period": to_iso_period(r[PERIOD_COL]),
                     "value": value})
    return rows


def fetch() -> bytes:
    """Download live ABS data (requires ABS_API_KEY)."""
    import requests

    key = _require_key()
    resp = requests.get(FETCH_URL, headers={"x-api-key": key},
                        params={"format": "csv"}, timeout=120)
    resp.raise_for_status()
    return resp.content


def ingest(path_or_bytes=None, client=None) -> list[dict]:
    """Parse (fetching live — requires key — if no source given) then upsert."""
    rows = parse(path_or_bytes if path_or_bytes is not None else fetch())
    upsert_indicators(rows, client=client)
    return rows

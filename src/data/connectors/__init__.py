"""Macro/reference connectors → macro_indicators rows.

Each module exposes ``parse(path_or_bytes) -> list[dict]`` and
``ingest(path_or_bytes=None, client=None)``; the live ``fetch()`` download is
never exercised in tests. ``to_iso_period`` normalises the varied source date
formats to an ISO date string (macro_indicators.period is a DATE).
"""
from __future__ import annotations

import pandas as pd


def to_iso_period(raw) -> str:
    """Normalise a source date ('2026-03', '31-Dec-2025', '2026-03-31') to ISO."""
    return pd.to_datetime(str(raw)).date().isoformat()


def to_float(val):
    """Parse a source cell to float, tolerating thousands separators.

    Returns ``None`` for blank/NA/non-numeric cells (descriptive columns common
    in real APRA/RBA files) so the caller can skip rather than crash.
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip().replace(",", "")
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None

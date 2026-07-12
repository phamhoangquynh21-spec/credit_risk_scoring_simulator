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

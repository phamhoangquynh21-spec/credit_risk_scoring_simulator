"""Access over macro_indicators (PK: source, indicator, period).

Pass `period` as an ISO date string (date column), e.g. "2026-01-01".
"""
from __future__ import annotations

from .client import get_service_client


def upsert_indicators(rows: list[dict], client=None) -> None:
    """Batch upsert of {source, indicator, period, value} dicts."""
    client = client or get_service_client()
    client.table("macro_indicators").upsert(rows).execute()


def get_indicators(source, indicator, since=None, client=None) -> list:
    """Series for (source, indicator), ordered by period; optionally >= since."""
    client = client or get_service_client()
    q = (client.table("macro_indicators").select("*")
         .eq("source", source).eq("indicator", indicator))
    if since is not None:
        q = q.gte("period", since)
    return q.order("period").execute().data

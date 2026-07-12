"""Time-series writes/reads over monitoring_metrics (PK: period, metric).

Pass `period` as an ISO-8601 timestamp string (timestamptz column).
"""
from __future__ import annotations

from .client import get_service_client


def record_metric(period, metric, value, client=None) -> None:
    """Upsert one metric point (idempotent on the (period, metric) PK)."""
    client = client or get_service_client()
    client.table("monitoring_metrics").upsert(
        {"period": period, "metric": metric, "value": value}).execute()


def record_metrics(rows: list, client=None) -> None:
    """Batch upsert of {period, metric, value} dicts."""
    client = client or get_service_client()
    client.table("monitoring_metrics").upsert(rows).execute()


def get_metrics(metric, since=None, client=None) -> list:
    """All points for a metric, ordered by period; optionally period >= since."""
    client = client or get_service_client()
    q = client.table("monitoring_metrics").select("*").eq("metric", metric)
    if since is not None:
        q = q.gte("period", since)
    return q.order("period").execute().data

"""Feature flag reads/writes over feature_flags (consumed by gated connectors)."""
from __future__ import annotations

from .client import get_service_client


def is_enabled(key, default=False, client=None) -> bool:
    """Return the flag's enabled state, or `default` when the flag is absent."""
    client = client or get_service_client()
    rows = (client.table("feature_flags").select("enabled")
            .eq("key", key).limit(1).execute().data)
    return rows[0]["enabled"] if rows else default


def set_flag(key, enabled, note=None, client=None) -> None:
    """Upsert a flag's full state (a None note clears any existing note)."""
    client = client or get_service_client()
    client.table("feature_flags").upsert(
        {"key": key, "enabled": enabled, "note": note}).execute()

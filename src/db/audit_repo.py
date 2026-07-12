"""Append-only writes to audit_logs."""
from __future__ import annotations

from .client import get_service_client


def log_action(actor_id, action, entity_type, entity_id=None,
               detail: dict | None = None, client=None) -> dict:
    """Append one audit_logs row and return it.

    actor_id=None records a service-role (non-user) action. The table is
    append-only for client roles; there is deliberately no update/delete here.
    """
    client = client or get_service_client()
    return client.table("audit_logs").insert({
        "actor_id": actor_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "detail": detail or {},
    }).execute().data[0]

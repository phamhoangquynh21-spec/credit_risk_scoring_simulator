"""GET /api/v1/audit/events — governance/compliance export of audit_logs.

Read-only. Gated to governance/compliance roles (admin always allowed via
require_role). Returns recent audit_logs rows as JSON, or CSV with ?format=csv.
"""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

import src.db as db

from ..auth import Principal, require_role

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])

_COLUMNS = ["id", "actor_id", "action", "entity_type", "entity_id", "detail",
            "created_at"]


def _recent_events(limit: int) -> list[dict]:
    return (db.get_service_client().table("audit_logs")
            .select(",".join(_COLUMNS)).order("created_at", desc=True)
            .limit(limit).execute().data)


@router.get("/events")
def audit_events(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    limit: int = Query(default=100, ge=1, le=1000),
    principal: Principal = Depends(require_role("governance", "compliance")),
):
    rows = _recent_events(limit)
    if format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c) for c in _COLUMNS})
        return Response(content=buf.getvalue(), media_type="text/csv")
    return {"count": len(rows), "events": rows}

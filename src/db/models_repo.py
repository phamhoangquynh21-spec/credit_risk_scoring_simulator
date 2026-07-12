"""Model registry access over model_versions (see migration 0003)."""
from __future__ import annotations

from . import audit_repo
from .client import get_service_client

ALLOWED_STAGES = {"dev", "staging", "champion", "retired"}


def register_model_version(semver, algo, metrics: dict, trained_on, threshold,
                           stage="dev", client=None) -> dict:
    """Insert a new model version and return the inserted row."""
    client = client or get_service_client()
    return client.table("model_versions").insert({
        "semver": semver,
        "algo": algo,
        "metrics": metrics,
        "trained_on": trained_on,
        "threshold": threshold,
        "stage": stage,
    }).execute().data[0]


def get_model_version(semver, client=None) -> dict | None:
    client = client or get_service_client()
    rows = (client.table("model_versions").select("*")
            .eq("semver", semver).limit(1).execute().data)
    return rows[0] if rows else None


def get_champion(client=None) -> dict | None:
    client = client or get_service_client()
    rows = (client.table("model_versions").select("*")
            .eq("stage", "champion").limit(1).execute().data)
    return rows[0] if rows else None


def promote_model(semver, to_stage, client=None) -> dict:
    """Move a model version to a new lifecycle stage; returns the updated row.

    The target semver is looked up FIRST: if it does not exist this raises
    ValueError before touching any row, so a typo'd/nonexistent semver can
    never retire the incumbent champion (fail-safe: the DB is never left with
    zero champions). Only after the target is confirmed, promoting to
    'champion' demotes any OTHER current champions to 'retired'. That demotion
    and the target update are two separate PostgREST calls and are NOT
    transactional: a crash between them can briefly leave no champion.

    Governance write: records an audit_logs entry via audit_repo.log_action
    (actor_id=None, i.e. a service-role action).
    """
    if to_stage not in ALLOWED_STAGES:
        raise ValueError(
            f"invalid stage {to_stage!r}; allowed: {sorted(ALLOWED_STAGES)}")
    client = client or get_service_client()

    if get_model_version(semver, client=client) is None:
        raise ValueError(f"model version {semver!r} not found")

    detail = {"to_stage": to_stage}
    if to_stage == "champion":
        others = (client.table("model_versions").select("semver")
                  .eq("stage", "champion").neq("semver", semver)
                  .execute().data)
        if others:
            (client.table("model_versions").update({"stage": "retired"})
             .eq("stage", "champion").neq("semver", semver).execute())
            detail["demoted"] = [r["semver"] for r in others]

    row = (client.table("model_versions").update({"stage": to_stage})
           .eq("semver", semver).execute().data[0])
    audit_repo.log_action(None, "promote_model", "model_version", semver,
                          detail, client=client)
    return row

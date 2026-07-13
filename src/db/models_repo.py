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


def promote_model(semver, to_stage, approved_by=None, client=None) -> dict:
    """Move a model version to a new lifecycle stage; returns the updated row.

    Governance gate: promoting to 'champion' requires an explicit governance
    approval — `approved_by` must be a non-None user id, else this raises
    ValueError before touching any row. Both up-front checks (approval gate and
    target existence) run BEFORE any write, so a missing approval or a
    typo'd/nonexistent semver can never retire the incumbent champion
    (fail-safe: the DB is never left with zero champions). For non-champion
    stages (dev/staging/retired) `approved_by` is not required and is ignored.

    The target semver is looked up before mutating: if it does not exist this
    raises ValueError. Only after both checks pass, promoting to 'champion'
    demotes any OTHER current champions to 'retired' and stamps `approved_by`
    on the target row. That demotion and the target update are two separate
    PostgREST calls and are NOT transactional: a crash between them can briefly
    leave no champion.

    Governance write: records an audit_logs entry via audit_repo.log_action
    (actor_id=None, i.e. a service-role action); for champion promotions the
    audit detail includes `approved_by`.
    """
    if to_stage not in ALLOWED_STAGES:
        raise ValueError(
            f"invalid stage {to_stage!r}; allowed: {sorted(ALLOWED_STAGES)}")
    if to_stage == "champion" and approved_by is None:
        raise ValueError(
            "promotion to champion requires governance approval (approved_by)")
    client = client or get_service_client()

    if get_model_version(semver, client=client) is None:
        raise ValueError(f"model version {semver!r} not found")

    detail = {"to_stage": to_stage}
    update = {"stage": to_stage}
    if to_stage == "champion":
        update["approved_by"] = approved_by
        detail["approved_by"] = approved_by
        others = (client.table("model_versions").select("semver")
                  .eq("stage", "champion").neq("semver", semver)
                  .execute().data)
        if others:
            (client.table("model_versions").update({"stage": "retired"})
             .eq("stage", "champion").neq("semver", semver).execute())
            detail["demoted"] = [r["semver"] for r in others]

    row = (client.table("model_versions").update(update)
           .eq("semver", semver).execute().data[0])
    audit_repo.log_action(None, "promote_model", "model_version", semver,
                          detail, client=client)
    return row

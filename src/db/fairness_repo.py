"""Access over fairness_runs / fairness_results (see migration 0003)."""
from __future__ import annotations

from .client import get_service_client


def create_fairness_run(model_version_id, client=None) -> str:
    """Insert a fairness_runs row and return its id."""
    client = client or get_service_client()
    return (client.table("fairness_runs")
            .insert({"model_version_id": model_version_id})
            .execute().data[0]["id"])


def add_fairness_results(run_id, results: list[dict], client=None) -> None:
    """Batch insert per-group results for a run.

    Each dict carries the fairness_results columns: attribute, grp, n,
    selection_rate, recall, precision, disparity_ratio.
    """
    client = client or get_service_client()
    client.table("fairness_results").insert(
        [{"run_id": run_id, **r} for r in results]).execute()


def get_latest_run_results(model_version_id, client=None) -> list:
    """Results of the most recent fairness run that actually has results.

    Runs are scanned newest-first, so an empty/failed run (a fairness_runs row
    with no fairness_results) is skipped in favour of the prior good run
    instead of masking it. Returns [] only when no run has any results.
    """
    client = client or get_service_client()
    runs = (client.table("fairness_runs").select("id")
            .eq("model_version_id", model_version_id)
            .order("run_at", desc=True).execute().data)
    for run in runs:
        results = (client.table("fairness_results").select("*")
                   .eq("run_id", run["id"]).execute().data)
        if results:
            return results
    return []

"""Thin Supabase access layer over the governance/monitoring tables.

Stages 3/5/6/7 (ML registry, monitoring, data connectors, governance) call
these repos instead of reinventing Supabase calls. All functions accept an
optional `client=` for test injection and default to the cached service-role
client; `supabase` itself is imported lazily so importing src.db is free.
"""
from .audit_repo import log_action
from .client import get_service_client
from .fairness_repo import (add_fairness_results, create_fairness_run,
                            get_latest_run_results)
from .flags_repo import is_enabled, set_flag
from .macro_repo import get_indicators, upsert_indicators
from .models_repo import (get_champion, get_model_version, promote_model,
                          register_model_version)
from .monitoring_repo import get_metrics, record_metric, record_metrics

__all__ = [
    "get_service_client",
    "register_model_version", "get_model_version", "get_champion", "promote_model",
    "record_metric", "record_metrics", "get_metrics",
    "create_fairness_run", "add_fairness_results", "get_latest_run_results",
    "upsert_indicators", "get_indicators",
    "log_action",
    "is_enabled", "set_flag",
]

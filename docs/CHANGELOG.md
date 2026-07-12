# Changelog

## Stage 1 — src/db access layer (2026-07-12)

Added `src/db/`, a thin Python access layer over the governance/monitoring
tables that already exist in Supabase (migrations 0001–0007) — no new tables,
no ORM. `client.get_service_client()` provides a cached service-role client
(lazy `supabase` import, matching `services/ml/persistence.py`), and six repos
wrap the tables Stages 3/5/6/7 need: `models_repo` (register/get/promote over
`model_versions`, with champion demotion + audit logging on promote),
`monitoring_repo` (`monitoring_metrics` upserts/reads), `fairness_repo`
(`fairness_runs`/`fairness_results`), `macro_repo` (`macro_indicators`),
`audit_repo` (append-only `audit_logs`), and `flags_repo` (`feature_flags`).
All functions accept an optional `client=` for test injection. Covered by 22
unit tests (fake client, no network) and 6 credential-gated integration tests
that round-trip disposable rows against the live project and clean up after
themselves.

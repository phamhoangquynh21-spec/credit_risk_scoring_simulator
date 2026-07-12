# Changelog

## Stage 3 — governed ML lifecycle (2026-07-12)

Added `src/ml/`, a set of governed-lifecycle helpers with all optional/heavy
dependencies lazy-imported so `import src.ml` stays cheap and serving/deploy
never need mlflow. `registry.py` logs each training run to a local `mlruns/`
file store and `register_from_training` threads the MLflow run_id into the
existing `model_versions.metrics` JSON (`mlflow_run_id` key — no new column);
`train_model.run_training()` gains a best-effort MLflow log wrapped in
try/except so training still works without mlflow. `feature_contract.py` pins an
explicit 28-feature contract (dtype + range or allowed categories, names derived
from `config`) with `validate_frame`/`validate_row` raising `FeatureContractError`.
`calibration.py` wraps a prefit estimator in `CalibratedClassifierCV` (isotonic,
Platt fallback under 1000 samples) without touching `model.pkl`, plus Brier and
a saved reliability curve. `threshold.py` replaces the fixed 0.5 with a
cost-sensitive optimiser (`FN_COST=5`, `FP_COST=1`); the chosen threshold is
persisted through the governed registration path (`register_from_training`).
`reason_codes.py` maps SHAP top factors to analyst-ready reason codes and always
appends the non-causal `CONTRIBUTION_DISCLAIMER`. The new `mlflow` dependency
lives only in `requirements-train.txt`. Covered by 20 offline unit tests
(fake mlflow + fake db client, no network); all existing signatures, prints and
`model.pkl` are unchanged.

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

# Changelog

## Stage 6 — data connectors (2026-07-12)

Added `src/data/`, an additive data layer that never touches `models/` or the
training path. `base.py` defines the `DataSource` ABC plus `RAW_COLUMNS` (the
raw UCI uppercase schema) and `validate_raw_schema`, so every source feeds the
existing `src.preprocessing` chain unchanged. `sources.py` ships
`SyntheticSource` (wraps `generate_raw`) and `CsvSource` (reads any raw-UCI CSV,
including the committed real-UCI file, with a helpful error on column mismatch).
Macro connectors `connectors/{rba,abs,apra}.py` each expose
`parse(path_or_bytes) -> list[dict]`, `fetch()` (live download; RBA/APRA keyless,
ABS requires `ABS_API_KEY`) and `ingest(path_or_bytes=None, client=None)` which
upserts to `macro_indicators` via `src.db.upsert_indicators`; ABS `fetch`/`ingest`
without a key fail loudly naming the var. `connectors/hmda.py` normalises an HMDA
LAR sample to demographic + binary-outcome columns for the (Stage 7) fairness
pipeline. `connectors/gated.py` builds `FreddieMacSource`, `BureauSource`,
`OpenBankingSource` on the `DataSource` interface but **shipped disabled**: each
`load()` checks `src.db.is_enabled(<flag>)` (keys `freddie_enabled`,
`bureau_enabled`, `openbanking_enabled` — all default OFF) then the required env
creds, raising a clear message naming the flag + external approval (license
verification / commercial contract + legal approval / CDR accreditation) or the
missing credential. `requests` is imported lazily inside `fetch()` only, so
`import src.data` stays cheap. Documented in `docs/data_sources.md`. Covered by
30 offline tests (committed fixtures + fake `src.db` client, no network/DB).

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

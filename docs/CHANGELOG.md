# Changelog

## Stage 2 — API wiring (2026-07-13)

Wires the Stage 3/5/7 capabilities into the live FastAPI ML service
(`services/ml/`). All response-schema changes are **additive** (new optional
fields only) so the deployed frontend contract is unbroken; the app still starts
when the optional `prometheus_client`/`anthropic` packages are absent.

**2.1 threshold in `/predict`**: `PredictResponse` gains `threshold_used` and
`recommendation` (`"decline"` if `probability >= champion.threshold` else
`"approve"` — decision-support only; the human analyst decides). Applied to both
`/api/v1/predict` and `/api/v1/predict/batch`.

**2.2 reason codes in `/explain`**: `ExplainResponse` gains `reason_codes` and
`disclaimer`, populated via `src.ml.reason_codes.build_explanation_payload`.
`top_factors` is unchanged.

**2.3 credit-memo endpoint** (`routers/llm.py`): `POST
/api/v1/llm-reports/credit-memo` scores an applicant and returns a grounded memo
via `src.llm.generate_memo`. Uses `AnthropicProvider` when `ANTHROPIC_API_KEY` is
set, else the deterministic template fallback — so it works out of the box. Live
memos need the `anthropic` package + `ANTHROPIC_API_KEY` (not added to
requirements).

**2.4 `/metrics`** (`main.py`): Prometheus request middleware +
`GET /metrics` via `src.monitoring.prometheus_mw`, both wrapped so a missing
`prometheus_client` logs a warning and **never blocks startup** (`/metrics` then
returns 503). Added `prometheus-client>=0.20` to `services/ml/requirements.txt`.

**2.5 audit export** (`routers/audit.py`): `GET /api/v1/audit/events` gated to
`governance`/`compliance` (admin always allowed), reading recent `audit_logs`
via `src.db.get_service_client()`; `?format=csv` returns `text/csv`.

**2.6 governance-gated promote** (`routers/models.py`): `POST
/api/v1/models/{semver}/promote` gated to `governance`, calls
`src.db.promote_model(..., approved_by=principal.user_id)`; the data-layer
`ValueError` gate surfaces as a `400 promotion_rejected` envelope.

## Stage 7 — fairness mitigation + governance (2026-07-13)

**7.1 mitigation** (`src/ml/mitigation.py`): Kamiran–Calders `reweigh` sample
weights + `per_group_thresholds` (reuse the cost-sensitive `optimize_threshold`)
+ `disparity_ratio` and `evaluate_mitigation`, which compares a single global
threshold vs per-group thresholds on the four-fifths / 0.8 rule so governance can
read off the accuracy-vs-fairness trade-off. Implemented with numpy/sklearn;
`fairlearn` is the documented optional upgrade. Per-group thresholds are surfaced
as a **governance experiment**, not auto-applied (applying different cut-offs by a
protected attribute can itself be disparate treatment).

**7.2 governance**: promoting a model to `champion` now **requires a governance
approver** — `promote_model(semver, "champion", approved_by=...)` refuses the
promotion before any write when `approved_by` is missing, stamps the approver on
the row, and audit-logs it (`src/db/models_repo.py`). Auto-generated **model
cards** (`src/ml/model_card.py`) render identity, metrics, the decision-support
disclaimer, and the per-group fairness table (flagging groups under the 0.8 rule)
from the live registry + fairness results.

**7.3**: `docs/runbooks/recalibration.md` — the end-to-end procedure to recalibrate
on new portfolio data (ingest → temporal split → retrain/register → recalibrate →
fairness rerun → governance-approved promotion), keeping the champion untouched
until sign-off.

## Stage 5 — monitoring + grounded LLM memos (2026-07-13)

Added `src/monitoring/` and `src/llm/` — all optional dependencies
(evidently, prometheus_client, anthropic, openai) lazy-imported so every module
imports and every test runs in the base environment. **5.1** `drift.py`:
PSI (quantile bins, warn 0.1 / alert 0.2) + two-sample KS per feature;
`record_drift` persists `drift_psi.<feature>` monitoring_metrics rows and a
`drift_alert` audit_logs row per non-ok feature. **5.2** `quality.py`:
null-rate and out-of-contract-rate per feature against
`src.ml.feature_contract` (thresholds 5%), persisted as `dq_null_rate.<f>` /
`dq_ooc_rate.<f>` plus `dq_alert` audit rows. **5.3** `prometheus_mw.py`:
pure-ASGI middleware factory (no FastAPI import) recording
`http_requests_total` + `http_request_duration_seconds`, and a
`metrics_endpoint()` exposition helper; without prometheus_client both raise a
RuntimeError naming `infra/requirements-monitoring.txt`. New `infra/` carries
the optional monitoring requirements, a Grafana dashboard (request rate, p95
latency, `drift_psi.<feature>` panel over monitoring_metrics) and wiring docs.
**5.4** `src/llm/`: `provider.py` (LLMProvider ABC; Anthropic `claude-sonnet-5`
/ OpenAI `gpt-4o`, SDKs in the new root `requirements-llm.txt`, keys read at
call time) and `memo.py`, the grounded memo layer — whitelist-only
`build_memo_inputs`, PII redaction (`name/email/phone/address/dob/national_id`
stripped pre-call), prompt built solely from the structured inputs with reason
codes from `src.ml.reason_codes`, and `validate_grounding` — a LAYERED
HEURISTIC defense (invented-number + feature-name incl. camelCase +
decision-directive/review-countermanding checks), NOT a factual-correctness
guarantee: it flags fabricated numbers, invented feature names and
"recommend/approve/decline/waive/override/skip-review/guarantee"-style
language (`GroundingError`), but cannot verify fluent digit-free prose. The
AUTHORITATIVE control is that every memo persists with `review_status='draft'`
behind mandatory human review before any external use. A deterministic
template fallback covers provider=None, provider failure, and empty/non-string
provider output (never raises for provider failures, never persists a
contentless memo); PII redaction recurses into nested dicts. Every memo carries
a mandatory contribution-disclaimer + "Decision-support
only; human review required." footer (guard-tested), and `persist_memo`
writing the exact `llm_reports` columns with `review_status='draft'` gating
external use pending human review. Covered by 41 offline tests
(tests/monitoring 24, tests/llm 17) — no network, no optional libs.

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
`import src.data` stays cheap. Documented in `docs/data_sources.md`. Real-data
robustness: ABS composes `indicator` from MEASURE plus every dimension column so
multi-dimensional SDMX series don't collide on the `macro_indicators` PK; macro
value parsing tolerates thousands separators and skips non-numeric/descriptive
cells; the HMDA loader survives NA `action_taken` rows. Covered by 33 offline
tests (committed fixtures + fake `src.db` client, no network/DB).

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

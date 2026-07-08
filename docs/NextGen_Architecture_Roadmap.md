# Next-Generation Explainable AI Credit Risk Platform: Architecture, Roadmap, and Product Expansion Plan

**Project:** `credit_risk_scoring_simulator`
**Document type:** Architecture & roadmap (planning only — no code changes)
**Status of current system:** Portfolio-grade Streamlit MVP, complete and deployed
**Author role:** Senior AI/ML engineer · fintech product architect · data scientist · dashboard UX/UI lead
**Grounded in commit:** `3e78e4b` (verified against the live repository)

> **How to read this document.** It is deliberately incremental. The current MVP is a *foundation to build on*, not something to discard. Every recommendation is tagged to a **phase** so the team can stop at any phase and still have a coherent, working product. Nothing here should be implemented all at once.

---

## 1. Executive Summary

The repository today is a **working, honest, explainable credit-risk MVP**: a synthetic UCI-structured dataset, a Logistic-Regression baseline and a CV-tuned XGBoost model (test AUC **0.793**, target ≥ 0.75 met), SHAP explanations, a real fairness audit, auto-generated business/fairness reports, and a four-tab Streamlit dashboard that self-bootstraps on first run. It stores everything on the local filesystem (`data/raw/*.csv`, `models/model.pkl`, `models/metrics.json`).

That is exactly the right scope for a portfolio artifact — but it is not a platform. To become a **serious corporate fintech credit-risk decision-support platform**, the project needs, in priority order: (1) a **service boundary** that separates ML logic from the UI, (2) a **prediction API** with authentication and audit logging, (3) an **operational database** so every prediction, explanation, and human decision is persisted and traceable, (4) **monitoring** for drift, performance, and fairness over time, (5) **governed ML lifecycle** (registry, calibration, cost-sensitive thresholds), and (6) an optional **LLM credit-memo layer** that is tightly grounded in structured model outputs.

The guiding principle throughout: **this remains a decision-support system, never an autonomous lending-approval engine.** Predictions, explanations, decision *recommendations*, and final *human decisions* are kept as four distinct, separately-stored concepts.

The evolution preserves the current strengths verbatim: the ML pipeline in `src/train_model.py`, the SHAP layer in `src/explain.py`, the fairness audit in `src/fairness.py`, the reports in `src/generate_reports.py`, and the Streamlit demo become the *internal analytics prototype* while a production React/FastAPI stack grows alongside them.

---

## 2. Current Repository Assessment

### 2.1 Current architecture (verified)

A single Python package `src/` with a filesystem-based data/model store and a Streamlit front end. There is **no service boundary** — the dashboard imports the ML modules directly and calls `model.predict_proba()` in-process.

```
generate_data.py → data/raw/credit_card_default.csv
      → preprocessing.py (clean + engineer + split)
      → train_model.py → models/model.pkl (bundle) + models/metrics.json
      → dashboard.py (loads bundle, calls explain.py + fairness.py in-process)
      → generate_reports.py → reports/*.md, *.pdf, figures/
```

### 2.2 Existing ML pipeline (verified against `src/train_model.py`)

- **Baseline:** `train_baseline()` — `Pipeline(StandardScaler → LogisticRegression(class_weight='balanced', max_iter=1000))`.
- **Advanced:** `train_advanced()` — `GridSearchCV(cv=3, scoring='roc_auc')` over a small XGBoost grid, with `scale_pos_weight` for imbalance and an automatic **RandomForest fallback** if xgboost is unavailable. Fitted model is tagged with `model_type_`, `cv_best_auc_`, `cv_best_params_`.
- **Evaluation:** `evaluate_model()` returns `auc_roc, precision, recall, f1, accuracy, confusion_matrix`.
- **Persistence:** `save_model()` uses `joblib`; `run_training()` writes a **bundle dict** `{model, baseline, features, model_type}` to `model.pkl` and a metrics JSON.
- **Current results (test set, n=6000):** AUC 0.793 (baseline 0.791), precision 0.442, recall 0.714, F1 0.546, accuracy 0.717; confusion matrix `TN 3280 / FP 1289 / FN 410 / TP 1021`; default rate 23.9%; 28 features (23 raw + 5 engineered).

### 2.3 Existing dashboard capabilities (verified against `src/dashboard.py`)

Four tabs: **Single Customer Prediction** (input form → 0–100 score + gauge + SHAP bar + plain-language sentences), **Model Performance** (AUC/precision/recall/F1, ROC curve, confusion heatmap, feature importance), **Segment Analysis** (risk distribution by sex/education/age), **Limitations & Disclaimer** (disclaimers + live fairness table). Uses `@st.cache_resource`/`@st.cache_data`; `main()` **self-bootstraps** (runs `run_training()` in-process if `model.pkl` is missing).

### 2.4 Existing explainability & fairness (verified)

- `src/explain.py`: `get_shap_values()` (`shap.TreeExplainer`), `explain_single_customer()` (top-5 by absolute contribution), `explain_in_plain_language()` (friendly names + sentences), `risk_score()`.
- `src/fairness.py`: `run_fairness_audit()` (per-group n, actual default rate, selection rate, recall, precision across sex/education/age-group) and `disparity_summary()` (min/max ratios). **Current finding:** age-group selection-rate ratio **0.599** (below the 0.8 "80% rule" → flagged), education 0.812, sex 0.950.

### 2.5 Current limitations

Filesystem-only storage; no API; no database; no auth; no model registry; no monitoring; no real-time ingestion; no LLM layer; synthetic data only; single-process coupling of UI and ML; threshold fixed at 0.5; no calibration; no label-maturity tracking (predictions are never compared to realised outcomes over time).

### 2.6 What to **preserve**

The ML pipeline, SHAP layer, fairness audit, report generators, the honest metrics/limitations posture, the test suite (`tests/`), and the Streamlit app **as an internal prototype**. These are genuine strengths and become reusable services.

### 2.7 What to **extend or replace**

| Preserve as-is | Extend | Replace for production |
|---|---|---|
| `explain.py`, `fairness.py`, report generators, tests | `train_model.py` → governed lifecycle (registry, calibration, thresholds) | Filesystem CSV/pkl store → PostgreSQL + object storage |
| Streamlit as internal prototype | `config.py` → typed settings (pydantic-settings) | In-process prediction → FastAPI service |
| Synthetic generator (as a test/demo fixture) | Fairness → ongoing monitoring, not one-shot | No-auth access → OAuth2/OIDC + RBAC |

---

## 3. Target Product Vision

A **production-style credit-risk decision-support system** that scores applications, explains each score, recommends (not decides) an action, and records the human's final decision with full auditability. Primary users and their core jobs:

| User | Primary job in the platform |
|---|---|
| **Credit risk analyst** | Assess a single applicant; read reason codes; recommend/override. |
| **Credit manager** | Monitor portfolio risk, approval-rate trends, team override rates. |
| **Model risk / governance** | Review model cards, performance-over-time, challenger/champion, approvals. |
| **Compliance / fair-lending** | Review fairness runs, adverse-action reasoning, audit trail. |
| **Executives** | Portfolio risk overview, exposure, trend, and threshold posture. |

**Non-negotiable product boundary:** the platform outputs a **decision recommendation** plus explanation; a **human** makes and records the final decision. No endpoint auto-approves or auto-declines credit.

---

## 4. Recommended Future Tech Stack

| Layer | Recommendation | Phase | Notes |
|---|---|---|---|
| Internal analytics UI | **Keep Streamlit** (current app) | 0–1 | Becomes the internal prototype/analyst sandbox. |
| Production frontend | **React / Next.js** | 4 | Corporate UX; consumes the API only. |
| API | **FastAPI** (+ Uvicorn/Gunicorn) | 2 | Wraps existing ML modules; versioned. |
| Operational DB | **PostgreSQL** | 3 | Serving + governance + audit. |
| Analytics warehouse | **BigQuery / Snowflake** (optional) | 7 | For historical analytics at scale; not required early. |
| Cache / queue | **Redis** + **Celery/RQ** | 5 | Batch scoring, report generation, async jobs. |
| ML lifecycle | **MLflow** model registry | 6 | Champion/challenger, versions, stages. |
| Monitoring | **Evidently AI** (drift/quality) + **Prometheus/Grafana** (infra) | 5 | Split ML-monitoring from infra-monitoring. |
| Auth | **OAuth2 / OIDC / SSO** (Auth0, Okta, Azure AD, or Cognito) | 2–3 | Provider-agnostic; RBAC on top. |
| LLM layer | **Provider-agnostic** abstraction over Claude / OpenAI | 6 | Grounded, audited, with template fallback. |
| Object storage | **S3 / GCS / Azure Blob** | 6–7 | Model artifacts, PDFs, LLM outputs. |
| Deploy | **Docker** + managed Postgres + **CI/CD** (GitHub Actions) + IaC (Terraform) | 2→8 | Incremental; containerise the API first. |

**Anti-overengineering rule:** Phases 0–3 need only FastAPI + PostgreSQL + Docker + the existing libraries. Warehouse, Celery, MLflow, and LLM come later and only if the earlier phases prove the need.

---

## 5. Real Data Strategy and External Connectors

The synthetic UCI-style generator (`generate_data.py`) stays as a **deterministic demo/test fixture**. Production requires real data, introduced behind connector interfaces so the ML code never hard-codes a source.

| Source | Use | Access/legal reality |
|---|---|---|
| **UCI Default of Credit Card Clients** | Public academic baseline | Free for academic/portfolio; cite. Already the schema basis. |
| **HMDA / FFIEC** (US mortgage) | Fair-lending, approval/denial, demographics, DTI/LTV, pricing, geography | Public; US-context; useful for fairness methodology, not AU calibration. |
| **Freddie Mac Single-Family Loan-Level** | Mortgage default/prepayment performance modelling | **Registration + license terms required** — verify before use. |
| **RBA statistical tables** | AU macro / payment / credit context | Public; macro features, not borrower-level. |
| **ABS API** | AU labour, income, demographic, regional indicators | Public API; macro/segment features. |
| **APRA ADI statistics** | AU banking/credit-system context | Public; portfolio context. |
| **Credit bureau APIs** (Equifax, Experian, illion) | Real production borrower data | **Commercial contract + legal + compliance approval required.** Future only. |
| **Internal bank/fintech data** | Applications, repayments, transactions, collections, arrears, limits, affordability, hardship | Requires data-governance, consent, and privacy controls. |

> **Hard requirement:** No real dataset — public or commercial — is ingested until **license, privacy, and usage-rights have been explicitly verified and documented.** Web/legal/commercial review is required for Freddie Mac and all bureau sources; treat this as a gate, not a formality.

**Connector design:** define a `DataSource` interface in `src/data/` with implementations `SyntheticSource` (today), `CsvSource`, `PostgresSource`, and later `BureauSource`. The ML pipeline depends on the interface, not the implementation.

---

## 6. Production Database Design (PostgreSQL)

Design goals: separate **operational serving**, **analytics**, **governance**, and **audit**; isolate PII; make every prediction and decision reconstructible. Use **Alembic** for migrations from day one of Phase 3. `JSONB` is used where the shape is model/version-dependent (feature payloads, SHAP outputs, LLM inputs).

**Legend — Category:** `OP` operational serving · `AN` analytics · `GOV` governance · `AUD` audit.

### 6.1 Identity, access, PII

| Table | Cat | PK | Key FKs | Important columns | JSONB? | Retention / privacy |
|---|---|---|---|---|---|---|
| `users` | OP | `user_id UUID` | — | `email` (unique), `full_name`, `status`, `created_at` | no | PII; access-controlled. |
| `roles` | GOV | `role_id` | — | `name` (analyst/manager/governance/compliance/exec/admin), `permissions JSONB` | yes (perms) | Low sensitivity. |
| `user_roles` | GOV | `(user_id, role_id)` | `users`, `roles` | `granted_by`, `granted_at` | no | Access reviews. |
| `api_keys` | OP | `api_key_id` | `users` | `key_hash` (never plaintext), `scopes JSONB`, `expires_at`, `revoked_at` | yes | Store **hash only**; rotate. |
| `customers` | OP | `customer_id UUID` | — | `created_at`, `status`, **non-PII** attributes only | no | Links to PII via identifiers table. |
| `customer_identifiers` | OP | `identifier_id` | `customers` | `id_type`, `id_value_encrypted`, `hash` | no | **PII vault**; encrypted at rest; strict RLS. |

### 6.2 Application & feature data (serving)

| Table | Cat | PK | Key FKs | Important columns | JSONB? | Notes |
|---|---|---|---|---|---|---|
| `credit_applications` | OP | `application_id UUID` | `customers` | `submitted_at`, `product_type`, `amount`, `term`, `channel`, `status` | no | One row per application. |
| `application_features` | OP | `feature_set_id` | `credit_applications` | `feature_schema_version`, `features JSONB`, `computed_at` | **yes** | The 28-feature vector today; schema-versioned. |
| `bureau_reports` | OP | `bureau_report_id` | `customers` | `provider`, `pulled_at`, `score`, `raw JSONB`, `consent_ref` | yes | Future; consent-gated PII. |
| `transaction_summaries` | OP/AN | `txn_summary_id` | `customers` | `window`, `inflow`, `outflow`, `volatility`, `features JSONB` | yes | Open-banking derived. |
| `repayment_history` | OP/AN | `repayment_id` | `customers` | `period`, `due`, `paid`, `days_late`, `status` | no | Maturing labels live here. |
| `macro_indicators` | AN | `(source, indicator, period)` | — | `value`, `source` (RBA/ABS/APRA), `ingested_at` | no | Borrower-agnostic context. |

### 6.3 Model registry & lifecycle (governance)

| Table | Cat | PK | Key FKs | Important columns | JSONB? | Notes |
|---|---|---|---|---|---|---|
| `model_registry` | GOV | `model_id` | — | `name`, `problem_type`, `owner`, `created_at` | no | Logical model (e.g. "pd_scorecard"). |
| `model_versions` | GOV | `model_version_id` | `model_registry` | `semver`, `algo` (logreg/xgboost), `stage` (dev/staging/champion/challenger/retired), `artifact_uri`, `training_data_ref`, `metrics JSONB`, `model_card_uri`, `approved_by` | yes | Mirrors today's `bundle['model_type']` + metrics. |
| `model_features` | GOV | `(model_version_id, feature_name)` | `model_versions` | `dtype`, `source`, `importance`, `required BOOL` | no | The feature contract (today's `features` list). |

### 6.4 Predictions, explanations, decisions (serving + governance)

| Table | Cat | PK | Key FKs | Important columns | JSONB? | Notes |
|---|---|---|---|---|---|---|
| `predictions` | OP | `prediction_id UUID` | `credit_applications`, `model_versions` | `probability`, `risk_score` (0–100), `risk_band`, `threshold_used`, `input_hash`, `latency_ms`, `created_at`, `created_by` | no | **Immutable**; input_hash for idempotency/reproducibility. |
| `prediction_explanations` | OP | `explanation_id UUID` | `predictions` | `method` ('shap_tree'), `top_factors JSONB`, `base_value`, `full_contributions JSONB` | **yes** | Output of `explain.py`. |
| `decision_recommendations` | GOV | `recommendation_id` | `predictions` | `recommended_action` (approve/refer/decline), `rationale`, `policy_version` | no | System suggestion — **not** the decision. |
| `human_decisions` | GOV | `decision_id UUID` | `credit_applications`, `predictions`, `users` | `final_action`, `decided_at`, `decided_by`, `notes` | no | The authoritative decision. |
| `override_logs` | AUD | `override_id` | `human_decisions`, `decision_recommendations` | `overrode BOOL`, `reason_code`, `justification`, `created_at` | no | Governance metric (override rate). |
| `llm_explanation_reports` | GOV | `llm_report_id UUID` | `predictions`, `users` | `provider`, `model_name`, `prompt JSONB`, `structured_inputs JSONB`, `output_text`, `source_fields JSONB`, `model_version_ref`, `redacted BOOL`, `created_at`, `created_by` | **yes** | Full grounding + provenance (see §11). |

### 6.5 Monitoring & quality (analytics + governance)

| Table | Cat | PK | Important columns | JSONB? | Notes |
|---|---|---|---|---|---|
| `fairness_audit_runs` | GOV | `fairness_run_id` | `model_version_id`, `dataset_ref`, `run_at`, `protected_attrs JSONB` | yes | One run of `run_fairness_audit()`. |
| `fairness_audit_results` | GOV | `(fairness_run_id, attribute, group)` | `n`, `actual_default_rate`, `selection_rate`, `recall`, `precision`, `disparity_ratio` | no | Today's per-group table, persisted. |
| `performance_metrics` | AN | `metric_id` | `model_version_id`, `period`, `auc`, `ks`, `gini`, `precision`, `recall`, `brier` | no | Time series once labels mature. |
| `drift_metrics` | AN | `drift_id` | `model_version_id`, `feature_name`, `period`, `psi`, `method`, `severity` | no | Feature/prediction drift + PSI. |
| `monitoring_events` | AUD | `event_id` | `type`, `severity`, `payload JSONB`, `created_at`, `resolved_at` | yes | Alerts/escalations. |
| `data_quality_checks` | AN | `dq_check_id` | `dataset_ref`, `check_name`, `passed BOOL`, `details JSONB`, `run_at` | yes | Missing-feature rate, ranges, schema. |

### 6.6 Audit

| Table | Cat | PK | Important columns | JSONB? | Notes |
|---|---|---|---|---|---|
| `audit_logs` | AUD | `audit_id UUID` | `actor_id`, `actor_type`, `action`, `entity_type`, `entity_id`, `before JSONB`, `after JSONB`, `ip`, `created_at` | **yes** | Append-only; **no PII values**, reference by id. |

### 6.7 Cross-cutting

- **Indexing:** btree on all FKs; `predictions(application_id, created_at)`, `predictions(model_version_id)`, `predictions(input_hash)`; GIN on hot `JSONB` (`application_features.features`, `prediction_explanations.top_factors`); partial index on `model_versions(stage) WHERE stage IN ('champion','challenger')`; time-partition `predictions`, `performance_metrics`, `audit_logs` by month.
- **PII separation:** all direct identifiers live only in `customer_identifiers` (encrypted); everything else references `customer_id` (a surrogate UUID). Feature/prediction/monitoring tables carry **no** raw PII.
- **Row-level security (RLS):** Postgres RLS policies keyed on role — compliance sees fairness/audit; analysts see their queue; PII vault access is separately gated and logged.
- **Auditability:** `audit_logs` and `override_logs` are append-only (revoke UPDATE/DELETE); prediction rows immutable.
- **Retention/privacy:** define per-table retention (e.g. raw bureau payloads shortest; audit longest); support subject-access/erasure by pseudonymisation of `customer_identifiers` while preserving non-PII analytics.
- **Migrations:** Alembic, one revision per schema change, reviewed like code; never edit a shipped migration.

---

## 7. Production API Architecture (FastAPI)

A versioned FastAPI service that **wraps the existing ML modules** — the first implementation calls `explain.py`, `fairness.py`, and the loaded `bundle` directly, so no ML logic is rewritten.

### 7.1 Endpoints

| Method & path | Purpose | Auth/role |
|---|---|---|
| `GET /health` | Liveness | public |
| `GET /ready` | Readiness (model + DB loaded) | public |
| `POST /api/v1/predict` | Score one application | service/analyst |
| `POST /api/v1/predict/batch` | Score many (idempotency key) | service |
| `POST /api/v1/explain` | SHAP top factors for an input/prediction | analyst |
| `GET /api/v1/customers/{customer_id}/risk-profile` | Latest scores/decisions | analyst/manager |
| `GET /api/v1/predictions/{prediction_id}` | Retrieve stored prediction + explanation | analyst |
| `GET /api/v1/models/current` | Champion model + metadata | any authed |
| `GET /api/v1/models/{model_version}` | Specific version card/metrics | governance |
| `POST /api/v1/llm-reports/credit-memo` | Generate grounded LLM memo | analyst (human-review gate) |
| `GET /api/v1/monitoring/performance` | Performance time series | manager/governance |
| `GET /api/v1/monitoring/drift` | Drift/PSI | governance |
| `GET /api/v1/fairness/latest` | Latest fairness run | compliance |
| `GET /api/v1/audit/events` | Audit trail (filtered) | governance/compliance |

### 7.2 Cross-cutting API concerns

- **Auth:** OAuth2/OIDC bearer **JWT** for users; hashed **API keys** for services; RBAC dependency per route.
- **Schemas:** Pydantic v2 request/response models; `PredictRequest` validates the 28-feature contract (or raw fields → server-side `engineer_features`), ranges (age>0, limit≥0), and enum codes.
- **Error format:** consistent envelope `{error: {code, message, request_id, details?}}`; never leak stack traces or PII.
- **Logging:** structured logs with `request_id`; **PII-redacting** middleware; log input **hashes**, not values.
- **Rate limiting:** per-key/token (Redis token bucket).
- **Versioning:** URI-versioned (`/api/v1`); additive changes only within a version.
- **Model pinning:** requests may pin `model_version`; default = champion; response always echoes the version used.
- **Idempotency:** `Idempotency-Key` header on batch scoring; `input_hash` dedupes single predictions.
- **Separation of concerns:** `predict` → probability/score; `explain` → SHAP; `decision_recommendations` → suggested action; `human_decisions` → the actual decision. Four endpoints/tables, never conflated.

---

## 8. ML and Explainable AI Roadmap

Evolve `train_model.py` from a local script into a **governed lifecycle** while keeping its current functions as the engine.

- **Dataset & feature versioning:** every training run records a dataset ref + `feature_schema_version` (persist to `model_versions`).
- **Feature schema validation:** a `FeatureContract` (great_expectations or pydantic) validates types/ranges before train and before every predict; today's implicit 28-column contract becomes explicit.
- **Split discipline:** keep the stratified split; add a **temporal** holdout once real dated data exists (train on past, test on future).
- **Models:** retain **Logistic Regression as the explainability benchmark**; add **XGBoost/LightGBM/CatBoost** as candidates via the existing `GridSearchCV` pattern.
- **Calibration:** wrap the classifier in `CalibratedClassifierCV` (Platt/isotonic) so `risk_score` reflects true probability — essential once scores drive decisions.
- **Cost-sensitive thresholds:** replace the fixed 0.5 with a threshold chosen from an FN:FP cost ratio (the current confusion matrix already exposes FN 410 vs FP 1289 — the machinery to reason about this exists).
- **Reject inference:** document the bias from training only on booked accounts; note methods (augmentation, parcelling) as future work — do not silently ignore.
- **Stability & bias monitoring:** PSI on features/scores; scheduled fairness runs (§6.5) rather than one-shot.
- **Model cards:** generate a card per `model_versions` row (intended use, data, metrics, fairness, limitations).
- **Explanations:** keep SHAP global + local; add **reason codes** (analyst-friendly mappings of `top_factors`); **counterfactual** explanations as future work.

> **Explainability boundary (must appear in UI and reports):** SHAP is **feature-contribution analysis**, *not* causal proof. The platform must never state or imply that a SHAP value means a feature *caused* default. Language is "contributed to the score", never "caused".

---

## 9. Real-Time Performance Monitoring Dashboard

Track operational and model health, clearly separating **real-time** signals from **label-delayed** ones.

**Real-time (available at scoring time):** prediction volume; recommendation approve/refer/decline rate; average predicted PD; risk-band distribution; latency p50/p95/p99; API error rate; data-quality failures; missing-feature rate; feature drift & prediction drift (PSI); LLM report usage/failure rate; override rate.

**Label-delayed (require outcome maturation):** actual default rate; AUC/KS/Gini over time; calibration curve; Population Stability Index of realised outcomes; fairness metrics recomputed on realised defaults.

> **Why the split matters (state it in the UI):** a default label only materialises after the customer's next payment cycle(s). Performance and calibration panels must show an explicit **"awaiting label maturity"** state and a data-as-of date, or they will mislead. Drift and volume can be near-real-time; realised-performance cannot.

---

## 10. Corporate Fintech Dashboard UX/UI Requirements

The production frontend (React/Next.js, Phase 4) — desktop-first, dense but legible.

**Pages:** Executive Overview · Single Applicant Risk Assessment · Portfolio Risk Monitor · Model Performance · Explainability Center · Fairness & Responsible AI · Data Quality Monitor · API & System Health · Model Governance · LLM Credit Memo Generator · Audit Trail · Settings / Access Control.

**UX/UI principles:**
- Clean corporate fintech aesthetic; no toy colours, no decorative charts without decision value.
- **Accessible, consistent risk colours** (the current Low/Medium/High green/amber/red, WCAG-checked, never colour-only — pair with labels).
- Every metric shows **value + trend + threshold/context**; no bare numbers.
- **Prediction and decision are visually separated**; the model output panel shows confidence/caveats/model version; the decision panel is a distinct human action.
- Every view has explicit **empty / loading / error** states.
- **Exportable** analyst/manager reports (PDF/CSV) reusing `generate_reports.py`.
- Responsive desktop-first layout (≥1280px primary; graceful ≥768px).
- Show **model version, data-as-of, and "decision-support only" disclaimer** on every scoring surface.

---

## 11. LLM-Generated Credit Explanation Reports

A **provider-agnostic** LLM layer (Claude and/or OpenAI) that turns structured model outputs into readable credit memos — grounded, audited, never free-associating.

**The memo contains:** credit-risk summary · main risk drivers · mitigating factors · data-quality caveats · fairness/compliance caution · analyst-facing recommendation language · plain-English explanation · suggested follow-up questions/documents · a **"do not use as the sole basis for a lending decision"** disclaimer.

**Hard constraints:**
- The LLM receives **only** structured inputs: model outputs (score/band/probability), SHAP `top_factors`, approved application/customer fields, and approved policy text. **No open-ended browsing, no invented facts.**
- Every memo embeds **source fields + model version**; unsupported claims are prohibited by prompt design and post-generation validation.
- Persist **prompt, structured inputs, output, provider, model name, timestamp, user id** in `llm_explanation_reports`.
- **PII redaction** before the call; store `redacted` flag.
- **Template fallback:** if the LLM API is unavailable, emit a deterministic template memo from the same structured inputs (reuse the plain-language layer in `explain.py`).
- **Human review** is mandatory before any memo is used externally; store reviewer + status.

---

## 12. Governance, Compliance, and Responsible AI

- **Model risk management:** champion/challenger, documented approvals (`model_versions.approved_by`), model cards, periodic validation.
- **Audit logging:** append-only `audit_logs`; every prediction, override, and access recorded.
- **Human-in-the-loop:** recommendations never auto-execute; `human_decisions` is authoritative.
- **Fairness testing:** scheduled runs + thresholds + escalation when disparity ratio < 0.8.
- **Explainability boundaries:** SHAP = contribution, not causation (repeated in UI/reports).
- **Data privacy & PII minimisation:** PII vault, encryption, RLS, retention, subject-access/erasure support.
- **Security:** secret management, hashed keys, least privilege, dependency scanning.
- **Access reviews:** periodic `user_roles` review; revoke stale access.
- **Model approval workflow:** dev → staging → (governance sign-off) → champion.
- **Monitoring escalation:** `monitoring_events` severity → alert → owner → resolution SLA.
- **Documentation:** model cards, data lineage, decision logs, validation reports.

> **Regulatory context (informational, not legal advice):** for a US context, adverse-action reasoning under **ECOA/FCRA**-style rules means reason codes must be accurate and non-misleading. For **Australia**, responsible-lending and anti-discrimination/fair-lending considerations apply. **Legal/compliance review is required before any real lending use — this document does not provide legal advice.**

---

## 13. Future Connectors / Productionisation

A professional restatement of the "future connectors" idea. **None of these exist in the current MVP, and that is correct for the current portfolio scope.** They are the right productionisation steps, introduced behind interfaces so the ML core is unchanged.

| Connector | Replaces / adds | Phase |
|---|---|---|
| **PostgreSQL / BigQuery** | Local CSV/pkl/JSON store | 3 / 7 |
| **Credit bureau API** (Equifax/Experian/illion) | External borrower data | 7 (legal-gated) |
| **Open-banking / transaction** connector | Affordability/behaviour features | 7 |
| **Internal loan-management** connector | Application/limit data | 7 |
| **Collections/arrears** connector | Hardship/arrears signals | 7 |
| **Macroeconomic** connector (RBA/ABS/APRA/FRED/World Bank) | Context features | 7 |
| **OAuth/SSO** provider | Authentication | 2–3 |
| **MLflow registry + feature store** | Model/feature governance | 6 |
| **Monitoring/alerting** platform | Drift/perf/infra observability | 5 |
| **Cloud object storage** | Artifacts, PDFs, LLM outputs | 6–7 |
| **CI/CD + IaC** | Repeatable deploys | 2→8 |
| **LLM provider abstraction** | Grounded memos | 6 |
| **Audit/compliance export** connector | Regulator/governance exports | 7 |

Each connector requires **license, privacy, and usage-rights verification** (§5) before enablement.

---

## 14. Limitations (professional restatement)

- Built on **synthetic data mirroring UCI Taiwan (2005)** — not real customers.
- **Not calibrated** to Australia or any live lending portfolio.
- **No** real bureau, transaction, open-banking, collections, hardship, or borrower-level macro data yet.
- Fairness audit is **detection-only**, not automated mitigation (current age-group disparity ratio 0.599 is disclosed, not corrected).
- Default threshold is **0.5**; it should be tuned to business loss economics (FN ≫ FP cost).
- **SHAP = model-contribution explanations, not causal proof.**
- LLM-generated explanations carry **hallucination risk** unless constrained, grounded, and audited (the §11 controls exist to manage this).
- The current **Streamlit app is portfolio-grade, not enterprise-grade**.
- **No** production auth, database, API, monitoring, or model registry yet.
- **No** legal/compliance validation for real lending use.
- **Not suitable for real credit decisions** without governance, validation, and human review.

---

## 15. Future Work

Validate on real local data · add bureau/open-banking/transaction/repayment features · add macro features (RBA/ABS/APRA/World Bank/FRED) · add production API (auth, logging, monitoring, versioning) · add Postgres operational DB + warehouse-ready schema · add real-time monitoring dashboard · add MLflow registry + feature store · run fairness-mitigation experiments · add cost-sensitive threshold optimisation · add score calibration · add champion/challenger framework · add guarded LLM credit memos · add analyst override workflow · add audit-ready governance exports · add cloud deployment with custom domain.

---

## 16. Phased Roadmap

Each phase is independently shippable and must **not break the working Streamlit app**.

### Phase 0 — Preserve & document
- **Objective:** freeze and document the current MVP as the baseline.
- **Scope:** architecture doc (this file), current-state diagram, tag a release.
- **Files:** docs only. **New:** `docs/` architecture notes. **Success:** MVP reproducible from a tagged commit; tests pass. **Validation:** `pytest` green. **Risks:** none.

### Phase 1 — Refactor for service boundaries (Streamlit stays)
- **Objective:** extract a clean ML service layer without behaviour change.
- **Scope:** introduce `src/ml/` (training/inference), `src/services/` (scoring/explanation facades) that wrap `train_model.py`/`explain.py`/`fairness.py`; make `dashboard.py` call the facades.
- **Affected:** `dashboard.py`, `config.py`. **New:** `src/services/scoring_service.py`, `src/ml/__init__.py`. **Success:** dashboard unchanged for users; facades unit-tested. **Validation:** existing 13 tests pass + new facade tests. **Risks:** import cycles — keep facades thin.

### Phase 2 — FastAPI prediction service
- **Objective:** expose predict/explain over HTTP with auth.
- **Scope:** `GET /health`, `/ready`, `POST /predict`, `/explain`, `GET /models/current`; JWT/API-key auth; Pydantic schemas; Dockerfile.
- **Affected:** none of the ML core (wrapped). **New:** `api/` (FastAPI app, routers, schemas, deps). **Success:** authed `/predict` returns score + model version + explanation id; unauthorised rejected. **Validation:** API tests (TestClient), schema tests. **Risks:** model-load cold start — load once at startup.

### Phase 3 — PostgreSQL + schemas
- **Objective:** persist predictions/explanations/decisions/audit.
- **Scope:** tables from §6 (start with `predictions`, `prediction_explanations`, `model_versions`, `human_decisions`, `audit_logs`); Alembic; repository layer.
- **New:** `src/db/`, `migrations/`. **Success:** every prediction stored with `input_hash`, model version, timestamp, actor; audit rows written. **Validation:** DB persistence tests (test container). **Risks:** PII leakage — enforce vault/RLS from the first migration.

### Phase 4 — Production dashboard redesign
- **Objective:** React/Next.js UI consuming the API.
- **Scope:** Executive, Single Applicant, Portfolio, Model Performance, Explainability, Fairness pages.
- **New:** `frontend/`. **Success:** feature parity with Streamlit tabs + prediction/decision separation; empty/loading/error states. **Validation:** component + e2e smoke tests. **Risks:** scope creep — ship pages incrementally; Streamlit remains the fallback.

### Phase 5 — Monitoring & drift
- **Objective:** track latency, errors, drift, data quality, fairness over time.
- **Scope:** Evidently jobs + Prometheus/Grafana; `drift_metrics`, `performance_metrics`, `data_quality_checks`, `monitoring_events`; Redis/Celery for scheduled jobs.
- **New:** `src/monitoring/`. **Success:** dashboards show drift/latency/DQ; alerts fire on thresholds. **Validation:** synthetic-drift test triggers an alert. **Risks:** label-maturity confusion — label-delayed panels clearly marked.

### Phase 6 — LLM report generation
- **Objective:** grounded credit memos with fallback.
- **Scope:** `POST /llm-reports/credit-memo`; provider abstraction; `llm_explanation_reports`; template fallback; human-review gate.
- **New:** `src/llm/`. **Success:** memos cite source fields + model version; PII redacted; fallback works offline. **Validation:** grounding tests (no field outside inputs), fallback test. **Risks:** hallucination — enforce structured-input-only + post-validation.

### Phase 7 — Real data connectors & governance
- **Objective:** ingest real/semi-real sources behind connectors; governance exports.
- **Scope:** `DataSource` implementations; macro connectors; fairness scheduling; model-approval workflow; compliance exports.
- **New:** `src/data/connectors/`. **Success:** at least one real public source (e.g. macro) ingested **after license verification**; governance export produced. **Validation:** connector contract tests. **Risks:** legal — no source enabled without documented rights.

### Phase 8 — Cloud deploy + custom domain
- **Objective:** production hosting.
- **Scope:** containerised API + frontend, managed Postgres, object storage, CI/CD, IaC, custom domain, TLS.
- **New:** `infra/`. **Success:** public authed platform on a custom domain; blue/green deploy. **Validation:** smoke tests post-deploy; rollback rehearsed. **Risks:** cost/secrets — IaC + secret manager.

---

## 17. Suggested Repository Structure (target)

> **Implement incrementally.** Do **not** create this all at once or move existing files prematurely — each folder appears only when its phase begins. The current `src/` keeps working throughout.

```
credit_risk_scoring_simulator/
├── app/                 # Streamlit internal prototype (today's dashboard.py moves here in P1+)
├── api/                 # FastAPI service (P2)
├── frontend/            # React/Next.js production UI (P4)
├── src/
│   ├── ml/              # training, inference, calibration, thresholds (from train_model.py)
│   ├── data/            # DataSource interface + connectors (synthetic/csv/postgres/bureau)
│   ├── db/              # SQLAlchemy models, repositories (P3)
│   ├── services/        # scoring/explanation/decision facades (P1)
│   ├── monitoring/      # drift, DQ, performance (P5)
│   ├── llm/             # provider abstraction + memo generation (P6)
│   ├── explain.py       # PRESERVED
│   ├── fairness.py      # PRESERVED
│   └── generate_reports.py  # PRESERVED
├── migrations/          # Alembic (P3)
├── infra/               # Docker, IaC, CI/CD (P2→P8)
├── docs/                # PRD, Technical_Spec, PROJECT_GUIDE, this roadmap
└── tests/               # existing + api/db/llm/monitoring tests
```

---

## 18. Acceptance Criteria

- `POST /api/v1/predict` returns a prediction **with model version and an explanation id**.
- Auth-protected endpoints **reject unauthorised** callers (401/403).
- Every prediction is stored with **input hash, model version, timestamp, and user/service id**.
- The dashboard shows **current and historical** model performance (with label-maturity states).
- Monitoring tracks **latency, drift, errors, and data quality**, with alerting.
- LLM reports are **grounded in structured model outputs**, carry provenance, and have a template fallback.
- **Existing tests continue to pass** (the current 13 remain green through every phase).
- **New tests** cover API endpoints, Pydantic schemas, DB persistence, and report generation.
- Documentation **clearly distinguishes MVP, internal prototype, and production-grade** capabilities.

---

## 19. Output & Delivery Notes

This is a planning document, not an implementation. It is specific to the current repository (functions, files, metrics, and fairness numbers are quoted from the actual code and reports at commit `3e78e4b`). Claims that depend on external factors — dataset licenses (Freddie Mac, bureaus), privacy/usage rights, and lending-law compliance — are explicitly flagged as requiring **web verification, license review, legal review, or business approval** before action.

**Preserved strengths carried through every phase:** the working ML pipeline (`train_model.py`), SHAP explanations (`explain.py`), the fairness audit (`fairness.py`), the report generators (`generate_reports.py`), and the Streamlit demo. **Nothing is rewritten wholesale**; the platform grows around the MVP.

*Companion documents: [`README.md`](../README.md) · [`PRD.md`](../PRD.md) · [`Technical_Spec.md`](../Technical_Spec.md) · [`docs/PROJECT_GUIDE.md`](PROJECT_GUIDE.md).*

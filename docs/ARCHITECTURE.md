# Credit Risk Scoring Simulator — Architecture

**Last updated:** 2026-07-12
**Status:** Single source of truth for architecture. Supersedes `NextGen_Architecture_Roadmap.md` (removed).
**Project:** `credit_risk_scoring_simulator` · Owner: Adam Pham (`phamhoangquynh21@gmail.com`)

This document describes the credit-risk platform **as it is actually built and running today**,
then the **forward architecture** the team is executing. Where an earlier planning document
(the NextGen roadmap) assumed a different stack, the live reality wins and the supersession is
noted briefly. The guiding product boundary is unchanged and non-negotiable: **this is a
decision-support system, never an autonomous lending-approval engine.** Predictions,
explanations, decision *recommendations*, and final *human decisions* are four distinct,
separately-stored concepts.

---

## 1. What this is

An Explainable-AI credit-risk platform (Finance × Data Science) that scores the probability a
credit-card customer defaults next month and explains *why*. It exists in two layers:

1. **The MVP** — a self-contained Python + Streamlit app (the original deliverable), now demoted
   to an internal analytics prototype.
2. **The production platform** — a multi-user web app: Next.js dashboard + FastAPI ML service +
   Supabase (Postgres, Auth, RLS). This is the current focus.

Data is **synthetic-but-realistic**, mirroring the UCI "Default of Credit Card Clients"
(Taiwan, 2005) schema; the platform also ingests the **real UCI file** (~30k rows). The trained
model reaches **AUC ≈ 0.78**.

---

## 2. Live deployment (authoritative)

| Component | Technology | Host | URL / identifier |
|---|---|---|---|
| Production dashboard | Next.js 16 (App Router, TypeScript, Tailwind) | **Vercel** | `credit-risk-scoring-simulator.vercel.app` |
| ML / API service | **FastAPI** (Uvicorn) | **Render** (free tier) | `credit-risk-ml-vmp3.onrender.com` |
| Database + Auth | **Supabase** (Postgres 17 + RLS + Supabase Auth) | Supabase (region `ap-southeast-2`) | project `uiormpweobimumzlxjml` |
| Streamlit MVP | Python + Streamlit | Streamlit Cloud | internal prototype/demo |

Operational notes: the Render free tier **sleeps after ~15 min idle** → first request incurs a
~30–50s cold start. The dashboard's public config (`NEXT_PUBLIC_*`) is baked into a committed
`frontend/.env.production` so the Vercel build is self-sufficient; a root `vercel.json` pins the
build to the Next app in `frontend/` (the repo root has `requirements.txt`, which otherwise makes
Vercel auto-detect Python).

---

## 3. System diagram

```
                                Browser
                                   │  HTTPS
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  Next.js 16 dashboard  (Vercel)               │
            │  App Router · TypeScript · Tailwind           │
            │  server route handlers + middleware auth gate │
            └───────┬───────────────────────────┬──────────┘
                    │                            │
   @supabase/ssr    │ RLS-governed reads         │ scoring: POST to own route
   (anon key +      │ (Sections 3 & 6 data)      │ handler, which forwards the
    user session)   ▼                            │ Supabase JWT
            ┌───────────────────────┐            ▼
            │  Supabase             │   ┌────────────────────────────────┐
            │  Postgres 17 + RLS    │◄──│  FastAPI ML service (Render)   │
            │  Supabase Auth (JWT)  │   │  re-verifies JWT · service-role │
            │  ~18 tables           │──►│  key · wraps the src/ ML core   │
            └───────────────────────┘   │  /predict /explain /batch ...  │
                    ▲ service-role key   └───────────────┬────────────────┘
                    │ (writes predictions/               │ in-process import
                    │  explanations)                     ▼
                    └──────────────────────  src/  Python ML pipeline
                                             (train_model · explain[SHAP] ·
                                              fairness · generate_reports)
```

**Trust boundary:** only `NEXT_PUBLIC_*` values (Supabase URL + anon key, public by design) reach
the browser. The **service-role key exists only on Render** and never in Vercel or the client.

---

## 4. Layers

### 4.1 Frontend — Next.js 16 on Vercel (`frontend/`)
- App Router, TypeScript, Tailwind. Route group `(app)` holds `assess`, `portfolio`,
  `performance`; plus `login` and `api/*` route handlers.
- Components: `Sidebar`, `DisclaimerBar`, `ApplicantForm`, `ScoreResult`, `MetricTile`, …
- `src/lib/`: Supabase clients (`@supabase/ssr`), ML proxy, formatting/nav/risk-band helpers.
- `src/middleware.ts`: auth gate, hardened with try/catch so a missing env or auth error can
  **never hard-500 the whole site**.
- **Data path:** for read data (portfolios, performance, fairness) the frontend reads Supabase
  directly with the anon key under the user's session — **RLS enforces per-user isolation**. For
  scoring it POSTs to its own route handlers, which **forward the Supabase JWT** to the ML service.
- Tests: 10 Vitest (helpers, Supabase clients, RBAC, schema mapping, a SHAP-factor regression).

### 4.2 ML / API service — FastAPI on Render (`services/ml/`)
This directory **is** the "api/" layer. There is **no separate `api/` package and no Alembic** in
the live system — the NextGen design's local-Postgres + Alembic + `api/` split was superseded by
Supabase + `services/ml/`.

- Structure: `main.py`, `settings.py`, `auth.py` (JWT + RBAC), `scoring.py`, `persistence.py`
  (service-role writes), `errors.py`, `logging_config.py`, `schemas.py`, `routers/{predict,explain,models}.py`.
- It **wraps the existing `src/` ML core in-process** — no ML logic is rewritten. It re-verifies
  the caller's Supabase JWT, scores, and persists predictions/explanations to Postgres via the
  service-role key.
- **Live endpoints (verified in code):**

| Method & path | Purpose |
|---|---|
| `GET /health` | Liveness → `{"status":"ok"}` |
| `GET /ready` | Readiness → `model_present:true` when the bundle is loaded |
| `POST /api/v1/predict` | Score one applicant |
| `POST /api/v1/predict/batch` | Score many; **idempotent** (idempotency key) |
| `POST /api/v1/explain` | SHAP top factors for an input/prediction |
| `GET /api/v1/models/current` | Champion model + metadata |

> `GET /api/v1/predictions/{id}` is described in the handoff as part of the intended surface but is
> **not currently registered** in `services/ml/routers/`. Today the frontend retrieves a stored
> prediction by reading Supabase directly under RLS, not via a dedicated ML endpoint.
> `TODO(verify)`: decide whether to add the `/predictions/{id}` route or keep retrieval on the
> Supabase read path.

### 4.3 Database + Auth — Supabase (managed Postgres 17)
- Schema lives in `supabase/migrations/` — **0001–0007 applied live**; ~18 tables. Migrations are
  applied via the Supabase MCP/dashboard (there is no Alembic).
- **Supabase Auth** issues the user JWT; **Row-Level Security** is enabled on every table with a
  default-deny posture; **RBAC** role is carried inline on `profiles.role`
  (`analyst | manager | compliance | executive | admin`).
- See §5 (data model) and §6 (security) for detail.

### 4.4 ML core — Python pipeline (`src/`)
The original, still-authoritative ML engine. **56 Python tests depend on it — do not break it.**
- `generate_data.py` → synthetic UCI-structured CSV; `preprocessing.py` (clean + engineer + split);
  `train_model.py` (LogisticRegression baseline + CV-tuned XGBoost, RandomForest fallback);
  `explain.py` (SHAP `TreeExplainer`, top-factor + plain-language layer); `fairness.py`
  (per-group audit + disparity summary); `dashboard.py` (Streamlit); `generate_reports.py`.
- Model: **AUC ≈ 0.78** on the real UCI "Default of Credit Card Clients" data; 28 features
  (23 raw + 5 engineered). `models/model.pkl` is committed so the Render image is self-contained
  (no training step at deploy).

### 4.5 Streamlit MVP (internal prototype)
The four-tab dashboard (Single Customer Prediction · Model Performance · Segment Analysis ·
Limitations & Disclaimer) that self-bootstraps training on first run. Retained as the internal
analyst sandbox on Streamlit Cloud; **not** the production surface.

---

## 5. Data model (live Supabase schema, ~18 tables)

Reconciled to `supabase/migrations/0001–0007`. This differs from the NextGen design, which won't
be maintained: the live schema **consolidated** NextGen's `customers` / `customer_identifiers` /
`credit_applications` / `application_features` into a portfolio model; folded
`performance_metrics` / `drift_metrics` / `data_quality_checks` / `monitoring_events` into one
`monitoring_metrics` time series; and carries the role inline on `profiles` rather than in
`roles` + `user_roles`. There is **no dedicated encrypted PII vault** because the data is synthetic
(no real borrower PII); when real bureau data is gated on later, a PII-isolation table returns
(see §8).

**Cluster legend:** OP operational · GOV governance · AUD audit · AN analytics.

### 5.1 Identity & access
| Table | Cat | Key columns | Notes |
|---|---|---|---|
| `profiles` | OP/GOV | `user_id` (PK→`auth.users`), `display_name`, `org`, `role` (enum), `is_demo` | Role is column-level-locked: users may update only `display_name`/`org`, never `role`. |
| `api_keys` | OP | `id`, `user_id`, `key_hash` (unique), `scopes JSONB`, `expires_at`, `revoked_at` | Hash only; client **write** policies were removed (0005) — issuance is a service-role flow. |

Supabase Auth's `auth.users` is the identity anchor; `profiles` is auto-created on signup via a
`handle_new_user()` trigger.

### 5.2 Portfolio & application data (serving)
| Table | Cat | Key columns | Notes |
|---|---|---|---|
| `portfolios` | OP | `id`, `owner_id`, `name`, `is_demo`, `row_count` | Batch-scoring unit. Demo portfolios are world-readable but only service-role-writable. |
| `portfolio_rows` | OP | `id`, `portfolio_id`, `row_index`, `features JSONB` | One applicant feature vector per row. |
| `upload_files` | OP | `id`, `portfolio_id`, `storage_path`, `original_name`, `size_bytes` | Uploaded CSV metadata. |

Single-applicant ("ad-hoc") scoring uses `predictions.portfolio_id = NULL` with the applicant
payload inline (see 5.4), so no portfolio row is required.

### 5.3 Model registry & lifecycle (governance)
| Table | Cat | Key columns | Notes |
|---|---|---|---|
| `model_versions` | GOV | `id`, `semver` (unique), `algo`, `stage` (`dev`/`staging`/`champion`/`retired`), `metrics JSONB`, `trained_on`, `threshold`, `approved_by` | The champion + its persisted decision `threshold`. Governance writes are service-role only in R1. |

### 5.4 Predictions, explanations, decisions (serving + governance)
| Table | Cat | Key columns | Notes |
|---|---|---|---|
| `predictions` | OP | `id`, `portfolio_id?`, `applicant JSONB`, `probability`, `risk_score`, `risk_band` (`Low`/`Medium`/`High`), `threshold_used`, `model_version_id`, `input_hash`, `latency_ms`, `created_by` | **Immutable** (UPDATE/DELETE revoked). `input_hash` for idempotency/reproducibility. |
| `prediction_explanations` | OP | `prediction_id` (PK), `method` (`shap_tree`), `top_factors JSONB`, `base_value` | Output of `explain.py`. |
| `decision_recommendations` | GOV | `prediction_id` (PK), `recommended_action` (`approve`/`refer`/`decline`), `rationale`, `policy_version` | System suggestion — **not** the decision. |
| `human_decisions` | GOV | `id`, `prediction_id`, `final_action`, `notes`, `decided_by` | The authoritative human decision. |
| `override_logs` | AUD | `id`, `decision_id`, `overrode`, `reason_code` | Override-rate governance metric; append-only. |
| `llm_reports` | GOV | `id`, `prediction_id?`, `provider`, `model_name`, `prompt JSONB`, `structured_inputs JSONB`, `output_text`, `source_fields JSONB`, `redacted`, `review_status` (`draft`/`reviewed`/`rejected`) | Full grounding + provenance for LLM memos (see §7, §8). Table exists; the generation endpoint is Stage-5 forward work. |

### 5.5 Monitoring, fairness & context (analytics + governance)
| Table | Cat | Key columns | Notes |
|---|---|---|---|
| `fairness_runs` | GOV | `id`, `model_version_id`, `run_at` | One execution of the fairness audit. |
| `fairness_results` | GOV | `(run_id, attribute, grp)` PK, `n`, `selection_rate`, `recall`, `precision`, `disparity_ratio` | Per-group results persisted. |
| `monitoring_metrics` | AN | `(period, metric)` PK, `value` | Single time-series table for latency/drift/DQ/performance (replaces four NextGen tables). |
| `macro_indicators` | AN | `(source, indicator, period)` PK, `value` | Borrower-agnostic AU macro context (RBA/ABS/APRA). |

### 5.6 Audit & config
| Table | Cat | Key columns | Notes |
|---|---|---|---|
| `audit_logs` | AUD | `id`, `actor_id`, `action`, `entity_type`, `entity_id`, `detail JSONB` | Append-only (UPDATE/DELETE revoked). `actor_id` retained even after user deletion. |
| `feature_flags` | GOV | `key` (PK), `enabled`, `note` | Gates connectors and optional features (see §8). |

---

## 6. Security model

- **Authentication:** Supabase Auth issues a JWT per user session. The frontend uses the anon key
  under that session; the ML service **re-verifies the JWT** before scoring and uses the
  service-role key only for privileged writes.
- **Row-Level Security:** enabled on all ~18 tables, default-deny. Representative policies:
  predictions readable by their creator or via an owned/demo portfolio; `human_decisions` and
  `override_logs` visible to `compliance`/`admin`; `audit_logs` to `compliance`/`admin`;
  `monitoring_metrics` to `manager`/`admin`; reference tables (`model_versions`, `macro_indicators`,
  `feature_flags`) world-readable; fairness tables authenticated-only (tightened in 0005).
- **RBAC:** role enum on `profiles.role`; `user_role()` is a `SECURITY DEFINER` helper used inside
  policies to avoid recursive RLS. Users cannot self-escalate: role is column-locked, and
  `is_demo` cannot be set by clients (0004).
- **Write-forgery hardening (migration 0005):** clients cannot forge predictions/decisions/LLM
  reports against other users' portfolios, nor self-issue `api_keys` scopes. **0006** blocks demo
  deletion by clients; **0007** switches actor FKs to `ON DELETE SET NULL` so records (and the
  audit trail) survive user deletion.
- **Append-only guarantees:** UPDATE/DELETE revoked on `predictions`, `audit_logs`, `override_logs`.
- **Secret handling:** `SUPABASE_SERVICE_ROLE_KEY` lives only on Render; Vercel gets only public
  `NEXT_PUBLIC_*` config; `.env` is gitignored. Rotating the service-role key updates Render only.

---

## 7. Business decisions (locked)

These are settled and drive the forward ML/governance work:

- **Cost-sensitive threshold:** FN:FP cost ratio = **5:1**. The fixed `0.5` threshold is being
  replaced by a cost-tuned threshold persisted per `model_versions.threshold`.
- **Fairness trigger:** the **four-fifths / 0.8 disparity rule** triggers action. (Current audit
  finding: age-group selection-rate disparity ≈ 0.599 — disclosed, not yet mitigated.)
- **Retention:** audit logs **7 years**, predictions **3 years**, raw bureau payloads **90 days**.
- **LLM provider:** **Anthropic/Claude** primary (OpenAI swappable behind the abstraction);
  deterministic **template fallback** when the API is offline, reusing `explain.py`'s
  plain-language layer.
- **Hosting:** stays on **free Vercel + Render**. Custom domain and MCP server come later;
  Terraform is written as **reference IaC** only (no paid cloud stood up).
- **Explainability boundary:** SHAP is **feature contribution, not causal proof**. The platform
  must never state or imply a SHAP value means a feature *caused* default — language is
  "contributed to the score," enforced by a test guard (Stage 3).

---

## 8. Connectors / DataSource design

The synthetic generator stays a deterministic demo/test fixture. Real data is introduced behind a
`DataSource` interface so the ML core never hard-codes a source. Interfaces are **built and
feature-flagged** (`feature_flags` table + `*_ENABLED` env); gated sources ship **OFF** until
their external gate clears.

| Connector | Data | Cost | Gate | Flag (default) |
|---|---|---|---|---|
| Synthetic | UCI-mirror generator | Free | — | on (test fixture) |
| CSV | Uploaded portfolios | Free | — | on |
| UCI real | Credit-card default (Taiwan 2005) | Free | Cite source | on |
| RBA tables | AU macro/credit stats | Free | Attribution | `RBA_ENABLED` |
| ABS Data API | AU labour/income/demographics | Free | API ToS (`ABS_API_KEY`) | `ABS_ENABLED` |
| APRA statistics | AU banking-system stats | Free | Attribution | `APRA_ENABLED` |
| HMDA/FFIEC | US mortgage fair-lending | Free | Public-data ToS | `HMDA_ENABLED` |
| Freddie Mac | Mortgage performance | Free w/ registration | **License — verify first** | `FREDDIE_ENABLED=0` |
| Credit bureaus (Equifax/Experian/illion) | Borrower credit files | **Paid** | **Legal + compliance contract** | `BUREAU_ENABLED=0` |
| Open banking (CDR) | Transactions/affordability | Paid/partner | **CDR accreditation** | `OPENBANKING_ENABLED=0` |

**Hard requirement:** no real dataset — public or commercial — is enabled until license, privacy,
and usage rights are explicitly verified and documented. Enabling a gated connector without its
credentials must fail loudly, naming the required approval.

When real bureau/borrower data lands, PII is isolated in a dedicated encrypted table referenced by
a surrogate id (the NextGen "PII vault" pattern), with retention per §7 and subject-access/erasure
by pseudonymisation. `TODO(verify)`: this PII-isolation table is **designed, not yet in
`supabase/migrations/`** — add it in the same migration wave that enables any real-PII connector.

---

## 9. Limitation matrix (L1–L11)

Honest posture: most limitations are removed by engineering in the forward plan; a few are removed
**only by external gates** no code can bypass (data licenses, bureau contracts, legal review).
`[EXTERNAL GATE]` marks those.

| # | Limitation | What removes it | Owner stage |
|---|---|---|---|
| L1 | Synthetic / real-UCI data only, not real customers | Real-data connectors: real UCI → HMDA → bureau `[EXTERNAL GATE: license/contract]` | Stage 6 |
| L2 | Not calibrated to Australia / any live portfolio | AU macro features + recalibration on local data `[EXTERNAL GATE: data owner]` | Stage 6 |
| L3 | No bureau / transaction / open-banking / collections data | Connector interfaces built; live once contracts exist `[EXTERNAL GATE]` | Stage 6 |
| L4 | Fairness audit is detection-only | `fairlearn` mitigation + governance sign-off | Stage 7 |
| L5 | Fixed 0.5 threshold | Cost-sensitive threshold (FN:FP = 5:1) + calibration, stored per version | Stage 3 |
| L6 | SHAP risks causal misreading | Reason codes + enforced "contribution not causation" text (test-guarded) | Stage 3 |
| L7 | LLM hallucination risk | Grounded memos: structured-inputs-only, post-validation, provenance, template fallback, human review | Stage 5 |
| L8 | Streamlit is portfolio-grade, not enterprise | FastAPI + Next.js **(DONE)**; remaining dashboard sections | Stage 2/4 |
| L9 | No auth/DB/API/monitoring/registry | Supabase Auth+RLS + FastAPI + DB **(DONE)**; MLflow + Evidently/Prometheus outstanding | Stage 1–5 |
| L10 | No legal/compliance validation | Governance pack makes review *possible*; the review itself `[EXTERNAL GATE: legal]` | Stage 7 |
| L11 | Not suitable for real credit decisions | Everything above + L10 sign-off; stays decision-support **by design** even then | Stage 8 |

Additional standing caveats: the Render service must be awake (cold start); one-click demo buttons
need `DEMO_PASSWORD` in Vercel (email login works regardless); no rate limiting yet (needs Redis).

---

## 10. Forward roadmap & ownership

The team executes `Master_Implementation_Plan.md` **adapted onto the live stack** (Supabase +
Render + Vercel replace the plan's local Postgres/Alembic/Docker assumptions). Work is split into
strict, non-overlapping ownership branches:

| Branch | Owner | Scope |
|---|---|---|
| `feat/stage1-db` | db-engineer | `supabase/migrations/` + a `src/db/` repository/access layer over the live schema. |
| `feat/stage2-api` | api-engineer | `services/ml/` FastAPI: harden endpoints, rate limiting, idempotency, error envelope. |
| `feat/stage3-ml` | ml-engineer | `src/ml/`: MLflow registry, explicit feature contract, isotonic calibration, cost-sensitive threshold (FN:FP = 5:1, replacing 0.5), reason codes + "contribution not causation" language guard. |
| `feat/stage4-ui` | frontend-engineer | `frontend/` remaining sections (Executive Overview, Portfolios/upload, Explainability Center, Fairness, Macro context, Governance, Audit Trail, System Health, Settings). |
| `feat/stage5-mon` | mlops-engineer | `src/monitoring/` (Evidently drift), `infra/` (Prometheus/Grafana), and `src/llm/` grounded Anthropic/Claude credit memos with template fallback. |
| `feat/stage6-data` | data-engineer | `src/data/connectors/`: `DataSource` interface + Synthetic/Csv/UCI + free AU macro (RBA/ABS/APRA) + HMDA + gated bureau/open-banking connectors (built, flagged OFF). |

**Cross-cutting stages, routed through the six owners above:**
- **Stage 7 — Fairness mitigation + governance:** `fairlearn` reweighing / per-group threshold
  experiments on the age-group gap; model cards; staging→champion approval workflow (a `governance`
  role action); audit/compliance export; recalibration runbook.
- **Stage 8 — Reference IaC + productionisation:** Terraform written as reference IaC (no paid
  cloud stood up), custom domain + TLS, and an MCP server exposing the platform to agent tooling.

**Invariants across every stage:** the 56 Python tests and 10 Vitest tests stay green; the Streamlit
MVP keeps working; predictions/explanations/recommendations/human-decisions stay four distinct,
separately-stored concepts; and the platform never auto-approves or auto-declines credit.

---

## 11. What changed vs. the NextGen roadmap (supersession log)

The NextGen roadmap was written against a pre-build target stack. The live system diverged; where
it did, the live reality is authoritative:

- **DB/Auth:** local Postgres 16 + Alembic + custom OAuth/OIDC → **Supabase (Postgres 17 + RLS +
  Supabase Auth JWT)**. Alembic and local Postgres are superseded; migrations live in
  `supabase/migrations/`.
- **API package:** a separate `api/` dir → the FastAPI app **is** `services/ml/`. No `api/` package.
- **Frontend:** generic "React/Next.js, Phase 4" → **Next.js 16 App Router, live on Vercel now.**
- **Schema:** the ~18-table design was consolidated (portfolio model instead of
  customers/applications; one `monitoring_metrics` table; inline role on `profiles`; no PII vault
  yet — synthetic data only).
- **Hosting:** "cloud + custom domain, Phase 8" → **free Vercel + Render today**; custom domain,
  MCP server, and Terraform reference IaC are later, deliberately unpaid.

*Companion documents: [`HANDOFF.md`](HANDOFF.md) (live operational truth) ·
[`Master_Implementation_Plan.md`](Master_Implementation_Plan.md) (execution playbook) ·
[`PROJECT_GUIDE.md`](PROJECT_GUIDE.md) (MVP internals).*

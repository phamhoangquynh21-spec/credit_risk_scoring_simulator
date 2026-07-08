# Master Implementation Plan — Removing Every Limitation, Step by Step

**Project:** `credit_risk_scoring_simulator`
**Document type:** Execution playbook (sequenced steps, connectors, prerequisites)
**Companion to:** [`NextGen_Architecture_Roadmap.md`](NextGen_Architecture_Roadmap.md) (the architecture), [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md) (the current system)
**Rule inherited from the roadmap:** the current MVP keeps working at every step; nothing is rewritten wholesale.

> **Honesty note (read first).** Every limitation below has a concrete removal path. Most are removed by engineering work in this plan. A few are removed only by **external actions** — signed data licenses, commercial bureau contracts, legal/compliance review, and budget. Those are marked **[EXTERNAL GATE]**: the engineering to support them is in this plan, but the gate itself is a business action no code can bypass. A plan that claimed otherwise would be lying to you.

---

## Part A — Limitation-by-Limitation Resolution Matrix

Each of the 11 limitations from the roadmap (§14), what removes it, and where in the step sequence it happens.

| # | Limitation today | What removes it | Needs | Steps |
|---|---|---|---|---|
| L1 | Synthetic data (UCI-mirror), not real customers | Real-data ingestion behind `DataSource` connectors: UCI real file → HMDA/Freddie Mac → internal/bureau data | UCI download; Freddie Mac registration **[EXTERNAL GATE: license]**; bureau contract **[EXTERNAL GATE]** | 6.1–6.5 |
| L2 | Not calibrated to Australia / any live portfolio | AU macro features (RBA/ABS/APRA connectors) + recalibration on local data once available | Public APIs (free); local lending data **[EXTERNAL GATE: data owner]** | 6.3, 7.3 |
| L3 | No bureau / transaction / open-banking / collections / hardship data | Connector interfaces + schema (already designed in roadmap §6) implemented; live once contracts exist | CDR/open-banking accreditation or partner, bureau contracts **[EXTERNAL GATE]** | 6.4–6.5 |
| L4 | Fairness audit is detection-only | Mitigation pipeline: reweighing / threshold-per-group experiments (fairlearn), governance sign-off flow | `fairlearn` library; governance policy decision | 7.1 |
| L5 | Fixed 0.5 threshold | Cost-sensitive threshold optimiser + calibration; threshold stored per model version | FN:FP cost ratio from business (default assumption documented) | 3.3–3.4 |
| L6 | SHAP framed risk of causal misreading | Reason-code layer + mandatory "contribution, not causation" text in UI/API/reports (enforced by tests) | none | 3.5 |
| L7 | LLM hallucination risk | Grounded memo layer: structured-inputs-only, post-validation, provenance, template fallback, human review | Anthropic/OpenAI API key | 5.1–5.4 |
| L8 | Streamlit is portfolio-grade, not enterprise-grade | FastAPI service + React/Next.js production UI; Streamlit demoted to internal prototype | Node.js ≥ 20; frontend effort | 2.x, 4.x |
| L9 | No auth, DB, API, monitoring, registry | OAuth2/JWT + API keys; PostgreSQL + Alembic; FastAPI; Evidently + Prometheus/Grafana; MLflow | Docker; Postgres (local → managed) | 1.x–5.x |
| L10 | No legal/compliance validation | Governance pack (model cards, audit exports, approval workflow) that makes review *possible*; the review itself | Lawyers/compliance **[EXTERNAL GATE]** | 7.2 |
| L11 | Not suitable for real credit decisions | Everything above **plus** L10's sign-off. The platform stays decision-support by design even then | All gates cleared | 8.x |

---

## Part B — Prerequisites & Required Information Checklist

Collect these **before** starting the stage that needs them. Nothing before Stage 1 needs anything you don't already have.

### B.1 Tooling (Stage 1–2)
- [ ] **Docker Desktop** installed (Windows: WSL2 backend).
- [ ] **Python 3.12+** (3.14 already proven working in this repo).
- [ ] **Node.js ≥ 20** + pnpm/npm (Stage 4 only).
- [ ] **PostgreSQL 16** — local via Docker first; managed later (Neon/Supabase/RDS/Cloud SQL).

### B.2 Accounts & credentials (by stage; store in `.env`, never commit)
| Variable | Used by | Stage | How to get |
|---|---|---|---|
| `DATABASE_URL` | API, migrations | 1 | Docker compose locally; managed-Postgres console later |
| `JWT_SECRET_KEY` | Auth | 2 | Generate: `python -c "import secrets;print(secrets.token_urlsafe(64))"` |
| `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` | SSO | 2 | Auth0/Okta/Azure AD/Cognito app registration (free tiers exist) |
| `REDIS_URL` | Rate limit, queue | 2/5 | Docker compose; managed later |
| `MLFLOW_TRACKING_URI` | Registry | 3 | Local `mlflow server` first; managed later |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | LLM memos | 5 | console.anthropic.com / platform.openai.com **(billing)** |
| `ABS_API_KEY` | AU indicators | 6 | ABS Data API registration (free) |
| — RBA tables | Macro | 6 | No key; public CSV/XLSX downloads |
| — APRA statistics | Macro | 6 | No key; public downloads |
| Freddie Mac dataset credentials | Loan-level data | 6 | **Register + accept license terms — verify usage rights first [EXTERNAL GATE]** |
| Bureau API credentials (Equifax/Experian/illion) | Production data | 7+ | **Commercial contract + legal approval [EXTERNAL GATE]** |
| Cloud account (AWS/GCP/Azure) + domain | Deploy | 8 | Billing enabled; DNS access |

### B.3 Business decisions to obtain (ask the "business owner" — for a portfolio project, you decide and document)
- [ ] **FN:FP cost ratio** for threshold tuning (default assumption if unknown: FN = 5× FP; document it).
- [ ] **Fairness policy**: which disparity ratio triggers action (default: 0.8 rule) and which mitigation is acceptable.
- [ ] **Retention periods** per table category (suggested: audit 7y, predictions 3y, raw bureau payloads 90d).
- [ ] **LLM provider preference** and monthly budget cap.

---

## Part C — Step-by-Step Build Sequence

Numbered `Stage.Step`. Each step: **Do → Files → Verify**. Stages map to roadmap Phases 0–8. Existing 13 tests must stay green after every stage.

### Stage 0 — Baseline freeze (½ day)
**0.1** Tag the MVP.
- Do: `git tag v1.0-mvp && git push origin v1.0-mvp`
- Verify: tag visible on GitHub; `pytest` green (13/13).

**0.2** Commit the two loose items (`AGENTS.md`, regenerated `business_report.pdf`) or discard the PDF change — decide, don't leave drift.
- Verify: `git status` clean.

---

### Stage 1 — Service boundary + database foundation (Week 1)
**1.1** Create typed settings.
- Do: add `pydantic-settings`; create `src/settings.py` reading `.env` (`DATABASE_URL`, later keys). Keep `src/config.py` untouched (paths/columns still live there).
- Verify: `python -c "from src.settings import settings"`.

**1.2** Extract service facades (no behaviour change).
- Files: `src/services/scoring_service.py` (`score(features)->{probability,risk_score,band,model_version}`), `src/services/explain_service.py` (wraps `explain.py`), `src/services/fairness_service.py`.
- Do: `dashboard.py` switches to facades.
- Verify: dashboard renders identically; new facade unit tests; 13 old tests green.

**1.3** Local Postgres + Redis via Docker.
- Files: `docker-compose.yml` (postgres:16, redis:7, volumes).
- Verify: `docker compose up -d` → `psql` connects.

**1.4** SQLAlchemy models + Alembic — first migration wave (serving core only): `model_versions`, `predictions`, `prediction_explanations`, `decision_recommendations`, `human_decisions`, `audit_logs`, `users`, `roles`, `user_roles`, `api_keys`.
- Files: `src/db/models.py`, `src/db/repo.py`, `migrations/`.
- Do: `alembic init migrations` → autogenerate → review → `alembic upgrade head`.
- Verify: tables exist; repo round-trip test (insert prediction → read back) passes.

**1.5** Persist predictions from the facade (dual-write: filesystem behaviour unchanged, DB row added).
- Verify: scoring via Streamlit inserts a `predictions` + `prediction_explanations` row with `input_hash`, `model_version`, timestamp.

---

### Stage 2 — FastAPI service with auth (Week 2)
**2.1** Scaffold API.
- Files: `api/main.py`, `api/routers/{health,predict,explain,models}.py`, `api/schemas.py`, `api/deps.py`.
- Endpoints: `GET /health`, `GET /ready`, `POST /api/v1/predict`, `POST /api/v1/explain`, `GET /api/v1/models/current`, `GET /api/v1/predictions/{id}`.
- Verify: `uvicorn api.main:app` → OpenAPI docs at `/docs`; TestClient tests pass.

**2.2** Auth: OAuth2 password/JWT for users + hashed API keys for services; RBAC dependency (`analyst/manager/governance/compliance/exec/admin`).
- Verify: no token → 401; wrong role → 403; tests cover both.

**2.3** Cross-cutting middleware: request-id, structured logging with PII redaction (log `input_hash`, never feature values), consistent error envelope, Redis rate limiting, `Idempotency-Key` on `POST /api/v1/predict/batch`.
- Verify: duplicate batch key returns the first result; rate-limit test returns 429.

**2.4** Dockerise the API; GitHub Actions CI (`pytest` + build) on every push.
- Files: `Dockerfile`, `.github/workflows/ci.yml`.
- Verify: CI green on GitHub.

---

### Stage 3 — Governed ML lifecycle (Week 3) — removes L5, L6, part of L9
**3.1** MLflow registry: log every training run (params, metrics, artifact); stages dev→staging→champion; `model_versions` row references the MLflow URI.
- Files: `src/ml/registry.py`; edits to `train_model.run_training()` (additive).
- Verify: `mlflow ui` shows the run; API `GET /models/current` reports the champion.

**3.2** Feature contract validation: explicit schema (name, dtype, range) for the 28 features; validate at train and at every predict.
- Files: `src/ml/feature_contract.py`.
- Verify: request with a missing/out-of-range feature → 422 with a clear message.

**3.3** Calibration: wrap champion in `CalibratedClassifierCV` (isotonic; Platt if data small); store calibration curve.
- Verify: Brier score improves or holds; calibration plot saved to reports.

**3.4** Cost-sensitive threshold: optimiser sweeps thresholds minimising `FN_cost*FN + FP_cost*FP` (ratio from B.3); persist `threshold_used` per model version; API/dashboard use it — **0.5 is gone**.
- Files: `src/ml/threshold.py`.
- Verify: unit test — with FN=5×FP the chosen threshold < 0.5; predictions echo `threshold_used`.

**3.5** Reason codes + language guard: map SHAP `top_factors` to analyst-ready reason codes; append "feature contribution, not causal proof" to every explanation payload; a test greps API/report output to enforce the wording.
- Files: `src/ml/reason_codes.py`.
- Verify: guard test fails if the disclaimer is removed.

---

### Stage 4 — Production frontend (Weeks 4–5) — removes L8
**4.1** Scaffold `frontend/` (Next.js + TypeScript; component lib e.g. shadcn/ui; server-side auth against the API).
**4.2** Ship pages in this order (each usable alone): Single Applicant Risk Assessment → Model Performance → Portfolio Risk Monitor → Fairness & Responsible AI → Executive Overview → remaining pages from roadmap §10.
- UX rules from roadmap §10 are acceptance criteria: prediction vs decision visually separated; model version + data-as-of + decision-support disclaimer on every scoring surface; empty/loading/error states; accessible risk colours.
**4.3** Streamlit app moves to `app/` and is labeled "internal prototype" in its title.
- Verify: e2e smoke (login → score → explain → record human decision); Streamlit still runs.

---

### Stage 5 — Monitoring + LLM memos (Week 6) — removes L7, rest of L9
**5.1** Monitoring jobs: Evidently for feature/prediction drift + data quality; write `drift_metrics`, `data_quality_checks`, `performance_metrics` (label-delayed), `monitoring_events`; Celery beat schedule.
- Verify: inject synthetic drift (shift `limit_bal` +50%) → severity event created → visible in dashboard.

**5.2** Infra metrics: Prometheus middleware (latency histograms, error counters) + Grafana dashboard JSON committed to `infra/`.
- Verify: p95 latency panel live under load test.

**5.3** LLM layer: `src/llm/provider.py` (abstract; Anthropic + OpenAI impls), `src/llm/memo.py` builds the memo **only** from `{prediction, top_factors, application fields, policy text}`; post-validation rejects any sentence referencing a field not in inputs; PII redaction pre-call; template fallback (reuses `explain_in_plain_language`) when the API is down; persist everything to `llm_explanation_reports`; human-review status field gates external use.
- Endpoint: `POST /api/v1/llm-reports/credit-memo`.
- Verify: grounding test (memo about unknown field → rejected); fallback test with network blocked; provenance row complete.

---

### Stage 6 — Real data connectors (Weeks 7–8) — removes L1, L2, L3 (engineering side)
**6.1** `DataSource` interface + `SyntheticSource` (wraps today's generator) + `CsvSource`.
- Files: `src/data/base.py`, `src/data/sources/`.
- Verify: training runs unchanged via `SyntheticSource`.

**6.2** **UCI real dataset**: download the actual UCI file (license: public/academic — cite), map via existing `clean_data()` (it already handles real category codes), retrain, register as a new model version.
- Verify: real-data model logged in MLflow with its own metrics; synthetic remains for tests.

**6.3** **AU macro connectors** (all free/public): RBA tables (CSV download job), ABS Data API (`ABS_API_KEY`), APRA statistics (download job) → `macro_indicators` table; join as context features by period.
- Files: `src/data/connectors/{rba,abs,apra}.py`.
- Verify: `macro_indicators` populated; a training run with macro features completes; document license/attribution for each in `docs/data_sources.md`.

**6.4** **HMDA/FFIEC** (public, US): loader for fair-lending methodology validation — run the fairness pipeline against real demographic outcomes.
- Verify: fairness audit runs on HMDA sample; findings stored in `fairness_audit_runs/results`.

**6.5** **Gated connectors — build the interface, ship disabled**: `FreddieMacSource` (enable only after registration + license verification), `BureauSource` (Equifax/Experian/illion; enable only after commercial contract + legal approval), open-banking/transactions, loan-management, collections/arrears connectors — same pattern: implemented against the interface, feature-flagged off, config documents exactly which credentials + approvals switch them on. **[EXTERNAL GATE]**
- Verify: contract tests run against fixtures; flags off by default; enabling without credentials fails loudly with a message naming the required approval.

---

### Stage 7 — Fairness mitigation + governance pack (Week 9) — removes L4, enables L10
**7.1** Mitigation experiments: `fairlearn` reweighing and per-group threshold analysis on the current age-group gap (ratio 0.599); compare AUC-vs-fairness trade-off; governance chooses; record the decision in `audit_logs` and the model card.
- Verify: experiment notebook + stored results; chosen mitigation (or documented decision *not* to mitigate) applied to champion.

**7.2** Governance pack: auto-generated model cards per version; approval workflow (staging→champion requires a `governance` role action via API); audit/compliance export endpoint (`GET /api/v1/audit/events` + CSV export); access-review script listing stale roles.
- Verify: promoting a model without governance approval → 403; export opens in Excel.

**7.3** AU calibration readiness: recalibration runbook — when local portfolio data arrives (L2's external gate), the documented procedure is: ingest via connector → temporal split → recalibrate → fairness rerun → governance approval. Write it as `docs/runbooks/recalibration.md`.

---

### Stage 8 — Cloud deployment (Week 10) — completes L9, L11 (engineering side)
**8.1** IaC (`infra/terraform/`): managed Postgres, Redis, object storage (models/PDFs/LLM outputs), container hosting (Cloud Run / ECS / AKS), secret manager.
**8.2** CI/CD: on tag → build → migrate → blue/green deploy → post-deploy smoke tests → auto-rollback on failure.
**8.3** Custom domain + TLS; OIDC redirect URIs updated.
**8.4** Load test (`k6`/`locust`): p95 predict latency < 300 ms at target RPS.
- Verify: public authed platform on custom domain; rollback rehearsed once deliberately.

---

## Part D — Connector Reference (what each needs, in one table)

| Connector | Data | Auth/credential | Cost | Legal gate | Env/flag |
|---|---|---|---|---|---|
| UCI dataset | Credit-card default (Taiwan 2005) | none (download) | Free | Cite source | `DATASOURCE=uci` |
| RBA tables | AU macro/credit stats | none | Free | Attribution | `RBA_ENABLED=1` |
| ABS Data API | AU labour/income/demographics | `ABS_API_KEY` | Free | API ToS | `ABS_ENABLED=1` |
| APRA statistics | AU banking system stats | none | Free | Attribution | `APRA_ENABLED=1` |
| HMDA/FFIEC | US mortgage fair-lending | none | Free | Public-data ToS | `HMDA_ENABLED=1` |
| Freddie Mac loan-level | Mortgage performance | Registration login | Free w/ registration | **License terms — verify before use** | `FREDDIE_ENABLED=0` until verified |
| Credit bureaus (Equifax/Experian/illion) | Borrower credit files | Commercial API keys | **Paid contract** | **Legal + compliance approval** | `BUREAU_ENABLED=0` until contracted |
| Open banking (CDR) | Transactions/affordability | Accredited access or partner | Paid/partner | **CDR accreditation** | `OPENBANKING_ENABLED=0` |
| Anthropic/OpenAI | LLM memos | API key | Paid (budget cap) | ToS; PII redaction mandatory | `LLM_PROVIDER=anthropic` |
| OIDC provider | SSO | client id/secret | Free tier | — | `OIDC_*` |
| Cloud (AWS/GCP/Azure) | Hosting | account + IaC creds | Paid | — | per Terraform |

---

## Part E — What "no limitations left" honestly means at the end

After Stage 8, of the original 11 limitations:

- **Fully removed by this plan (engineering):** L4, L5, L6, L7, L8, L9 — mitigation pipeline, tuned thresholds, enforced explanation language, grounded LLM, enterprise UI/API/DB/monitoring/registry.
- **Removed once free public data lands (built-in, just run the steps):** L1 partially (real UCI + HMDA + AU macro replace "synthetic-only"), L2 partially (AU macro context + recalibration runbook).
- **Removed only when external gates clear (plan makes it a switch-flip):** L1/L2/L3 fully (bureau/open-banking/internal data — contracts), L10 (legal/compliance review), L11 (all of the above together).

The platform is engineered so that clearing each external gate requires **configuration, not construction** — that is the strongest "no limits" position a plan can truthfully deliver. And by design it **remains a decision-support system**: removing limitations never means removing the human from the decision.

---

## Part F — Master checklist (print this)

- [ ] Stage 0: tag `v1.0-mvp`; repo clean; 13/13 tests
- [ ] Stage 1: facades + Postgres + Alembic wave 1 + dual-write
- [ ] Stage 2: FastAPI + JWT/API keys + RBAC + rate limit + Docker + CI
- [ ] Stage 3: MLflow + feature contract + calibration + cost threshold + reason codes
- [ ] Stage 4: Next.js frontend (6 core pages) + Streamlit → `app/` internal
- [ ] Stage 5: Evidently drift + Prometheus/Grafana + grounded LLM memos w/ fallback
- [ ] Stage 6: DataSource + real UCI + RBA/ABS/APRA + HMDA + gated connectors (flagged off)
- [ ] Stage 7: fairlearn mitigation + model cards + approval workflow + audit export + recalibration runbook
- [ ] Stage 8: Terraform + CI/CD blue-green + custom domain + load test
- [ ] External gates log: Freddie license ▢ · bureau contract ▢ · open-banking ▢ · legal review ▢

*Every stage ends with: existing tests green, new tests added, `git tag stage-N-complete`, and a one-paragraph changelog entry in `docs/CHANGELOG.md`.*

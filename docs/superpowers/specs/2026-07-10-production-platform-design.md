# Design Spec — Production Explainable AI Credit Risk Platform

**Date:** 2026-07-10
**Status:** Approved design (Parts 1–3 approved in session); pending user review of this written spec
**Supersedes nothing** — implements the vision of the former `docs/NextGen_Architecture_Roadmap.md` (now consolidated into `docs/ARCHITECTURE.md`) via Approach A (Supabase-centric). The Streamlit app remains the internal prototype throughout.

---

## 1. Summary & approved decisions

Evolve the deployed Streamlit MVP into a **multi-user, security-first, AI-native credit-risk decision-support web platform** that strangers can use on a public HTTPS URL.

Decisions locked with the user:

| Decision | Choice |
|---|---|
| Claude's role | **All three**: Claude API inside the product (memos, chart explainer) + platform built by separated Claude Code agents + platform exposes its own MCP server |
| Real data v1 | **Real UCI dataset** (30k anonymized customers, trains model + demo portfolio) + **AU macro overlay** (RBA/ABS/APRA) + **user-uploaded private portfolios**. HMDA deferred. Synthetic generator survives only in tests. |
| User access | **Demo roles + real signup**: 4 one-click read-only demo accounts (Analyst/Manager/Compliance/Executive) + email-verified self-signup via Supabase Auth |
| Domain | **Free `*.vercel.app` subdomain now** (HTTPS automatic); custom domain attachable later without redeploy |
| Architecture | **Approach A**: Next.js on Vercel + Supabase (Sydney) + Python FastAPI ML sidecar + Claude API server-side + MCP server on the ML service |

Product boundary (unchanged from roadmap): **decision-support, never autonomous approval**. Prediction, explanation, recommendation, and human decision remain four separate stored concepts.

## 2. Architecture

```
Browser ──HTTPS── Next.js 15 (App Router, TS) on Vercel
                   │  server routes only; zero secrets in browser
                   ├── Supabase (existing project uiormpweobimumzlxjml, ap-southeast-2)
                   │     Auth: signup/verification/sessions + 4 seeded demo users
                   │     Postgres 17 + RLS (single source of truth)
                   │     Storage: private bucket for uploaded CSV originals
                   ├── ML Service: FastAPI (Python) on Render/Fly free tier
                   │     wraps existing src/ UNCHANGED (score, SHAP, fairness)
                   │     /health, /predict, /predict/batch, /explain, /fairness
                   │     + MCP server endpoint (/mcp, streamable HTTP)
                   └── Claude API (Anthropic), called from Next.js server routes only
Scheduled jobs (GitHub Actions cron): macro refresh, monitoring rollups, alert checks
```

Boundary rule: Python owns ML only; everything else is Supabase/Next.js. Existing `src/` modules and their 16 tests are not modified.

## 3. Real data strategy

1. **UCI real dataset** — one-time ingest script downloads the official UCI "Default of Credit Card Clients" file (public/academic license, cited), retrains the model (existing pipeline), registers a new `model_versions` row, and seeds the public **demo portfolio**. All public charts are real from R1.
2. **AU macro** — cron connectors pull RBA cash rate, ABS unemployment/income, APRA credit aggregates into `macro_indicators` (public-read). Dashboards overlay macro on portfolio risk.
3. **User portfolios** — authenticated upload (CSV, validated against the 23-column contract) → `portfolios`/`portfolio_rows` (owner-only RLS) → batch scored by ML service → `predictions` + explanations stored → private dashboards.

## 4. Database schema (v1 — 18 tables)

| Group | Tables & key columns |
|---|---|
| Identity | `profiles` (user_id PK→auth.users, display_name, org, role enum[analyst,manager,compliance,executive,admin], created_at) · `api_keys` (id, user_id, key_hash, scopes, expires_at, revoked_at) |
| Portfolio | `portfolios` (id, owner_id, name, row_count, created_at) · `portfolio_rows` (id, portfolio_id, features JSONB, row_index) · `upload_files` (id, portfolio_id, storage_path, original_name, size) |
| Scoring | `predictions` (id, portfolio_id nullable, applicant JSONB nullable, probability, risk_score, risk_band, threshold_used, model_version_id, input_hash, latency_ms, created_by, created_at — **immutable**) · `prediction_explanations` (prediction_id, method, top_factors JSONB, base_value) |
| Decisions | `decision_recommendations` (prediction_id, recommended_action, rationale, policy_version) · `human_decisions` (id, prediction_id, final_action, notes, decided_by, decided_at) · `override_logs` (decision_id, overrode bool, reason_code, justification) |
| AI | `llm_reports` (id, prediction_id, provider, model_name, prompt JSONB, structured_inputs JSONB, output_text, source_fields JSONB, redacted bool, review_status, created_by, created_at) |
| Governance | `model_versions` (id, semver, algo, stage[dev,staging,champion,retired], metrics JSONB, trained_on, threshold, approved_by) · `fairness_runs` (id, model_version_id, run_at) · `fairness_results` (run_id, attribute, grp, n, selection_rate, recall, precision, disparity_ratio) · `audit_logs` (id, actor_id, action, entity_type, entity_id, detail JSONB — **append-only**) |
| Context/Ops | `macro_indicators` (source, indicator, period, value — public-read) · `monitoring_metrics` (period, metric, value) · `feature_flags` (key, enabled, note) |

Migrations via Supabase MCP + committed SQL files in `supabase/migrations/`.

## 5. Security model (top priority)

- **RLS on every table, default-deny.** Owner-only: portfolios/rows/files/predictions-of-own-portfolio. Role-gated: governance, audit (compliance/admin), monitoring (manager/admin). Public-read: `macro_indicators`, demo portfolio. RLS is enforced by Postgres, not app code.
- **Secrets**: `ANTHROPIC_API_KEY`, Supabase service key, ML-service key live only in server env vars (Vercel/Render). Browser gets the anon key only (safe by design with RLS).
- **PII**: private storage bucket; logs carry `input_hash` never values; LLM inputs redacted; account deletion cascade-wipes portfolios/files/reports; minimal profile data collected (email, name, org, role).
- **Auth**: Supabase email verification; demo accounts are read-only (RLS role checks); ML service requires a valid Supabase JWT or service key; rate limiting per user/key.
- **Audit**: `audit_logs`/`override_logs` append-only (UPDATE/DELETE revoked); every prediction traceable (model version + input hash + actor + timestamp).
- **Transport**: HTTPS enforced end-to-end (Vercel, Supabase, Render defaults). This satisfies the "secure domain" requirement on the free subdomain from day one.

## 6. Sections (14) and role access

Sections: 1 Executive Overview · 2 Single Applicant Assessment · 3 Portfolio Risk Monitor · 4 My Portfolios · 5 Batch Scoring Results · 6 Model Performance · 7 Explainability Center · 8 Fairness & Responsible AI · 9 Macro Context (AU) · 10 AI Analyst · 11 Model Governance · 12 Audit Trail · 13 System Health & Data Quality · 14 Settings & Access Control.

Access matrix (✅ full, view = read-only, – hidden):

| Section | Analyst | Manager | Compliance | Executive | Admin |
|---|---|---|---|---|---|
| 1 | – | ✅ | – | ✅ | ✅ |
| 2–5 | ✅ | ✅ | view | – | ✅ |
| 6–7 | ✅ | ✅ | ✅ | – | ✅ |
| 8 | view | ✅ | ✅ | – | ✅ |
| 9 | ✅ | ✅ | – | ✅ | ✅ |
| 10 | ✅ | ✅ | – | – | ✅ |
| 11 | – | view | ✅ | – | ✅ |
| 12 | – | – | ✅ | – | ✅ |
| 13 | – | ✅ | – | – | ✅ |
| 14 | profile | profile | profile | profile | ✅ |

Demo accounts demonstrate the matrix live. Enforcement is dual: UI hides + RLS/API denies (defense in depth).

## 7. UX/UI standard

Corporate fintech aesthetic (ui-ux-pro-max + frontend-design skills at build time): slate/navy neutrals, risk colors reserved for risk and WCAG-AA with text labels; shadcn/ui + Tailwind + Recharts; every metric shows value+trend+threshold; prediction visually separated from decision with model version + data-as-of + decision-support disclaimer on every scoring surface; designed empty/loading/error states for all sections; CSV/PDF exports; desktop-first responsive (≥1280px primary, usable ≥768px); dark+light themes; all product copy and memo templates pass humanizer + stop-slop.

## 8. User management

Signup: email+password, verification required. Profile: display name, optional org; role defaults to analyst; only admin promotes. Self-service: password change, data export, account deletion (cascade). Admin: user list, role assignment, disable, audit view. Stored user data is minimal by design.

## 9. Development agent roster

Seven agents, each with own branch/worktree, directory ownership, scoped spec; artifacts (SQL migrations, OpenAPI, generated TS types) are the only inter-agent contract; conventional commits `type(agent/scope):`; one PR per task; CI green + qa-validator approval required to merge; builder never validates own work (SR 11-7 principle).

| Agent | Owns |
|---|---|
| supabase-engineer | `supabase/migrations/`, RLS policies |
| ml-service-engineer | `services/ml/` (FastAPI + MCP server) |
| frontend-engineer | `frontend/` (all 14 sections) |
| ai-engineer | `services/ml/llm/` + Next.js AI routes (grounding, redaction) |
| data-engineer | `services/ml/ingest/` (UCI, RBA/ABS/APRA, cron) |
| qa-validator | `tests/` additions, RLS penetration tests, PR review |
| devops-engineer | CI/CD, env, deploy config, branch protection |

## 10. Backend control plane

Health endpoints + hourly `monitoring_metrics` rollups (volume, latency p50/p95, error rate, PSI drift) rendered in Section 13 · `feature_flags` kill-switches (LLM, uploads, signup) effective without redeploy · Claude API monthly budget cap + per-user daily memo quota enforced server-side · scheduled alert checks email the admin on error/drift/budget breach · runbooks in `docs/runbooks/` (deploy, rollback, incident, key rotation) written before launch · operator access via Supabase MCP, Vercel/Render dashboards.

## 11. AI guardrails

LLM memos: structured inputs only (prediction, SHAP top-factors, application fields, approved policy text); post-generation validator rejects sentences citing out-of-input fields; PII redaction pre-call; provenance row per memo (`llm_reports`); deterministic template fallback on API failure; embedded "not a sole basis for lending decisions" disclaimer; human-review status before external export.
MCP server: read-mostly tools (`score_customer`, `get_portfolio_summary`, `get_model_metrics`, `get_fairness_latest`, `draft_credit_memo`); hashed API-key auth; rate-limited; audit-logged; **no destructive tools**.

## 12. Testing

Existing 16 pytest green throughout (ML core untouched) · ML-service API tests (contract, auth rejection, rate limit) · **RLS penetration tests: user A provably cannot read user B's data** · Playwright e2e (login → upload → score → memo → decision) via webapp-testing skill · AI grounding/fallback/redaction tests · GitHub Actions CI on every PR · branch protection on `main`, no self-merge.

## 13. Rollout — five shippable releases

| Release | Ships |
|---|---|
| R1 Foundation | Supabase schema+RLS+auth+demo roles · ML service · Next.js shell + Sections 2, 3, 6 on real UCI · public vercel.app URL |
| R2 User data | Sections 4, 5 · profile/settings · erasure |
| R3 Context & responsibility | Sections 1, 7, 8, 9 (macro connectors live) |
| R4 AI-native | Section 10 (memos + chart explainer) · MCP server · quotas (**needs ANTHROPIC_API_KEY + budget cap**) |
| R5 Governance & ops | Sections 11–14 · alerts · runbooks · optional custom domain |

Each release: tests green → tag → deploy → CHANGELOG entry.

## 14. Prerequisites (external to code)

- Render free account (default ML-service host; Fly.io is the fallback if Render's free tier changes) — user creates at R1, ~5 min.
- Vercel account linked to the GitHub repo (R1) — user creates, ~5 min.
- `ANTHROPIC_API_KEY` with monthly cap (R4) — user creates; until then AI Analyst renders template-fallback memos, clearly labeled.
- Custom domain (optional, R5) — user purchases if/when wanted.
- Supabase: already provisioned (project `uiormpweobimumzlxjml`, Sydney) and MCP-connected.

## 15. Out of scope (this build)

Real bureau/open-banking/collections connectors (contract-gated; interfaces only) · HMDA ingestion · MLflow (registry-lite table instead) · BigQuery/Snowflake warehouse · Celery/Redis queue (cron + serverless suffice at this scale) · autonomous decisioning (excluded by product principle, permanently).

## 16. Success criteria

A stranger can: open the public HTTPS URL → one-click demo any of 4 roles and see role-appropriate real-data dashboards → sign up, verify email, upload their own CSV portfolio, batch-score it, and see private charts of their real data → generate a grounded AI credit memo (R4+) → and cannot access anyone else's data (RLS-proven). The owner can: flip kill-switches, see health/drift/budget, audit every action, and roll back any release. All existing ML tests stay green; every release is tagged and demo-able.

# Credit Risk Scoring Simulator — Handoff Document

**Last updated:** 2026-07-13
**Owner:** Adam Pham (`phamhoangquynh21@gmail.com`)
**Repo:** https://github.com/phamhoangquynh21-spec/credit_risk_scoring_simulator

This document is the single source of truth for what exists, where it runs, how to
operate it, and what's next. Read it first before touching anything.

> **R2 status (2026-07-13):** the full `docs/Master_Implementation_Plan.md` build is
> complete — all 8 stages merged to `main` (tags `stage-1..8-complete`): `src/db`
> access layer, governed ML lifecycle (`src/ml`: registry, feature contract,
> calibration, cost-sensitive threshold, reason codes), monitoring + grounded LLM
> memos (`src/monitoring`, `src/llm`), real/gated data connectors (`src/data`),
> fairness mitigation + governance (model cards, approval-gated promotion), the
> FastAPI wiring for all of it, the Next.js dashboard on the approved design system,
> and a read-only MCP server (`mcp_server/`) + reference Terraform (`infra/terraform/`).
> **224 Python tests + 13 Vitest, green.** Still open: custom domain (needs a domain),
> re-tuning the live champion's threshold (machinery built; see the recalibration
> runbook), and a live `ANTHROPIC_API_KEY` for non-template memos. See `docs/CHANGELOG.md`.

---

## 1. What this project is

A portfolio-grade **Explainable AI credit-risk platform** (Finance × Data Science)
that predicts the probability a credit-card customer defaults next month and
explains *why*. It exists in two layers:

1. **The MVP** — a self-contained Python + Streamlit app (the original deliverable).
2. **The production platform (R1)** — a multi-user web platform: Next.js dashboard +
   FastAPI ML service + Supabase (auth/DB/RLS), built to demonstrate production
   fintech engineering. This is the current focus.

The data is **synthetic-but-realistic**, mirroring the UCI "Default of Credit Card
Clients" (Taiwan, 2005) schema, and the platform also ingests the **real UCI file**
(30k rows) — the trained model reaches **AUC ≈ 0.78**.

---

## 2. Live services (all deployed)

| Service | URL | Host | Notes |
|---|---|---|---|
| **Production dashboard** (Next.js) | https://credit-risk-scoring-simulator.vercel.app | Vercel | The main platform UI |
| **ML service** (FastAPI) | https://credit-risk-ml-vmp3.onrender.com | Render (free) | `/health`, `/ready`, `/api/v1/*`. Sleeps when idle (~30–50s cold start) |
| **Streamlit MVP** | https://creditriskscoringsimulator-dzqtmjsoouv4ud4pk5siae.streamlit.app | Streamlit Cloud | The original self-contained demo |
| **Database / Auth** | project `uiormpweobimumzlxjml` (region ap-southeast-2) | Supabase | Postgres 17, 18 tables, RLS enforced |

### Logging in to the dashboard
Use the **email sign-in form** on the login page:
- Email: `demo-analyst@demo.local` (also `demo-manager`, `demo-compliance`, `demo-executive`)
- Password: the `DEMO_PASSWORD` value in the local `.env` (not committed)

The four **one-click role buttons** additionally require `DEMO_PASSWORD` to be set as a
Vercel env var (Production scope) + redeploy. Until then, use the email form.

---

## 3. Architecture

```
Browser
  │  HTTPS
  ▼
Next.js 16 dashboard (Vercel)  ── @supabase/ssr ──►  Supabase (Auth + Postgres 17 + RLS)
  │  server route handlers                                ▲
  │  forward the user's JWT                                │ RLS-governed reads
  ▼                                                        │ (anon key + user session)
FastAPI ML service (Render)  ── service-role key ─────────┘
  wraps the existing src/ Python ML pipeline
  /predict  /explain  /predict/batch  /models/current
```

- **Frontend** reads Supabase directly for data (Sections 3 & 6) using the anon key
  under the user's session (RLS enforces per-user isolation). For scoring (Section 2)
  it POSTs to its own route handlers, which forward the Supabase JWT to the ML service.
- **ML service** re-verifies the JWT with Supabase, scores via the existing `src/`
  code, and persists predictions/explanations to Postgres.
- **Secrets never reach the browser**: only `NEXT_PUBLIC_*` (Supabase URL + anon key,
  both public by design) are client-visible. The service-role key lives only on Render.

---

## 4. Repository layout

```
credit_risk_scoring_simulator/
├── src/                       # Python ML core (MVP): generate_data, preprocessing,
│                              #   train_model, explain (SHAP), fairness, dashboard (Streamlit),
│                              #   generate_reports.  DO NOT break — 56 tests depend on it.
├── services/ml/               # FastAPI ML service (wraps src/): main, settings, auth (JWT+RBAC),
│                              #   scoring, persistence, errors, routers/*, Dockerfile
├── frontend/                  # Next.js 16 dashboard (App Router, TS, Tailwind)
│   ├── src/app/               #   (app) route group (assess/portfolio/performance), login, api/*
│   ├── src/components/        #   Sidebar, DisclaimerBar, ApplicantForm, ScoreResult, MetricTile, ...
│   ├── src/lib/               #   supabase clients, ml proxy, format/nav/bands helpers
│   ├── src/middleware.ts      #   auth gate (hardened: never hard-500s)
│   └── .env.production        #   PUBLIC Supabase config baked for build (committed on purpose)
├── supabase/migrations/       # 0001..0007 — schema, RLS, seed-supporting DDL (applied live)
├── scripts/                   # ingest_uci.py (real data), seed_platform.py (demo users/portfolio)
├── data/ models/ reports/     # raw CSV, model.pkl (committed for deploy), metrics.json, reports
├── docs/                      # specs, plans, runbooks, guides (see §8)
├── render.yaml                # Render Blueprint for the ML service
├── vercel.json                # builds the Next app in frontend/ (@vercel/next) — see §7
├── requirements.txt           # Python ML deps (root)
└── .env                       # secrets (gitignored) — see §5
```

Branches: **`main`** contains everything (R1 Plans 1–3 merged). Feature branches
`feat/r1-foundation`, `feat/r1-plan2-ml-service`, `feat/r1-plan3-frontend` and tags
`r1-plan{1,2,3}-complete` mark the review milestones.

---

## 5. Environment variables

Local dev uses the **gitignored `.env`** at repo root:

| Var | Used by | Secret? | Value source |
|---|---|---|---|
| `SUPABASE_URL` | ML service, scripts | no | `https://uiormpweobimumzlxjml.supabase.co` |
| `SUPABASE_ANON_KEY` | frontend, ML service | **public** (RLS-protected) | Supabase → Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | ML service, scripts | **YES — never commit / never put in Vercel** | Supabase → Settings → API |
| `DEMO_PASSWORD` | demo login | secret-ish | your chosen demo password |

**Where each deployment gets them:**
- **Vercel (frontend):** public Supabase config + `ML_SERVICE_URL` are baked into the
  committed `frontend/.env.production`. `DEMO_PASSWORD` must be set in the Vercel
  dashboard (Production) to enable the one-click demo buttons. **Never** put the
  service-role key in Vercel.
- **Render (ML service):** `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
  are set in the Render dashboard (`render.yaml` declares them `sync:false`).

---

## 6. Running locally

Python side (ML + Streamlit MVP):
```bash
py -m venv .venv                          # Python 3.11+ (3.14 verified)
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m pytest        # 56 tests (needs .env for the live-Supabase RLS tests)
.venv/Scripts/python.exe -m streamlit run src/dashboard.py     # MVP
.venv/Scripts/python.exe -m uvicorn services.ml.main:app --port 8000   # ML service
```

Frontend (Next.js) — **Node is portable, not on PATH** (see §9):
```bash
export PATH="/c/Users/Gamer/AppData/Local/nodejs-portable/node-v24.18.0-win-x64:$PATH"
cd frontend
npm install
npm run test          # 10 Vitest tests
npm run dev           # http://localhost:3000 (needs frontend/.env.local; Section 2 needs the ML service at ML_SERVICE_URL)
npm run build
```

---

## 7. Deployment notes & the gotchas we hit (IMPORTANT)

These cost real debugging time — documented so they don't recur:

1. **Vercel built the repo root as Python.** The repo root has `requirements.txt`, so
   Vercel auto-detected Python and failed on a missing entrypoint. The dashboard
   "Root Directory = frontend" setting **would not persist** (framework stayed
   `python` per the API). **Fix:** a root **`vercel.json`** with
   `"builds": [{"src":"frontend/package.json","use":"@vercel/next"}]` pins the build to
   the Next app. This is why `vercel.json` exists — do not delete it.
2. **`NEXT_PUBLIC_*` env vars were undefined at build → every Supabase call 500'd.**
   These are inlined at *build* time; setting them in the dashboard after a build (or on
   the wrong scope) leaves them missing. **Fix:** committed `frontend/.env.production`
   with the public Supabase URL + anon key (public by design) so the build is
   self-sufficient. `ML_SERVICE_URL` is baked there too.
3. **Vercel Deployment Protection** was ON, returning a Vercel-SSO redirect for
   anonymous visitors. Disable it (Settings → Deployment Protection → Vercel
   Authentication → Disabled) for a public demo.
4. **Middleware hardened**: `frontend/src/middleware.ts` wraps the Supabase check in
   try/catch and short-circuits on missing env, so it can never turn the whole site
   into a 500 (we saw `MIDDLEWARE_INVOCATION_FAILED`).
5. **Model file committed**: `models/model.pkl` is force-committed (past gitignore) so
   the Render Docker image is self-contained (no training step at deploy). If it ever
   fails to load due to library drift, add a `python -m src.train_model` build step
   (the `data/raw` CSV is in the image).
6. **Render free tier sleeps** after ~15 min idle → first request ~30–50s cold start.

Runbooks: `docs/runbooks/frontend-deploy.md`, `docs/runbooks/ml-service-deploy.md`.

---

## 8. Key documents

| Doc | What it is |
|---|---|
| `docs/PROJECT_GUIDE.md` | Multi-level explainer of the whole MVP (study guide + reference + per-file internals) |
| `docs/ARCHITECTURE.md` | Single source of truth for architecture (live stack + forward roadmap); supersedes the old NextGen roadmap |
| `docs/Master_Implementation_Plan.md` | Limitation-by-limitation removal plan |
| `docs/superpowers/specs/2026-07-10-production-platform-design.md` | The approved platform design (Approach A) |
| `docs/superpowers/plans/2026-07-11-r1-plan*.md` | The three R1 implementation plans (executed) |
| `PRD.md`, `Technical_Spec.md` | Original MVP product + technical specs |

---

## 9. Environment gotchas (this Windows machine)

- **`C:/Users/Gamer` (home) is itself a git repo** — never commit from there; always
  work in the project repo.
- **Bare `python`/`py` are Windows Store stubs** — use `.venv/Scripts/python.exe`.
- **Node.js is portable** at `C:\Users\Gamer\AppData\Local\nodejs-portable\node-v24.18.0-win-x64`
  (v24.18.0), **not on PATH** — prepend it in every shell (see §6).
- **`gh` CLI is not installed** (winget can't in this environment). Push with plain
  `git push` (Git Credential Manager handles auth). PRs were created via the GitHub API
  using the GCM-cached token.

---

## 10. Testing & quality posture

- **Python:** 224 tests (`pytest`) — ML pipeline, preprocessing, batch scoring, ML-service
  API/auth, RLS penetration tests (prove cross-user isolation), report generation, plus
  the R2 layers: `src/db` repos, `src/ml` lifecycle, `src/data` connectors, `src/monitoring`
  drift/quality, `src/llm` grounded memos, fairness mitigation, and the MCP tools.
  (Some tests are credential-gated and skip cleanly without `.env`.)
- **Frontend:** 13 tests (`vitest`) — helpers, Supabase clients, RBAC, schema mapping,
  nav, the SHAP-factor regression test.
- Everything was built via **subagent-driven development**: implementer + independent
  reviewer per task + a final whole-branch review. That process caught real bugs before
  merge (e.g. the ML Dockerfile missing `supabase`, RLS write-forgery holes, the
  Section-2 SHAP `top_factors` field mismatch).

---

## 11. Known limitations (be honest about these)

- **Synthetic/real-UCI data only** — not real customers, not AU-calibrated, not for real
  lending decisions. The UI says "decision-support only" everywhere.
- **Section 2 needs the Render service awake** — cold start delay on first use.
- **One-click demo buttons** need `DEMO_PASSWORD` in Vercel (email login works regardless).
- **Fairness is detect-only**; **threshold is 0.5** (should be cost-tuned); **SHAP =
  contribution, not causation** (stated in-app).
- **No production hardening beyond R1**: no rate limiting (needs Redis), no MLflow
  registry, no monitoring dashboard, no LLM credit memos — all scoped as R2+.

---

## 12. What's next (R2+)

The R2 build (Master Plan Stages 1–8) is **done** — see the R2 status note at the top
and `docs/CHANGELOG.md`. What genuinely remains:

- **Custom domain** (Master Plan 8.3): reference Terraform is committed but the app
  still runs on the free `*.vercel.app` / Render / Supabase stack. Needs a domain the
  owner provides + DNS access; then point it at Vercel/Render.
- **Re-tune the live champion's threshold**: the cost-sensitive threshold machinery
  (`src/ml/threshold.py`, FN:FP 5:1) is built and tested, but the live champion
  `1.0.0-real-uci` still stores `threshold=0.5`. Re-tuning is a data step — follow
  `docs/runbooks/recalibration.md`.
- **Live LLM memos**: the grounded-memo layer works today via a deterministic template;
  set `ANTHROPIC_API_KEY` (+ `pip install anthropic`) to switch to live Claude.
- **Enable a gated connector** (bureau / open banking / Freddie Mac): flip its
  `feature_flags` row on *and* provide credentials — both are required, and each fails
  loudly otherwise (see `docs/data_sources.md`).
- **Cloud migration / CI-CD blue-green** (Master Plan 8.1–8.2): the Terraform blueprint
  exists; standing it up is a business decision (cost + a cloud account).

---

## 13. Quick operational reference

- **Redeploy frontend:** push to `main` (Vercel auto-deploys; touch something under
  `frontend/` since "skip unchanged root" is on).
- **Redeploy ML service:** push to `main` (or Render dashboard → Manual Deploy). Verify
  `…onrender.com/health` → `{"status":"ok"}` and `/ready` → `model_present:true`.
- **Apply a DB migration:** add `supabase/migrations/000N_*.sql`; apply via the Supabase
  MCP/dashboard (migrations 0001–0007 already applied live).
- **Rotate the service-role key** if ever exposed: Supabase → Settings → API → reset,
  then update it in Render only.

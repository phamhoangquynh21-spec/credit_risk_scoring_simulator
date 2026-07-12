# Credit Risk Scoring Simulator

Predict the probability that a credit-card customer defaults on their next
payment — and explain *why* — as an auditable, decision-support platform.
A Finance × Data Science portfolio project built to look and behave like real
fintech risk infrastructure, not a notebook demo.

**Author:** Adam Pham · **Decision-support only** — this scores synthetic and
public research data, never real lending decisions.

## Live services

| Service | URL |
|---|---|
| Production dashboard (Next.js) | https://credit-risk-scoring-simulator.vercel.app |
| ML API (FastAPI) | https://credit-risk-ml-vmp3.onrender.com — `/health`, `/docs` |
| Streamlit prototype | https://creditriskscoringsimulator-dzqtmjsoouv4ud4pk5siae.streamlit.app |
| Database / Auth | Supabase (Postgres 17, RLS) |

> The ML API runs on Render's free tier and sleeps when idle — the first request
> after a pause takes ~30–50s to wake.

## What it does

Given a customer's credit profile (limit, demographics, and six months of
repayment / bill / payment history), the platform returns:

- a **0–100 risk score** and a Low / Medium / High band;
- a **calibrated default probability** and an **approve / refer / decline**
  recommendation set against a **cost-sensitive threshold** (not a naïve 0.5);
- a **SHAP explanation** turned into analyst-ready **reason codes**, each carrying
  the explicit reminder that these are *feature contributions, not proof of
  causation*;
- a **fairness read** across protected attributes (four-fifths / 0.8 rule).

The decision always stays with the human — the UI separates the model's
prediction from the recorded decision, and every scoring surface shows the model
version, the data-as-of date, and a decision-support disclaimer.

## Architecture

Two layers share one Python ML core:

```
Browser
  │ HTTPS
  ▼
Next.js dashboard (Vercel) ── @supabase/ssr ──►  Supabase (Auth + Postgres 17 + RLS)
  │ server route handlers forward the user JWT           ▲
  ▼                                                       │ RLS-governed reads
FastAPI ML service (Render) ── service-role key ─────────┘
  wraps the src/ ML pipeline · /predict /explain /predict/batch /models/current
```

- The **frontend** reads Supabase directly under the user's session (RLS enforces
  per-user isolation) and POSTs scoring requests to its own route handlers, which
  forward the Supabase JWT to the ML service.
- The **ML service** re-verifies the JWT, scores via the `src/` code, and persists
  predictions and explanations to Postgres.
- **Secrets never reach the browser** — only the public Supabase URL + anon key
  are client-visible; the service-role key lives only on Render.

Full detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## The data

Trained on the real **UCI *Default of Credit Card Clients*** dataset (Taiwan,
2005 — 30,000 records; public, cited), reaching **AUC ≈ 0.78** on the held-out
test set. A structurally-identical **synthetic generator** (`src/generate_data.py`)
mirrors the UCI schema for tests and offline demos, so the suite never depends on
a download. Additional free public sources (RBA / ABS / APRA macro indicators,
HMDA fair-lending data) are wired through a connector layer; commercial sources
(bureau, open banking, Freddie Mac) are built against the same interface but
ship **feature-flagged off** behind their license/contract gates.

## Repository layout

```
├── src/                 # Python ML core: data gen, preprocessing, training, SHAP, fairness, Streamlit
│   ├── db/              #   Supabase access layer (model registry, monitoring, fairness, audit, flags)
│   ├── ml/              #   registry (MLflow), feature contract, calibration, cost-sensitive threshold, reason codes
│   └── data/            #   DataSource interface + real/macro/gated connectors
├── services/ml/         # FastAPI ML service (JWT auth + RBAC) wrapping src/
├── frontend/            # Next.js 16 dashboard (App Router, TypeScript, Tailwind)
├── supabase/migrations/ # Postgres schema + RLS (applied live)
├── scripts/             # UCI ingest, platform seed
├── notebooks/           # EDA, modeling, fairness audit
├── docs/                # architecture, handoff, guides, runbooks, plans
├── data/ models/ reports/
├── render.yaml          # Render blueprint (ML service)
└── vercel.json          # Vercel build config (frontend)
```

## Running locally

**Python core (ML + Streamlit + FastAPI):**
```bash
py -m venv .venv                                   # Python 3.11+ (3.14 verified)
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m pytest                 # full test suite
.venv/Scripts/python.exe -m streamlit run src/dashboard.py
.venv/Scripts/python.exe -m uvicorn services.ml.main:app --port 8000
```
MLflow-based training extras live in `requirements-train.txt` (training only —
not needed to serve).

**Frontend (Next.js):**
```bash
cd frontend
npm install
npm run test        # Vitest
npm run dev         # http://localhost:3000
```

Environment variables and the deployment gotchas we hit are documented in
[`docs/HANDOFF.md`](docs/HANDOFF.md).

## Testing & quality

- **Python:** 100+ tests (`pytest`) — ML pipeline, preprocessing, batch scoring,
  the `src/db` access layer, the `src/ml` lifecycle, and RLS penetration tests
  that prove cross-user isolation.
- **Frontend:** Vitest — helpers, Supabase clients, RBAC, schema mapping, and a
  SHAP-factor regression test.
- Built stage-by-stage with an implementer + independent adversarial reviewer per
  change; the MVP core stays green after every stage.

## Documentation

| Doc | What it is |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | The live system architecture (single source of truth) |
| [`docs/HANDOFF.md`](docs/HANDOFF.md) | Operating guide: services, env vars, deploy, runbooks |
| [`docs/Master_Implementation_Plan.md`](docs/Master_Implementation_Plan.md) | The staged plan removing each limitation |
| [`docs/PROJECT_GUIDE.md`](docs/PROJECT_GUIDE.md) | Deep explainer of the MVP core, per module |
| [`docs/PRD.md`](docs/PRD.md) · [`docs/Technical_Spec.md`](docs/Technical_Spec.md) | Original MVP product + technical specs |

## Honest limitations

- Scores **synthetic and public research data** — not real customers, not
  calibrated to any live portfolio, never a real lending decision.
- Fairness is measured and reported; automated mitigation and full governance
  sign-off are in progress.
- Commercial data connectors (bureau, open banking) exist as disabled interfaces —
  enabling them requires contracts and legal review no code can bypass.
- SHAP shows contribution, not causation — stated everywhere it appears.

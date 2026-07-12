# Credit Risk Scoring Simulator — Frontend

Next.js (App Router) frontend for the Credit Risk Scoring Simulator: auth, single-applicant
scoring (Section 2), portfolio monitoring (Section 3), and model performance (Section 6),
backed by Supabase (auth + data) and the FastAPI ML service (scoring).

**Live:** deployed on Vercel (Root Directory = `frontend`). The ML service runs on Render
(`https://credit-risk-ml-vmp3.onrender.com`) and is wired in via the `ML_SERVICE_URL` env var.

## Prerequisites

- **Node.js 20+**, portable install on this machine (not on PATH). Before any `npm`/`npx`
  command, prepend the portable Node directory to `PATH`:

  ```bash
  export PATH="/c/Users/Gamer/AppData/Local/nodejs-portable/node-v24.18.0-win-x64:$PATH"
  ```

- A Supabase project (URL + anon key) with the schema/RLS from the Plan 1 migrations.
- For Section 2 (single applicant scoring) to work, the FastAPI ML service
  (`services/ml`) must be reachable at `ML_SERVICE_URL`.

## Install

```bash
cd frontend
npm install
```

## Environment variables

Copy `.env.example` to `.env.local` and fill in real values:

```bash
cp .env.example .env.local
```

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL (public, used by browser + server clients) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon/public key (public) |
| `ML_SERVICE_URL` | Base URL of the FastAPI ML service, e.g. `http://localhost:8000` (server-only — never exposed to the browser) |
| `DEMO_PASSWORD` | Shared password used by the demo-role login flow (server-only) |

`.env.local` is gitignored and must never be committed.

## Development

```bash
npm run dev
```

Runs the app at http://localhost:3000. Section 2 (`/assess`) requires the ML service
running locally (see `services/ml/README.md`) and reachable at `ML_SERVICE_URL`; without
it, prediction requests will fail with a 502. Sections 3 (`/portfolio`) and 6
(`/performance`) only depend on Supabase and work independently of the ML service.

## Tests

```bash
npm run test
```

Runs the Vitest suite (unit tests for `lib/`, `components/`, and auth actions).

## Production build

```bash
npm run build
```

Compiles the app for production (server output — this app is **not** statically
exported, since it needs server-side Supabase sessions and the `/api/*` route handlers).
Run `npm run start` to serve the build locally.

## Routes

| Route | Section |
| --- | --- |
| `/login` | Demo-role + email/password sign-in |
| `/assess` | Section 2 — Single Applicant scoring |
| `/portfolio` | Section 3 — Portfolio Monitor |
| `/performance` | Section 6 — Model Performance |
| `/api/predict`, `/api/explain` | Server-side proxy to the ML service (forwards the user's Supabase JWT) |
| `/api/demo-login` | Demo-role login handler |

## Deploying

See [`docs/runbooks/frontend-deploy.md`](../docs/runbooks/frontend-deploy.md) for the
Vercel deploy runbook.

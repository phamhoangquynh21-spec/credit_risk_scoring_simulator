# Runbook: Deploy the Frontend to Vercel

Deploys the Next.js app in `frontend/` to Vercel. Sections 3 (Portfolio Monitor) and 6
(Model Performance) work Supabase-only. Section 2 (Single Applicant scoring) additionally
requires the ML service to be deployed and reachable — see **Follow-up** below.

## 1. Import the project

1. In Vercel, **Add New → Project** and import this repository.
2. Under **Root Directory**, set it to `frontend` (the repo root is not the Next.js app —
   the app lives in the `frontend/` subdirectory).
3. Framework preset should auto-detect as **Next.js**. Leave build/output settings at
   their defaults (`npm run build`, server output — this app is not statically exported).

## 2. Set environment variables

In the Vercel project's **Settings → Environment Variables**, add these 4 variables
(for Production, and Preview if desired):

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Your Supabase anon/public key |
| `ML_SERVICE_URL` | Base URL of the deployed ML service (see Follow-up if not yet deployed) |
| `DEMO_PASSWORD` | Shared password for the demo-role login flow |

Do not commit these values anywhere — set them only in Vercel's dashboard.

## 3. Deploy

Trigger a deploy (push to the connected branch, or **Deploy** in the Vercel dashboard).
Verify the build succeeds and the app is reachable at the assigned Vercel URL.

## 4. Smoke test

- `/login` — demo-role and/or email sign-in works.
- `/portfolio` — loads portfolio segments from Supabase.
- `/performance` — loads champion model metrics from Supabase.
- `/assess` — only fully works once the ML service follow-up (below) is complete;
  until then, expect a 502 from `/api/predict` and `/api/explain`.

## Follow-up: deploy the ML service for Section 2

Section 2 (`/assess`) calls the FastAPI ML service (`services/ml`, with its own
`Dockerfile`) via the server-side `/api/predict` and `/api/explain` routes, which forward
the signed-in user's Supabase JWT. Until the ML service is deployed:

- **Sections 3 and 6 work normally** (Supabase-only, no dependency on the ML service).
- **Section 2 returns a 502** from `/api/predict` / `/api/explain`, since `ML_SERVICE_URL`
  has no reachable service behind it (e.g. still pointing at `http://localhost:8000`).

To complete Section 2 in production:

1. Deploy `services/ml` (its `Dockerfile`) to a container host — e.g. Render.
2. Once deployed, copy its public URL.
3. In the Vercel project, update `ML_SERVICE_URL` to that URL and redeploy the frontend.

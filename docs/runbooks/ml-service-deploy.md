# ML Service Deploy Runbook — Render

Deploys the FastAPI ML service (`services/ml/`) so the frontend's **Section 2
(Single Applicant)** works end-to-end. Sections 3 & 6 do **not** need this — they
read Supabase directly.

## What's already prepared (in the repo)
- `services/ml/Dockerfile` — builds the service (root + service requirements, `src/`, `services/`, `models/`).
- `models/model.pkl` — the trained real-UCI model, **committed** so the image needs no training step.
- `render.yaml` — Render Blueprint: Docker service, `$PORT` binding, `/health` check, and the 3 secret env vars declared as `sync:false` (you paste values in the dashboard).

## Steps (you do these — they need your Render account)

1. **Create a Render account** at <https://render.com> (free) and connect your GitHub (`phamhoangquynh21-spec`).

2. **New → Blueprint.** Select this repo. For **branch**, choose one that contains `services/ml/` and `render.yaml`:
   - `feat/r1-plan2-ml-service` (or `feat/r1-plan3-frontend`, which includes it), **or**
   - `main` — *recommended, after you merge the PR stack (#1 → #2 → #3)*.

3. Render reads `render.yaml` and shows the service **credit-risk-ml**. It will prompt for the 3 secret env vars — paste these (same values as your local `.env`):
   - `SUPABASE_URL` = `https://uiormpweobimumzlxjml.supabase.co`
   - `SUPABASE_ANON_KEY` = *(your Supabase anon key)*
   - `SUPABASE_SERVICE_ROLE_KEY` = *(your Supabase service_role key — secret)*

4. **Apply / Create.** First build takes ~5–10 min (installs xgboost/shap/pandas). When live, Render gives a URL like `https://credit-risk-ml.onrender.com`.

5. **Verify**: open `https://credit-risk-ml.onrender.com/health` → should return `{"status":"ok"}`. And `/ready` → confirms the model loaded.

6. **Give the URL to the frontend**: set `ML_SERVICE_URL` in Vercel (see `docs/runbooks/frontend-deploy.md`) to `https://credit-risk-ml.onrender.com` (no trailing slash), then redeploy the frontend. Section 2 now scores live.

## Notes & caveats
- **Free tier sleeps** after ~15 min idle; the first request after sleep takes ~30–50 s (cold start) — fine for a demo, mention it if presenting.
- **Model/library compatibility**: `model.pkl` was trained with the pinned libs in `requirements.txt`. If the service logs a load error on boot (library drift), the fix is to add a one-off build step `python -m src.train_model` (regenerates the pkl from the committed `data/raw` CSV) — the data is in the image. Ask and I'll wire that into the Dockerfile.
- **CORS**: the frontend calls the ML service **server-side** (Next.js route handlers), not from the browser, so no CORS config is needed.
- Keep `autoDeploy: false` (in `render.yaml`) until you're happy, then flip it on for push-to-deploy.

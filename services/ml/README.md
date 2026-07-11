# Credit Risk ML Service (R1 Plan 2)

FastAPI service wrapping the `src/` ML pipeline. Endpoints (all under `/api/v1`
except health): `GET /health`, `GET /ready`, `GET /api/v1/models/current`,
`POST /api/v1/predict`, `POST /api/v1/predict/batch`, `POST /api/v1/explain`.

## Run locally
```bash
.venv/Scripts/python.exe -m uvicorn services.ml.main:app --reload --port 8000
# docs at http://localhost:8000/docs
```

Auth: send `Authorization: Bearer <supabase access token>`. Predictions are
written to Supabase with `created_by` = the token's user, so Plan 1 RLS governs
reads. Deferred to R4: MCP server, LLM credit memos.

## Deploy (Render, later)
Build from `services/ml/Dockerfile`; set env vars `SUPABASE_URL`,
`SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`.

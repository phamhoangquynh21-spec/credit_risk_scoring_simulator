# Reference IaC — full cloud deployment (NOT applied)

This Terraform is **reference infrastructure-as-code**, not a live deployment. The
platform currently runs on managed services (Supabase Postgres + Auth, Vercel for
the Next.js dashboard, Render for the FastAPI ML service) — see
[`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md). This module documents what a
**self-hosted, single-cloud** migration would provision, so the path off the
managed stack is configuration rather than design work (Master Plan Stage 8.1).

It targets **Google Cloud** as a concrete example; the same shape (managed
Postgres, Redis, object storage, container hosting, secret manager) maps directly
onto AWS (RDS + ElastiCache + S3 + ECS/Fargate + Secrets Manager) or Azure.

> ⚠️ **Do not `terraform apply` this as-is.** It has no backend/state config and no
> credentials, and standing up these resources incurs real cost. It is committed for
> review and as the migration blueprint. Costs and exact resource sizing are
> deliberately conservative placeholders.

## What it provisions

| Component | GCP resource | Replaces (today) |
|---|---|---|
| ML service container | Cloud Run (`google_cloud_run_v2_service`) | Render |
| Relational DB | Cloud SQL for PostgreSQL | Supabase Postgres |
| Cache / rate-limit / queue | Memorystore for Redis | (not yet used; R2 rate limiting) |
| Model / report / LLM-output storage | Cloud Storage bucket | committed `models/` |
| Secrets | Secret Manager | `.env` / Render env vars |

Auth (Supabase Auth today) would move to the cloud IdP or a self-hosted OIDC
provider; that migration is a separate, documented step.

## Usage (for a real migration)

```bash
cd infra/terraform
terraform init        # configure a remote backend first (GCS bucket for state)
terraform plan  -var project_id=<gcp-project> -var region=australia-southeast1
terraform apply -var project_id=<gcp-project> -var region=australia-southeast1
```

Then push the ML image, run migrations against Cloud SQL, load secrets into Secret
Manager, and repoint the frontend at the Cloud Run URL. The blue/green deploy +
smoke-test + rollback flow is Master Plan Stage 8.2 (CI/CD).

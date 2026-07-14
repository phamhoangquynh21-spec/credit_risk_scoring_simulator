# Reference IaC — full single-cloud deployment of the credit-risk platform.
# NOT APPLIED. No backend/state, no credentials. See README.md.
#
# Provisions: Cloud Run (ML service) + Cloud SQL (Postgres) + Memorystore (Redis)
# + Cloud Storage (models/reports/LLM outputs) + Secret Manager (secrets).

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  # backend "gcs" { bucket = "<state-bucket>" prefix = "credit-risk" }  # configure before apply
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# --- Secrets ---------------------------------------------------------------
# Values are set out-of-band (never in Terraform state). One secret per key the
# ML service reads today: SUPABASE_* (or the self-hosted DB URL), ANTHROPIC_API_KEY.
resource "google_secret_manager_secret" "app" {
  for_each  = toset(["database-url", "jwt-secret", "anthropic-api-key"])
  secret_id = "credit-risk-${each.key}"
  replication { auto {} }
}

# --- Relational database (replaces Supabase Postgres) ----------------------
resource "google_sql_database_instance" "postgres" {
  name             = "credit-risk-pg"
  database_version = "POSTGRES_17"
  region           = var.region
  settings {
    tier              = var.db_tier
    availability_type = "ZONAL" # REGIONAL for production HA
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }
    ip_configuration { ipv4_enabled = false } # private IP only
  }
  deletion_protection = true
}

resource "google_sql_database" "app" {
  name     = "credit_risk"
  instance = google_sql_database_instance.postgres.name
}

# --- Cache / rate-limit / queue (R2 rate limiting) -------------------------
resource "google_redis_instance" "cache" {
  name           = "credit-risk-redis"
  memory_size_gb = var.redis_memory_gb
  region         = var.region
  tier           = "BASIC" # STANDARD_HA for production
}

# --- Object storage (models, reports, LLM outputs) -------------------------
resource "google_storage_bucket" "artifacts" {
  name                        = "${var.project_id}-credit-risk-artifacts"
  location                    = var.region
  uniform_bucket_level_access = true
  versioning { enabled = true }
  lifecycle_rule {
    condition { age = 90 } # raw LLM/bureau payloads: 90-day retention (see governance)
    action { type = "Delete" }
  }
}

# --- ML service container (replaces Render) --------------------------------
resource "google_cloud_run_v2_service" "ml" {
  name     = "credit-risk-ml"
  location = var.region
  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 4
    }
    containers {
      image = var.ml_image
      resources { limits = { cpu = "1", memory = "1Gi" } }
      ports { container_port = 8000 }
      # Secrets are injected as env vars from Secret Manager at deploy time.
      dynamic "env" {
        for_each = google_secret_manager_secret.app
        content {
          name = upper(replace(env.value.secret_id, "credit-risk-", ""))
          value_source { secret_key_ref { secret = env.value.secret_id version = "latest" } }
        }
      }
    }
  }
}

output "ml_service_url" {
  value       = google_cloud_run_v2_service.ml.uri
  description = "Cloud Run URL for the ML service (repoint the frontend here)."
}

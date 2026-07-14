# Reference IaC variables. See README.md — NOT applied.

variable "project_id" {
  type        = string
  description = "GCP project id to deploy into."
}

variable "region" {
  type        = string
  description = "GCP region (data residency matters for a credit platform)."
  default     = "australia-southeast1"
}

variable "ml_image" {
  type        = string
  description = "Container image for the FastAPI ML service (services/ml/Dockerfile)."
  default     = "gcr.io/PROJECT/credit-risk-ml:latest"
}

variable "db_tier" {
  type        = string
  description = "Cloud SQL machine tier."
  default     = "db-custom-1-3840" # 1 vCPU / 3.75 GB — small, resize for load
}

variable "redis_memory_gb" {
  type        = number
  description = "Memorystore capacity in GB."
  default     = 1
}

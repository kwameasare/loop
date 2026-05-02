variable "service_name" {
  description = "OVH Public Cloud project service name."
  type        = string
}

variable "name_prefix" {
  description = "Customer or environment prefix for OVH resources."
  type        = string
}

variable "loop_region" {
  description = "Loop abstract region, for labels and residency evidence."
  type        = string
}

variable "ovh_region" {
  description = "Concrete OVH region resolved from regions.yaml."
  type        = string
}

variable "node_flavor" {
  description = "OVH node flavor for the default Kubernetes node pool."
  type        = string
}

variable "postgres_plan" {
  description = "OVH Managed Postgres plan."
  type        = string
}

variable "redis_plan" {
  description = "OVH Managed Redis plan."
  type        = string
}

variable "allowed_cidrs" {
  description = "CIDR ranges allowed to reach managed databases."
  type        = list(string)
}

variable "object_storage_name" {
  description = "S3-compatible object storage bucket/container name."
  type        = string
}

variable "vault_chart_version" {
  description = "Pinned Vault Helm chart version for transit KMS."
  type        = string
  default     = "0.28.1"
}

variable "tags" {
  description = "Extra metadata labels rendered into Kubernetes resources."
  type        = map(string)
  default     = {}
}

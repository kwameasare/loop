variable "name_prefix" {
  description = "Customer or environment prefix for Hetzner resources."
  type        = string
}

variable "loop_region" {
  description = "Loop abstract region, for labels and residency evidence."
  type        = string
}

variable "hcloud_location" {
  description = "Concrete Hetzner location resolved from regions.yaml."
  type        = string
}

variable "ssh_key_ids" {
  description = "Hetzner SSH key IDs allowed onto provisioned nodes."
  type        = list(string)
}

variable "server_type" {
  description = "HCloud server type for Kubernetes nodes."
  type        = string
}

variable "postgres_plan" {
  description = "Hetzner managed Postgres plan."
  type        = string
}

variable "network_cidr" {
  description = "Private network CIDR for the Loop stack."
  type        = string
  default     = "10.42.0.0/16"
}

variable "minio_chart_version" {
  description = "Pinned MinIO Helm chart version."
  type        = string
  default     = "14.10.5"
}

variable "vault_chart_version" {
  description = "Pinned Vault Helm chart version for transit KMS."
  type        = string
  default     = "0.28.1"
}

variable "tags" {
  description = "Extra labels rendered into Kubernetes resources."
  type        = map(string)
  default     = {}
}

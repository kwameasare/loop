variable "name_prefix" {
  description = "Customer or environment prefix for Alibaba resources."
  type        = string
}

variable "loop_region" {
  description = "Loop abstract region, for labels and residency evidence."
  type        = string
}

variable "alibaba_region" {
  description = "Concrete Alibaba Cloud region resolved from regions.yaml."
  type        = string
}

variable "vpc_id" {
  description = "Existing VPC ID for the dedicated Loop stack."
  type        = string
}

variable "vswitch_ids" {
  description = "At least two VSwitch IDs spanning zones in the target region."
  type        = list(string)
}

variable "worker_instance_types" {
  description = "ACK worker node instance types."
  type        = list(string)
}

variable "worker_password" {
  description = "Initial ACK worker password supplied by the operator."
  type        = string
  sensitive   = true
}

variable "postgres_allowed_cidrs" {
  description = "CIDR ranges allowed to reach ApsaraDB PostgreSQL."
  type        = list(string)
}

variable "redis_allowed_cidrs" {
  description = "CIDR ranges allowed to reach ApsaraDB Redis."
  type        = list(string)
}

variable "oss_bucket_name" {
  description = "Globally unique OSS bucket name for Loop object storage."
  type        = string
}

variable "dcdn_domain" {
  description = "Customer edge hostname served by Alibaba DCDN."
  type        = string
}

variable "dcdn_origin" {
  description = "Origin hostname or SLB address behind DCDN."
  type        = string
}

variable "tags" {
  description = "Extra tags merged onto Alibaba resources."
  type        = map(string)
  default     = {}
}

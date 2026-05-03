variable "name_prefix" {
  description = "Customer or environment prefix for AWS resources."
  type        = string
}

variable "loop_region" {
  description = "Loop abstract region, for labels and residency evidence."
  type        = string
}

variable "aws_region" {
  description = "Concrete AWS region resolved from regions.yaml."
  type        = string
}

variable "vpc_id" {
  description = "Existing VPC ID for the dedicated Loop stack."
  type        = string
}

variable "subnet_ids" {
  description = "At least two private subnet IDs spanning AZs in the target region."
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "At least 2 subnet IDs across AZs are required for high availability."
  }
}

variable "cluster_security_group_ids" {
  description = "Security groups attached to the EKS control-plane ENIs."
  type        = list(string)
  default     = []
}

variable "eks_version" {
  description = "Kubernetes minor version for the EKS control plane."
  type        = string
  default     = "1.30"
}

variable "worker_instance_types" {
  description = "EC2 instance types for the EKS managed node group."
  type        = list(string)
  default     = ["m6i.xlarge"]
}

variable "worker_desired_size" {
  description = "Desired number of EKS worker nodes."
  type        = number
  default     = 3
}

variable "worker_min_size" {
  description = "Minimum number of EKS worker nodes."
  type        = number
  default     = 3
}

variable "worker_max_size" {
  description = "Maximum number of EKS worker nodes (autoscaler ceiling)."
  type        = number
  default     = 6
}

variable "postgres_allowed_cidrs" {
  description = "CIDR ranges allowed to reach RDS PostgreSQL on 5432/tcp."
  type        = list(string)
}

variable "postgres_instance_class" {
  description = "RDS instance class for PostgreSQL."
  type        = string
  default     = "db.m6i.large"
}

variable "postgres_storage_gb" {
  description = "Initial allocated storage for RDS PostgreSQL (GiB)."
  type        = number
  default     = 100
}

variable "postgres_max_storage_gb" {
  description = "Storage autoscaling ceiling for RDS PostgreSQL (GiB)."
  type        = number
  default     = 500
}

variable "postgres_master_password" {
  description = "RDS PostgreSQL master password supplied by the operator."
  type        = string
  sensitive   = true
}

variable "redis_allowed_cidrs" {
  description = "CIDR ranges allowed to reach ElastiCache Redis on 6379/tcp."
  type        = list(string)
}

variable "redis_node_type" {
  description = "ElastiCache node type for Redis."
  type        = string
  default     = "cache.r7g.large"
}

variable "s3_bucket_name" {
  description = "Globally unique S3 bucket name for Loop object storage."
  type        = string
}

variable "enable_cloudfront" {
  description = "Provision a CloudFront distribution in front of cp-api."
  type        = bool
  default     = false
}

variable "cloudfront_origin_domain" {
  description = "Origin hostname (ALB/NLB DNS) behind CloudFront. Required when enable_cloudfront=true."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Extra tags merged onto AWS resources."
  type        = map(string)
  default     = {}
}

# Staging environment — AWS us-east-2 (S904).
#
# Apply on top of an existing VPC + private subnets owned by the
# operator. Real apply is blocked until S002 (cloud accounts) lands;
# until then this file passes `terraform validate` + `tflint` so the
# module + env wiring is locked.
#
# Apply (after S002):
#
#   cd infra/terraform/envs/staging-aws-us-east-2
#   terraform init
#   terraform plan \
#     -var "vpc_id=vpc-xxxxxxxx" \
#     -var 'subnet_ids=["subnet-aaa","subnet-bbb"]' \
#     -var 'postgres_allowed_cidrs=["10.0.0.0/16"]' \
#     -var 'redis_allowed_cidrs=["10.0.0.0/16"]' \
#     -var 's3_bucket_name=loop-staging-na-east-objects' \
#     -var 'postgres_master_password=<from-vault>'
#   terraform apply

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.66"
    }
  }
}

variable "loop_region" {
  description = "Loop abstract region."
  type        = string
  default     = "na-east"

  validation {
    condition     = var.loop_region == "na-east"
    error_message = "staging-aws-us-east-2 only deploys the na-east abstract region."
  }
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "postgres_allowed_cidrs" {
  type = list(string)
}

variable "redis_allowed_cidrs" {
  type = list(string)
}

variable "s3_bucket_name" {
  type = string
}

variable "postgres_master_password" {
  description = "RDS PostgreSQL master password supplied by the operator."
  type        = string
  sensitive   = true
}

variable "worker_instance_types" {
  type    = list(string)
  default = ["m6i.xlarge"]
}

variable "enable_cloudfront" {
  type    = bool
  default = false
}

variable "cloudfront_origin_domain" {
  type    = string
  default = ""
}

locals {
  regions    = yamldecode(file("${path.module}/../../regions.yaml")).regions
  region     = local.regions[var.loop_region]
  aws_region = local.region.concrete.aws
}

provider "aws" {
  region = local.aws_region
}

module "loop_aws" {
  source                   = "../../modules/aws-loop-stack"
  name_prefix              = "loop-staging-${var.loop_region}"
  loop_region              = var.loop_region
  aws_region               = local.aws_region
  vpc_id                   = var.vpc_id
  subnet_ids               = var.subnet_ids
  postgres_allowed_cidrs   = var.postgres_allowed_cidrs
  redis_allowed_cidrs      = var.redis_allowed_cidrs
  s3_bucket_name           = var.s3_bucket_name
  postgres_master_password = var.postgres_master_password
  worker_instance_types    = var.worker_instance_types
  enable_cloudfront        = var.enable_cloudfront
  cloudfront_origin_domain = var.cloudfront_origin_domain

  tags = {
    residency = local.region.residency
    region    = var.loop_region
    env       = "staging"
  }
}

output "eks_cluster_endpoint" {
  description = "Kubernetes API server endpoint."
  value       = module.loop_aws.eks_cluster_endpoint
}

output "postgres_endpoint" {
  description = "RDS PostgreSQL connection endpoint."
  value       = module.loop_aws.postgres_endpoint
}

output "redis_primary_endpoint" {
  description = "ElastiCache Redis primary endpoint."
  value       = module.loop_aws.redis_primary_endpoint
}

output "s3_bucket" {
  description = "Loop object-store S3 bucket name."
  value       = module.loop_aws.s3_bucket
}

output "kms_key_arn" {
  description = "KMS key ARN for envelope encryption + S3 SSE-KMS."
  value       = module.loop_aws.kms_key_arn
}

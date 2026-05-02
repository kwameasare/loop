terraform {
  required_version = ">= 1.6.0"

  required_providers {
    alicloud = {
      source  = "aliyun/alicloud"
      version = "~> 1.230"
    }
  }
}

variable "loop_region" {
  description = "Loop abstract region."
  type        = string
  default     = "cn-shanghai"

  validation {
    condition     = var.loop_region == "cn-shanghai"
    error_message = "prod-alibaba-cn-shanghai only deploys the cn-shanghai abstract region."
  }
}

variable "vpc_id" {
  type        = string
}

variable "vswitch_ids" {
  type        = list(string)
}

variable "worker_instance_types" {
  type        = list(string)
}

variable "worker_password" {
  description = "Initial ACK worker password supplied by the operator."
  type        = string
  sensitive   = true
}

variable "postgres_allowed_cidrs" {
  type        = list(string)
}

variable "redis_allowed_cidrs" {
  type        = list(string)
}

variable "oss_bucket_name" {
  type        = string
}

variable "dcdn_domain" {
  type        = string
}

variable "dcdn_origin" {
  type        = string
}

locals {
  regions        = yamldecode(file("${path.module}/../../regions.yaml")).regions
  region         = local.regions[var.loop_region]
  alibaba_region = local.region.concrete.alibaba
}

provider "alicloud" {
  region = local.alibaba_region
}

module "loop_alibaba" {
  source                 = "../../modules/alibaba-loop-stack"
  name_prefix            = "loop-${var.loop_region}"
  loop_region            = var.loop_region
  alibaba_region         = local.alibaba_region
  vpc_id                 = var.vpc_id
  vswitch_ids            = var.vswitch_ids
  worker_instance_types  = var.worker_instance_types
  worker_password        = var.worker_password
  postgres_allowed_cidrs = var.postgres_allowed_cidrs
  redis_allowed_cidrs    = var.redis_allowed_cidrs
  oss_bucket_name        = var.oss_bucket_name
  dcdn_domain            = var.dcdn_domain
  dcdn_origin            = var.dcdn_origin

  tags = {
    residency = local.region.residency
    region    = var.loop_region
  }
}

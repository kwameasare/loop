terraform {
  required_version = ">= 1.6.0"
  required_providers {
    ovh = {
      source  = "ovh/ovh"
      version = "~> 0.47"
    }
  }
}

variable "loop_region" {
  description = "Loop abstract region."
  type        = string
  default     = "eu-sovereign"
  validation {
    condition     = var.loop_region == "eu-sovereign"
    error_message = "prod-ovh-eu-sovereign only deploys the eu-sovereign region."
  }
}

variable "service_name" {
  type = string
}
variable "node_flavor" {
  type = string
}
variable "postgres_plan" {
  type = string
}
variable "redis_plan" {
  type = string
}
variable "allowed_cidrs" {
  type = list(string)
}
variable "object_storage_name" {
  type = string
}

locals {
  regions    = yamldecode(file("${path.module}/../../regions.yaml")).regions
  region     = local.regions[var.loop_region]
  ovh_region = local.region.concrete.ovh
}

provider "ovh" {
  endpoint = "ovh-eu"
}

module "loop_ovh" {
  source              = "../../modules/ovh-loop-stack"
  service_name        = var.service_name
  name_prefix         = "loop-${var.loop_region}"
  loop_region         = var.loop_region
  ovh_region          = local.ovh_region
  node_flavor         = var.node_flavor
  postgres_plan       = var.postgres_plan
  redis_plan          = var.redis_plan
  allowed_cidrs       = var.allowed_cidrs
  object_storage_name = var.object_storage_name
  tags = {
    residency = local.region.residency
    region    = var.loop_region
  }
}

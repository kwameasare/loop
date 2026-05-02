terraform {
  required_version = ">= 1.6.0"
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.49"
    }
  }
}

variable "loop_region" {
  description = "Loop abstract region."
  type        = string
  default     = "eu-cost"
  validation {
    condition     = var.loop_region == "eu-cost"
    error_message = "prod-hetzner-eu-central only deploys the eu-cost region."
  }
}

variable "hcloud_token" {
  type      = string
  sensitive = true
}
variable "ssh_key_ids" {
  type = list(string)
}
variable "server_type" {
  type = string
}
variable "postgres_plan" {
  type = string
}

locals {
  regions         = yamldecode(file("${path.module}/../../regions.yaml")).regions
  region          = local.regions[var.loop_region]
  hcloud_location = local.region.concrete.hetzner
}

provider "hcloud" {
  token = var.hcloud_token
}

module "loop_hetzner" {
  source          = "../../modules/hetzner-loop-stack"
  name_prefix     = "loop-${var.loop_region}"
  loop_region     = var.loop_region
  hcloud_location = local.hcloud_location
  ssh_key_ids     = var.ssh_key_ids
  server_type     = var.server_type
  postgres_plan   = var.postgres_plan
  tags = {
    residency = local.region.residency
    region    = var.loop_region
  }
}

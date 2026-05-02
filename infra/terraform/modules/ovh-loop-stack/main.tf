terraform {
  required_version = ">= 1.6.0"
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.29"
    }
    ovh = {
      source  = "ovh/ovh"
      version = "~> 0.47"
    }
  }
}
locals {
  labels = merge(var.tags, {
    "app.kubernetes.io/part-of" = "loop"
    "loop.ai/cloud"             = "ovh"
    "loop.ai/region"            = var.loop_region
    "loop.ai/provider-region"   = var.ovh_region
  })
}
resource "ovh_cloud_project_kube" "cluster" {
  service_name = var.service_name
  name         = "${var.name_prefix}-k8s"
  region       = var.ovh_region
}
resource "ovh_cloud_project_kube_nodepool" "default" {
  service_name  = var.service_name
  kube_id       = ovh_cloud_project_kube.cluster.id
  name          = "${var.name_prefix}-pool"
  flavor_name   = var.node_flavor
  desired_nodes = 3
  min_nodes     = 3
  max_nodes     = 12
}
resource "ovh_cloud_project_database" "postgres" {
  service_name = var.service_name
  description  = "${var.name_prefix}-postgres"
  engine       = "postgresql"
  version      = "16"
  plan         = var.postgres_plan
  nodes {
    region = var.ovh_region
  }
  ip_restrictions = var.allowed_cidrs
}
resource "ovh_cloud_project_database" "redis" {
  service_name = var.service_name
  description  = "${var.name_prefix}-redis"
  engine       = "redis"
  version      = "7"
  plan         = var.redis_plan
  nodes {
    region = var.ovh_region
  }
  ip_restrictions = var.allowed_cidrs
}
resource "ovh_cloud_project_region_storage" "objects" {
  service_name = var.service_name
  region_name  = var.ovh_region
  name         = var.object_storage_name
  versioning   = true
}
resource "kubernetes_namespace" "vault" {
  metadata {
    name   = "${var.name_prefix}-vault"
    labels = local.labels
  }
}
resource "helm_release" "vault" {
  name       = "vault"
  namespace  = kubernetes_namespace.vault.metadata[0].name
  repository = "https://helm.releases.hashicorp.com"
  chart      = "vault"
  version    = var.vault_chart_version
  wait       = true
  values = [yamlencode({
    server = { ha = { enabled = true, replicas = 3 } }
    injector = { enabled = false }
  })]
}

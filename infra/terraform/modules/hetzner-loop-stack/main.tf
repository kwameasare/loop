terraform {
  required_version = ">= 1.6.0"
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.49"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.29"
    }
  }
}

locals {
  labels = merge(var.tags, {
    "app.kubernetes.io/part-of" = "loop"
    "loop.ai/cloud"             = "hetzner"
    "loop.ai/region"            = var.loop_region
    "loop.ai/provider-region"   = var.hcloud_location
  })
}

resource "hcloud_network" "loop" {
  name     = "${var.name_prefix}-net"
  ip_range = var.network_cidr
}
resource "hcloud_network_subnet" "loop" {
  network_id   = hcloud_network.loop.id
  type         = "cloud"
  network_zone = "eu-central"
  ip_range     = cidrsubnet(var.network_cidr, 8, 1)
}
resource "hcloud_server" "control_plane" {
  name        = "${var.name_prefix}-cp-1"
  image       = "ubuntu-24.04"
  server_type = var.server_type
  location    = var.hcloud_location
  ssh_keys    = var.ssh_key_ids
  network {
    network_id = hcloud_network.loop.id
  }
  labels = local.labels
}
resource "hcloud_server" "worker" {
  count       = 3
  name        = "${var.name_prefix}-worker-${count.index + 1}"
  image       = "ubuntu-24.04"
  server_type = var.server_type
  location    = var.hcloud_location
  ssh_keys    = var.ssh_key_ids
  network {
    network_id = hcloud_network.loop.id
  }
  labels = local.labels
}
resource "hcloud_managed_database" "postgres" {
  name     = "${var.name_prefix}-postgres"
  engine   = "postgresql"
  version  = "16"
  plan     = var.postgres_plan
  location = var.hcloud_location
  labels   = local.labels
}
resource "kubernetes_namespace" "platform" {
  metadata {
    name   = "${var.name_prefix}-platform"
    labels = local.labels
  }
}
resource "helm_release" "minio" {
  name       = "minio"
  namespace  = kubernetes_namespace.platform.metadata[0].name
  repository = "https://charts.bitnami.com/bitnami"
  chart      = "minio"
  version    = var.minio_chart_version
  wait       = true
}
resource "helm_release" "vault" {
  name       = "vault"
  namespace  = kubernetes_namespace.platform.metadata[0].name
  repository = "https://helm.releases.hashicorp.com"
  chart      = "vault"
  version    = var.vault_chart_version
  wait       = true
}

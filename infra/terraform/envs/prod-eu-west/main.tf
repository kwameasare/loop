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
  }
}

variable "kubeconfig_path" {
  description = "Path to kubeconfig for the pre-provisioned EU cluster."
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Kube context for the EU cluster."
  type        = string
}

variable "namespace" {
  description = "Namespace for the EU-resident Loop data plane."
  type        = string
  default     = "loop-eu-west"
}

variable "region" {
  description = "Loop abstract region."
  type        = string
  default     = "eu-west"

  validation {
    condition     = var.region == "eu-west"
    error_message = "prod-eu-west only deploys the eu-west abstract region."
  }
}

locals {
  loop_chart_dir = "${path.module}/../../../helm/loop"
  values_file    = "${local.loop_chart_dir}/values-eu-west.yaml"
}

provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kube_context
}

provider "helm" {
  kubernetes {
    config_path    = var.kubeconfig_path
    config_context = var.kube_context
  }
}

resource "kubernetes_namespace" "loop" {
  metadata {
    name = var.namespace
    labels = {
      app.kubernetes.io/part-of = "loop"
      region                    = var.region
      residency                 = "eu"
    }
  }
}

resource "helm_release" "loop" {
  name             = "loop"
  namespace        = kubernetes_namespace.loop.metadata[0].name
  create_namespace = false
  chart            = local.loop_chart_dir
  values           = [file(local.values_file)]

  timeout = 900
  wait    = true
}

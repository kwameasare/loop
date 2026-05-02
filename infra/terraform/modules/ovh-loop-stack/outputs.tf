output "kube_cluster_id" {
  description = "OVH Managed Kubernetes cluster ID."
  value       = ovh_cloud_project_kube.cluster.id
}

output "postgres_id" {
  description = "OVH Managed PostgreSQL service ID."
  value       = ovh_cloud_project_database.postgres.id
}

output "redis_id" {
  description = "OVH Managed Redis service ID."
  value       = ovh_cloud_project_database.redis.id
}

output "object_storage_name" {
  description = "S3-compatible OVH object storage name."
  value       = ovh_cloud_project_region_storage.objects.name
}

output "vault_namespace" {
  description = "Namespace containing Vault Transit KMS."
  value       = kubernetes_namespace.vault.metadata[0].name
}

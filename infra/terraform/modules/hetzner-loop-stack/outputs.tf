output "control_plane_id" {
  description = "Primary HCloud control-plane server ID."
  value       = hcloud_server.control_plane.id
}

output "worker_ids" {
  description = "HCloud worker server IDs."
  value       = hcloud_server.worker[*].id
}

output "postgres_id" {
  description = "Hetzner managed PostgreSQL service ID."
  value       = hcloud_managed_database.postgres.id
}

output "platform_namespace" {
  description = "Namespace containing MinIO and Vault Transit."
  value       = kubernetes_namespace.platform.metadata[0].name
}

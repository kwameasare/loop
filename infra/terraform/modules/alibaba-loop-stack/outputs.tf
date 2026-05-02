output "ack_cluster_id" {
  description = "ACK cluster ID hosting the Loop stack."
  value       = alicloud_cs_managed_kubernetes.ack.id
}

output "postgres_connection_string" {
  description = "ApsaraDB PostgreSQL connection endpoint."
  value       = alicloud_db_instance.postgres.connection_string
}

output "redis_connection_domain" {
  description = "ApsaraDB Redis connection endpoint."
  value       = alicloud_kvstore_instance.redis.connection_domain
}

output "oss_bucket" {
  description = "OSS bucket used by Loop object storage."
  value       = alicloud_oss_bucket.objects.bucket
}

output "kms_key_id" {
  description = "KMS key ID for envelope encryption."
  value       = alicloud_kms_key.loop.id
}

output "dcdn_domain" {
  description = "DCDN edge domain fronting the Loop stack."
  value       = alicloud_dcdn_domain.edge.domain_name
}

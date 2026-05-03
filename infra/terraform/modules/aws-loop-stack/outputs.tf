output "eks_cluster_id" {
  description = "EKS cluster ID hosting the Loop stack."
  value       = aws_eks_cluster.loop.id
}

output "eks_cluster_endpoint" {
  description = "Kubernetes API server endpoint for the EKS cluster."
  value       = aws_eks_cluster.loop.endpoint
}

output "eks_cluster_ca_data" {
  description = "Cluster CA certificate data, base64-encoded."
  value       = aws_eks_cluster.loop.certificate_authority[0].data
  sensitive   = true
}

output "eks_node_role_arn" {
  description = "IAM role ARN attached to EKS worker nodes."
  value       = aws_iam_role.eks_node.arn
}

output "postgres_endpoint" {
  description = "RDS PostgreSQL connection endpoint."
  value       = aws_db_instance.postgres.endpoint
}

output "postgres_address" {
  description = "RDS PostgreSQL hostname (without port)."
  value       = aws_db_instance.postgres.address
}

output "redis_primary_endpoint" {
  description = "ElastiCache Redis primary endpoint."
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "s3_bucket" {
  description = "S3 bucket used by Loop object storage."
  value       = aws_s3_bucket.objects.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the Loop object-store bucket."
  value       = aws_s3_bucket.objects.arn
}

output "kms_key_id" {
  description = "KMS key ID for envelope encryption + S3 SSE-KMS."
  value       = aws_kms_key.loop.key_id
}

output "kms_key_arn" {
  description = "KMS key ARN for envelope encryption + S3 SSE-KMS."
  value       = aws_kms_key.loop.arn
}

output "kms_key_alias" {
  description = "Human-friendly KMS alias."
  value       = aws_kms_alias.loop.name
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (when enabled)."
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.edge[0].domain_name : null
}

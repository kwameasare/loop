# AWS Loop stack module (S904).
#
# Provisions the managed services Loop's Helm chart depends on, in a
# single region inside a customer-supplied VPC:
#   - KMS key (envelope encryption + S3 SSE-KMS)
#   - S3 bucket (object store with SSE-KMS)
#   - EKS managed cluster (control plane + workers)
#   - RDS PostgreSQL 16
#   - ElastiCache Redis 7
#   - CloudFront distribution (edge, optional)
#
# Mirrors the alibaba-loop-stack / hetzner-loop-stack / ovh-loop-stack
# modules so the cloud-portability matrix stays honest. Validation runs
# in CI via `terraform validate` + `tflint`; the module is intentionally
# `terraform apply`-blocked until S002 (cloud accounts) lands and the
# operator provisions the underlying VPC/subnets.
#
# Companion env: infra/terraform/envs/staging-aws-us-east-2/main.tf

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.66"
    }
  }
}

locals {
  common_tags = merge(var.tags, {
    app         = "loop"
    loop_region = var.loop_region
    region      = var.aws_region
    cloud       = "aws"
  })
}

# ──────────────────────────────────────────────────────────────────────
# KMS — envelope encryption key
# ──────────────────────────────────────────────────────────────────────

resource "aws_kms_key" "loop" {
  description             = "${var.name_prefix} Loop envelope encryption key"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  tags                    = local.common_tags
}

resource "aws_kms_alias" "loop" {
  name          = "alias/${var.name_prefix}-loop"
  target_key_id = aws_kms_key.loop.key_id
}

# ──────────────────────────────────────────────────────────────────────
# S3 — object storage with SSE-KMS
# ──────────────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "objects" {
  bucket = var.s3_bucket_name
  tags   = local.common_tags
}

resource "aws_s3_bucket_server_side_encryption_configuration" "objects" {
  bucket = aws_s3_bucket.objects.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.loop.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "objects" {
  bucket = aws_s3_bucket.objects.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "objects" {
  bucket = aws_s3_bucket.objects.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "objects" {
  bucket = aws_s3_bucket.objects.id

  rule {
    id     = "expire-noncurrent"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# ──────────────────────────────────────────────────────────────────────
# EKS — managed Kubernetes for runtime + cp-api + gateway + kb-engine
# ──────────────────────────────────────────────────────────────────────

resource "aws_iam_role" "eks_cluster" {
  name = "${var.name_prefix}-eks-cluster"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_eks_cluster" "loop" {
  name     = "${var.name_prefix}-eks"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = var.eks_version

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = false
    security_group_ids      = var.cluster_security_group_ids
  }

  encryption_config {
    provider {
      key_arn = aws_kms_key.loop.arn
    }
    resources = ["secrets"]
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy_attachment.eks_cluster_policy]
}

resource "aws_iam_role" "eks_node" {
  name = "${var.name_prefix}-eks-node"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "eks_node_worker" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node.name
}

resource "aws_iam_role_policy_attachment" "eks_node_cni" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node.name
}

resource "aws_iam_role_policy_attachment" "eks_node_ecr" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node.name
}

resource "aws_eks_node_group" "workers" {
  cluster_name    = aws_eks_cluster.loop.name
  node_group_name = "${var.name_prefix}-workers"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = var.subnet_ids
  instance_types  = var.worker_instance_types

  scaling_config {
    desired_size = var.worker_desired_size
    min_size     = var.worker_min_size
    max_size     = var.worker_max_size
  }

  update_config {
    max_unavailable = 1
  }

  tags = local.common_tags

  depends_on = [
    aws_iam_role_policy_attachment.eks_node_worker,
    aws_iam_role_policy_attachment.eks_node_cni,
    aws_iam_role_policy_attachment.eks_node_ecr,
  ]
}

# ──────────────────────────────────────────────────────────────────────
# RDS PostgreSQL — primary metadata DB
# ──────────────────────────────────────────────────────────────────────

resource "aws_db_subnet_group" "postgres" {
  name       = "${var.name_prefix}-postgres"
  subnet_ids = var.subnet_ids
  tags       = local.common_tags
}

resource "aws_security_group" "postgres" {
  name        = "${var.name_prefix}-postgres"
  description = "Loop Postgres ingress"
  vpc_id      = var.vpc_id
  tags        = local.common_tags

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.postgres_allowed_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "postgres" {
  identifier             = "${var.name_prefix}-postgres"
  engine                 = "postgres"
  engine_version         = "16.4"
  instance_class         = var.postgres_instance_class
  allocated_storage      = var.postgres_storage_gb
  max_allocated_storage  = var.postgres_max_storage_gb
  storage_type           = "gp3"
  storage_encrypted      = true
  kms_key_id             = aws_kms_key.loop.arn
  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.postgres.id]
  username               = "loop"
  password               = var.postgres_master_password
  db_name                = "loop"
  multi_az               = true
  publicly_accessible    = false
  skip_final_snapshot    = false
  final_snapshot_identifier = "${var.name_prefix}-postgres-final"
  deletion_protection    = true
  backup_retention_period = 14
  tags                   = local.common_tags
}

# ──────────────────────────────────────────────────────────────────────
# ElastiCache Redis — session memory + rate-limit + idempotency cache
# ──────────────────────────────────────────────────────────────────────

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.name_prefix}-redis"
  subnet_ids = var.subnet_ids
  tags       = local.common_tags
}

resource "aws_security_group" "redis" {
  name        = "${var.name_prefix}-redis"
  description = "Loop Redis ingress"
  vpc_id      = var.vpc_id
  tags        = local.common_tags

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = var.redis_allowed_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${var.name_prefix}-redis"
  description                = "Loop Redis cache"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = var.redis_node_type
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  port                       = 6379
  parameter_group_name       = "default.redis7"
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                 = aws_kms_key.loop.arn
  tags                       = local.common_tags
}

# ──────────────────────────────────────────────────────────────────────
# CloudFront — edge in front of the cp-api ingress (optional)
# ──────────────────────────────────────────────────────────────────────

resource "aws_cloudfront_distribution" "edge" {
  count = var.enable_cloudfront ? 1 : 0

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.name_prefix} Loop edge"
  default_root_object = ""
  price_class         = "PriceClass_100"

  origin {
    domain_name = var.cloudfront_origin_domain
    origin_id   = "loop-cp-api-origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "loop-cp-api-origin"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Accept", "Content-Type"]

      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
      locations        = []
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = local.common_tags
}

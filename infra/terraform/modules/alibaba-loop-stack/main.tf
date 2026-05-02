terraform {
  required_version = ">= 1.6.0"
  required_providers {
    alicloud = {
      source  = "aliyun/alicloud"
      version = "~> 1.230"
    }
  }
}
locals {
  common_tags = merge(var.tags, {
    app         = "loop"
    loop_region = var.loop_region
    region      = var.alibaba_region
    cloud       = "alibaba"
  })
}
resource "alicloud_kms_key" "loop" {
  description            = "${var.name_prefix} Loop envelope encryption key"
  key_usage              = "ENCRYPT/DECRYPT"
  pending_window_in_days = 7
  tags                   = local.common_tags
}

resource "alicloud_oss_bucket" "objects" {
  bucket          = var.oss_bucket_name
  acl             = "private"
  redundancy_type = "ZRS"
  tags            = local.common_tags
}

resource "alicloud_oss_bucket_server_side_encryption_rule" "objects" {
  bucket            = alicloud_oss_bucket.objects.bucket
  sse_algorithm     = "KMS"
  kms_master_key_id = alicloud_kms_key.loop.id
}

resource "alicloud_cs_managed_kubernetes" "ack" {
  name                  = "${var.name_prefix}-ack"
  cluster_spec          = "ack.pro.small"
  vpc_id                = var.vpc_id
  worker_vswitch_ids    = var.vswitch_ids
  worker_instance_types = var.worker_instance_types
  worker_number         = 3
  worker_disk_category  = "cloud_essd"
  worker_disk_size      = 120
  password              = var.worker_password
  pod_cidr              = "10.244.0.0/16"
  service_cidr          = "172.21.0.0/20"
  slb_internet_enabled  = false
  new_nat_gateway       = false
  deletion_protection   = true
  tags                  = local.common_tags
}

resource "alicloud_db_instance" "postgres" {
  engine                   = "PostgreSQL"
  engine_version           = "16.0"
  instance_type            = "pg.n2.2c.2m"
  instance_storage         = 100
  db_instance_storage_type = "cloud_essd"
  vswitch_id               = var.vswitch_ids[0]
  security_ips             = var.postgres_allowed_cidrs
  instance_name            = "${var.name_prefix}-postgres"
  tags                     = local.common_tags
}

resource "alicloud_kvstore_instance" "redis" {
  instance_name  = "${var.name_prefix}-redis"
  instance_class = "redis.master.small.default"
  instance_type  = "Redis"
  engine_version = "7.0"
  vswitch_id     = var.vswitch_ids[0]
  security_ips   = var.redis_allowed_cidrs
  tags           = local.common_tags
}

resource "alicloud_dcdn_domain" "edge" {
  domain_name = var.dcdn_domain
  scope       = "overseas"

  sources {
    content  = var.dcdn_origin
    type     = "domain"
    port     = 443
    priority = "20"
    weight   = "10"
  }
}

# Cloud portability proof

Loop publishes this page so operators can see which deployment primitives are
portable across the supported clouds and whether the nightly smoke is still
green.

The matrix tracks the customer-visible capability, not the vendor product
name. Implementation details live in
[CLOUD_PORTABILITY.md](../loop_implementation/architecture/CLOUD_PORTABILITY.md).

## Capability matrix

| Capability | AWS | Azure | GCP | Alibaba Cloud | OVHcloud | Hetzner | Self-host |
|------------|-----|-------|-----|---------------|----------|---------|-----------|
| Kubernetes deploy | EKS | AKS | GKE | ACK | Managed Kubernetes | HCloud + k3s | k3s / kubeadm |
| Postgres | RDS PostgreSQL | Azure PostgreSQL Flexible | Cloud SQL PostgreSQL | ApsaraDB RDS | Managed Postgres | Managed Postgres | CloudNativePG |
| Redis | ElastiCache | Azure Cache for Redis | Memorystore | Tair / ApsaraDB Redis | Managed Redis | Redis operator | Redis operator |
| Object storage | S3 | Blob Storage | Cloud Storage S3 interop | OSS S3 interop | S3-compatible object store | MinIO | MinIO |
| KMS | AWS KMS | Key Vault | Cloud KMS | Alibaba KMS | Vault Transit | Vault Transit | Vault Transit |
| Secrets | Secrets Manager | Key Vault Secrets | Secret Manager | KMS Secret | Vault | Vault | Vault |
| Edge / CDN / WAF | CloudFront + WAF | Front Door + WAF | Cloud CDN + Armor | DCDN + WAF | Cloudflare | Cloudflare | Cloudflare / Envoy |
| Email | SES | Communication Services | partner SMTP | DirectMail | SMTP relay | SMTP relay | SMTP relay |
| Telemetry storage | ClickHouse on k8s | ClickHouse on k8s | ClickHouse on k8s | ClickHouse on k8s | ClickHouse on k8s | ClickHouse on k8s | ClickHouse Helm |

## Nightly smoke marks

`cross-cloud-smoke` appends one row per checked cloud on its nightly schedule.
GREEN means the Helm install and first-turn runtime smoke passed for that
cloud label. RED means the job produced a failed, skipped, cancelled, or timed
out mark and paged on-call from the same workflow.

| Checked at (UTC) | Cloud | Region | Mark | Run | Commit |
|------------------|-------|--------|------|-----|--------|
<!-- CLOUD_PROOF_HISTORY:BEGIN -->
| 2026-05-30T06:29:07Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26676884375) | `881bf68f33da` |
| 2026-05-30T06:29:06Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26676884375) | `881bf68f33da` |
| 2026-05-30T06:29:05Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26676884375) | `881bf68f33da` |
| 2026-05-31T06:42:26Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26705618997) | `c3008817da0d` |
| 2026-05-31T06:42:33Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26705618997) | `c3008817da0d` |
| 2026-05-31T06:42:26Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26705618997) | `c3008817da0d` |
| 2026-06-01T07:00:34Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26740119483) | `1e330b3b3f9c` |
| 2026-06-01T07:00:35Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26740119483) | `1e330b3b3f9c` |
| 2026-06-01T07:00:36Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26740119483) | `1e330b3b3f9c` |
| 2026-06-02T06:55:17Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26803683912) | `f0db07278ea9` |
| 2026-06-02T06:55:11Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26803683912) | `f0db07278ea9` |
| 2026-06-02T06:55:10Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26803683912) | `f0db07278ea9` |
| 2026-06-03T06:59:47Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26868952147) | `45490fd5adf7` |
| 2026-06-03T06:59:43Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26868952147) | `45490fd5adf7` |
| 2026-06-03T06:59:42Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26868952147) | `45490fd5adf7` |
| 2026-06-04T06:55:15Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26935992037) | `1daeee7f7075` |
| 2026-06-04T06:55:08Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26935992037) | `1daeee7f7075` |
| 2026-06-04T06:55:07Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26935992037) | `1daeee7f7075` |
| 2026-06-05T06:47:46Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27000037541) | `ed23ed2b11d3` |
| 2026-06-05T06:47:51Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27000037541) | `ed23ed2b11d3` |
| 2026-06-05T06:47:56Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27000037541) | `ed23ed2b11d3` |
| 2026-06-06T06:30:54Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27055033921) | `c2fd3cadb7bd` |
| 2026-06-06T06:30:47Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27055033921) | `c2fd3cadb7bd` |
| 2026-06-06T06:30:52Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27055033921) | `c2fd3cadb7bd` |
| 2026-06-07T06:47:22Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27085287141) | `592e4e959e4d` |
| 2026-06-07T06:47:14Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27085287141) | `592e4e959e4d` |
| 2026-06-07T06:47:15Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27085287141) | `592e4e959e4d` |
| 2026-06-08T06:57:46Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27121144312) | `800b95438a20` |
| 2026-06-08T06:56:48Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27121144312) | `800b95438a20` |
| 2026-06-08T06:56:59Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27121144312) | `800b95438a20` |
| 2026-06-09T06:36:44Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27188475600) | `c5ee69ea7c79` |
| 2026-06-09T06:36:55Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27188475600) | `c5ee69ea7c79` |
| 2026-06-09T06:36:46Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27188475600) | `c5ee69ea7c79` |
| 2026-06-10T06:47:39Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27258502061) | `ef558f1af1f5` |
| 2026-06-10T06:47:34Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27258502061) | `ef558f1af1f5` |
| 2026-06-10T06:47:45Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27258502061) | `ef558f1af1f5` |
| 2026-06-11T06:59:22Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27329658057) | `22f2198542f3` |
| 2026-06-11T06:59:18Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27329658057) | `22f2198542f3` |
| 2026-06-11T06:59:28Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27329658057) | `22f2198542f3` |
| 2026-06-12T06:55:04Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27399892030) | `d9ae07e1b146` |
| 2026-06-12T06:55:04Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27399892030) | `d9ae07e1b146` |
| 2026-06-12T06:55:00Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27399892030) | `d9ae07e1b146` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

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
| 2026-07-18T06:01:16Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29633235982) | `20a79c46325b` |
| 2026-07-18T06:01:15Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29633235982) | `20a79c46325b` |
| 2026-07-18T06:01:13Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29633235982) | `20a79c46325b` |
| 2026-07-19T06:14:06Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29676085904) | `b0b143e2f269` |
| 2026-07-19T06:14:10Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29676085904) | `b0b143e2f269` |
| 2026-07-19T06:14:12Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29676085904) | `b0b143e2f269` |
| 2026-07-20T06:25:05Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29721577453) | `679fffccebca` |
| 2026-07-20T06:24:58Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29721577453) | `679fffccebca` |
| 2026-07-20T06:25:01Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29721577453) | `679fffccebca` |
| 2026-07-21T06:13:37Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29806324846) | `58f7a32d38bf` |
| 2026-07-21T06:13:37Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29806324846) | `58f7a32d38bf` |
| 2026-07-21T06:13:40Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29806324846) | `58f7a32d38bf` |
| 2026-07-22T06:12:30Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29895991478) | `5ca1f22b29c7` |
| 2026-07-22T06:12:37Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29895991478) | `5ca1f22b29c7` |
| 2026-07-22T06:12:34Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29895991478) | `5ca1f22b29c7` |
| 2026-07-23T06:15:45Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29984457474) | `bb8ce664e754` |
| 2026-07-23T06:15:45Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29984457474) | `bb8ce664e754` |
| 2026-07-23T06:15:48Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29984457474) | `bb8ce664e754` |
| 2026-07-24T06:11:38Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30071502863) | `87a6b06a279c` |
| 2026-07-24T06:11:34Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30071502863) | `87a6b06a279c` |
| 2026-07-24T06:11:32Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30071502863) | `87a6b06a279c` |
| 2026-07-25T06:06:48Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30146911632) | `45885c35d795` |
| 2026-07-25T06:06:38Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30146911632) | `45885c35d795` |
| 2026-07-25T06:06:41Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30146911632) | `45885c35d795` |
| 2026-07-26T06:18:41Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30190808755) | `387e5f433e76` |
| 2026-07-26T06:18:59Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30190808755) | `387e5f433e76` |
| 2026-07-26T06:18:51Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30190808755) | `387e5f433e76` |
| 2026-07-27T06:30:34Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30242919894) | `64d09a43e127` |
| 2026-07-27T06:30:33Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30242919894) | `64d09a43e127` |
| 2026-07-27T06:30:44Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30242919894) | `64d09a43e127` |
| 2026-07-28T06:12:04Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30333958539) | `c5c376cc42d0` |
| 2026-07-28T06:12:04Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30333958539) | `c5c376cc42d0` |
| 2026-07-28T06:11:50Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30333958539) | `c5c376cc42d0` |
| 2026-07-29T06:14:40Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30427491324) | `cc0bfa42caf5` |
| 2026-07-29T06:14:39Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30427491324) | `cc0bfa42caf5` |
| 2026-07-29T06:14:36Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30427491324) | `cc0bfa42caf5` |
| 2026-07-30T06:11:07Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30518744569) | `013b0b00ec62` |
| 2026-07-30T06:11:04Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30518744569) | `013b0b00ec62` |
| 2026-07-30T06:10:58Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30518744569) | `013b0b00ec62` |
| 2026-07-31T06:23:21Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30609449267) | `fd40f2f58e9d` |
| 2026-07-31T06:23:21Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30609449267) | `fd40f2f58e9d` |
| 2026-07-31T06:23:23Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30609449267) | `fd40f2f58e9d` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

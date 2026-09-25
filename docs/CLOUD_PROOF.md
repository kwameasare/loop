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
| 2026-09-12T05:27:07Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/34675575011) | `1fda23be8eac` |
| 2026-09-12T05:27:03Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/34675575011) | `1fda23be8eac` |
| 2026-09-12T05:27:03Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/34675575011) | `1fda23be8eac` |
| 2026-09-13T05:26:55Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/34740282663) | `8b82b6b55cdd` |
| 2026-09-13T05:27:01Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/34740282663) | `8b82b6b55cdd` |
| 2026-09-13T05:27:01Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/34740282663) | `8b82b6b55cdd` |
| 2026-09-14T05:30:15Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/34809816647) | `adf6e8adb55b` |
| 2026-09-14T05:30:21Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/34809816647) | `adf6e8adb55b` |
| 2026-09-14T05:30:17Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/34809816647) | `adf6e8adb55b` |
| 2026-09-15T05:29:55Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/34932908891) | `cf382abc6c6c` |
| 2026-09-15T05:30:00Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/34932908891) | `cf382abc6c6c` |
| 2026-09-15T05:29:51Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/34932908891) | `cf382abc6c6c` |
| 2026-09-16T05:29:51Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35059684981) | `95ed80970842` |
| 2026-09-16T05:30:02Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35059684981) | `95ed80970842` |
| 2026-09-16T05:30:08Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35059684981) | `95ed80970842` |
| 2026-09-17T05:29:50Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35185904961) | `d22321900452` |
| 2026-09-17T05:30:03Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35185904961) | `d22321900452` |
| 2026-09-17T05:29:48Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35185904961) | `d22321900452` |
| 2026-09-18T05:28:40Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35310889749) | `5660445e448d` |
| 2026-09-18T05:29:05Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35310889749) | `5660445e448d` |
| 2026-09-18T05:28:35Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35310889749) | `5660445e448d` |
| 2026-09-19T05:27:27Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35423958120) | `689d8a6fdf4d` |
| 2026-09-19T05:27:29Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35423958120) | `689d8a6fdf4d` |
| 2026-09-19T05:27:28Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35423958120) | `689d8a6fdf4d` |
| 2026-09-20T05:27:27Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35491687227) | `9dac323b1fa6` |
| 2026-09-20T05:27:42Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35491687227) | `9dac323b1fa6` |
| 2026-09-20T05:27:26Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35491687227) | `9dac323b1fa6` |
| 2026-09-21T05:31:03Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35564749461) | `df4ef9656fe4` |
| 2026-09-21T05:31:05Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35564749461) | `df4ef9656fe4` |
| 2026-09-21T05:31:05Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35564749461) | `df4ef9656fe4` |
| 2026-09-22T05:30:03Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35690881340) | `ee8d4495dc64` |
| 2026-09-22T05:30:06Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35690881340) | `ee8d4495dc64` |
| 2026-09-22T05:30:22Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35690881340) | `ee8d4495dc64` |
| 2026-09-23T05:30:00Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35822586474) | `75613639690f` |
| 2026-09-23T05:29:56Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35822586474) | `75613639690f` |
| 2026-09-23T05:29:55Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35822586474) | `75613639690f` |
| 2026-09-24T05:29:59Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35960145337) | `8a74c878cac1` |
| 2026-09-24T05:30:03Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35960145337) | `8a74c878cac1` |
| 2026-09-24T05:30:05Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/35960145337) | `8a74c878cac1` |
| 2026-09-25T05:30:14Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36098772601) | `717c128f6adf` |
| 2026-09-25T05:30:15Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36098772601) | `717c128f6adf` |
| 2026-09-25T05:30:23Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36098772601) | `717c128f6adf` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

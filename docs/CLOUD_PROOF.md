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
| 2026-06-16T07:07:47Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27600424233) | `58a9ced2723c` |
| 2026-06-16T07:07:43Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27600424233) | `58a9ced2723c` |
| 2026-06-16T07:07:48Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27600424233) | `58a9ced2723c` |
| 2026-06-17T07:02:40Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27671699353) | `8f911e562911` |
| 2026-06-17T07:02:35Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27671699353) | `8f911e562911` |
| 2026-06-17T07:02:30Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27671699353) | `8f911e562911` |
| 2026-06-18T06:59:42Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27742437267) | `0a569eac5d45` |
| 2026-06-18T06:59:40Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27742437267) | `0a569eac5d45` |
| 2026-06-18T06:59:45Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27742437267) | `0a569eac5d45` |
| 2026-06-19T07:01:59Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27810788860) | `bea56514061f` |
| 2026-06-19T07:01:52Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27810788860) | `bea56514061f` |
| 2026-06-19T07:02:07Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27810788860) | `bea56514061f` |
| 2026-06-20T06:46:06Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27863274762) | `a70cf04caa23` |
| 2026-06-20T06:46:06Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27863274762) | `a70cf04caa23` |
| 2026-06-20T06:46:08Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27863274762) | `a70cf04caa23` |
| 2026-06-21T06:59:17Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27896603324) | `454a622341ff` |
| 2026-06-21T06:59:20Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27896603324) | `454a622341ff` |
| 2026-06-21T06:59:23Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27896603324) | `454a622341ff` |
| 2026-06-22T07:06:50Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27935580245) | `46acded46a2c` |
| 2026-06-22T07:06:44Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27935580245) | `46acded46a2c` |
| 2026-06-22T07:06:48Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/27935580245) | `46acded46a2c` |
| 2026-06-23T06:35:34Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28007190358) | `793515e5f02e` |
| 2026-06-23T06:35:40Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28007190358) | `793515e5f02e` |
| 2026-06-23T06:35:30Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28007190358) | `793515e5f02e` |
| 2026-06-24T06:33:25Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28079929169) | `8d615881c057` |
| 2026-06-24T06:33:30Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28079929169) | `8d615881c057` |
| 2026-06-24T06:33:36Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28079929169) | `8d615881c057` |
| 2026-06-25T06:35:55Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28151652828) | `7d011ff66127` |
| 2026-06-25T06:35:55Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28151652828) | `7d011ff66127` |
| 2026-06-25T06:35:56Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28151652828) | `7d011ff66127` |
| 2026-06-26T06:38:56Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28221727145) | `0ee82635d5cc` |
| 2026-06-26T06:38:59Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28221727145) | `0ee82635d5cc` |
| 2026-06-26T06:38:56Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28221727145) | `0ee82635d5cc` |
| 2026-06-27T06:30:25Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28281225744) | `9edd63de6165` |
| 2026-06-27T06:30:30Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28281225744) | `9edd63de6165` |
| 2026-06-27T06:30:26Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28281225744) | `9edd63de6165` |
| 2026-06-28T06:44:44Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28314147484) | `d7799ba0b695` |
| 2026-06-28T06:44:40Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28314147484) | `d7799ba0b695` |
| 2026-06-28T06:44:39Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28314147484) | `d7799ba0b695` |
| 2026-06-29T06:59:13Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28354336431) | `8a675cc4adf1` |
| 2026-06-29T06:59:17Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28354336431) | `8a675cc4adf1` |
| 2026-06-29T06:59:15Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28354336431) | `8a675cc4adf1` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

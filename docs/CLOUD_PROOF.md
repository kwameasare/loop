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
| 2026-10-29T05:24:49Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/40823160017) | `3fd17343fac7` |
| 2026-10-29T05:24:49Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/40823160017) | `3fd17343fac7` |
| 2026-10-29T05:24:49Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/40823160017) | `3fd17343fac7` |
| 2026-10-30T05:24:56Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41008222171) | `1b66651ef77c` |
| 2026-10-30T05:24:53Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41008222171) | `1b66651ef77c` |
| 2026-10-30T05:24:49Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41008222171) | `1b66651ef77c` |
| 2026-10-31T05:22:39Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41172286546) | `905ba24c7d58` |
| 2026-10-31T05:22:34Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41172286546) | `905ba24c7d58` |
| 2026-10-31T05:22:33Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41172286546) | `905ba24c7d58` |
| 2026-11-01T05:22:39Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41276655963) | `081bc5331fcd` |
| 2026-11-01T05:22:44Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41276655963) | `081bc5331fcd` |
| 2026-11-01T05:22:38Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41276655963) | `081bc5331fcd` |
| 2026-11-02T05:23:24Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41393638189) | `d71a9b1d783f` |
| 2026-11-02T05:23:13Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41393638189) | `d71a9b1d783f` |
| 2026-11-02T05:23:20Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41393638189) | `d71a9b1d783f` |
| 2026-11-03T05:22:49Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41583484229) | `ea9d1d68582b` |
| 2026-11-03T05:22:54Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41583484229) | `ea9d1d68582b` |
| 2026-11-03T05:22:51Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41583484229) | `ea9d1d68582b` |
| 2026-11-04T05:24:36Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41778964782) | `4a175bea8f2a` |
| 2026-11-04T05:24:31Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41778964782) | `4a175bea8f2a` |
| 2026-11-04T05:24:29Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41778964782) | `4a175bea8f2a` |
| 2026-11-05T05:22:44Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41973540902) | `a61480158a99` |
| 2026-11-05T05:22:45Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41973540902) | `a61480158a99` |
| 2026-11-05T05:22:39Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/41973540902) | `a61480158a99` |
| 2026-11-06T05:23:02Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42168004626) | `6f608ea9aec1` |
| 2026-11-06T05:22:54Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42168004626) | `6f608ea9aec1` |
| 2026-11-06T05:22:53Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42168004626) | `6f608ea9aec1` |
| 2026-11-07T05:22:40Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42342413191) | `bf046281bd11` |
| 2026-11-07T05:22:41Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42342413191) | `bf046281bd11` |
| 2026-11-07T05:22:52Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42342413191) | `bf046281bd11` |
| 2026-11-08T05:22:47Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42450488381) | `305b2156dcd6` |
| 2026-11-08T05:22:53Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42450488381) | `305b2156dcd6` |
| 2026-11-08T05:22:43Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42450488381) | `305b2156dcd6` |
| 2026-11-09T05:23:24Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42566993215) | `2f2e472ebea3` |
| 2026-11-09T05:23:35Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42566993215) | `2f2e472ebea3` |
| 2026-11-09T05:23:54Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42566993215) | `2f2e472ebea3` |
| 2026-11-10T05:23:27Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42761715622) | `a443a012312d` |
| 2026-11-10T05:23:16Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42761715622) | `a443a012312d` |
| 2026-11-10T05:23:17Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42761715622) | `a443a012312d` |
| 2026-11-11T05:22:57Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42965296743) | `dcefd4aa5dee` |
| 2026-11-11T05:23:02Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42965296743) | `dcefd4aa5dee` |
| 2026-11-11T05:22:59Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/42965296743) | `dcefd4aa5dee` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

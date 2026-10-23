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
| 2026-10-10T05:32:05Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38027780014) | `cae179e68667` |
| 2026-10-10T05:32:04Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38027780014) | `cae179e68667` |
| 2026-10-10T05:32:04Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38027780014) | `cae179e68667` |
| 2026-10-11T05:32:23Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38115063607) | `a82721068a7a` |
| 2026-10-11T05:32:29Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38115063607) | `a82721068a7a` |
| 2026-10-11T05:32:30Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38115063607) | `a82721068a7a` |
| 2026-10-12T05:41:40Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38208988159) | `7afd95a3eef1` |
| 2026-10-12T05:41:44Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38208988159) | `7afd95a3eef1` |
| 2026-10-12T05:41:42Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38208988159) | `7afd95a3eef1` |
| 2026-10-13T05:36:32Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38352188995) | `8b1b92473539` |
| 2026-10-13T05:36:34Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38352188995) | `8b1b92473539` |
| 2026-10-13T05:36:30Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38352188995) | `8b1b92473539` |
| 2026-10-14T05:30:22Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38516900032) | `e7add3ac95d6` |
| 2026-10-14T05:30:35Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38516900032) | `e7add3ac95d6` |
| 2026-10-14T05:30:25Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38516900032) | `e7add3ac95d6` |
| 2026-10-15T05:30:29Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38687065843) | `e1f51f1fb069` |
| 2026-10-15T05:30:42Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38687065843) | `e1f51f1fb069` |
| 2026-10-15T05:30:38Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38687065843) | `e1f51f1fb069` |
| 2026-10-16T05:30:31Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38856053133) | `f7bd84356b04` |
| 2026-10-16T05:30:29Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38856053133) | `f7bd84356b04` |
| 2026-10-16T05:30:34Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38856053133) | `f7bd84356b04` |
| 2026-10-17T05:28:37Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39006333969) | `66ec51f1e8ef` |
| 2026-10-17T05:28:37Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39006333969) | `66ec51f1e8ef` |
| 2026-10-17T05:28:33Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39006333969) | `66ec51f1e8ef` |
| 2026-10-18T05:28:04Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39100592963) | `949e10e60921` |
| 2026-10-18T05:28:05Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39100592963) | `949e10e60921` |
| 2026-10-18T05:28:09Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39100592963) | `949e10e60921` |
| 2026-10-19T05:31:57Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39204959568) | `2b38a20af84d` |
| 2026-10-19T05:31:47Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39204959568) | `2b38a20af84d` |
| 2026-10-19T05:31:48Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39204959568) | `2b38a20af84d` |
| 2026-10-20T05:31:15Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39375252992) | `6ab401bfd45b` |
| 2026-10-20T05:31:24Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39375252992) | `6ab401bfd45b` |
| 2026-10-20T05:31:21Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39375252992) | `6ab401bfd45b` |
| 2026-10-21T05:31:15Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39549917501) | `5810899bc8e1` |
| 2026-10-21T05:31:09Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39549917501) | `5810899bc8e1` |
| 2026-10-21T05:31:11Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39549917501) | `5810899bc8e1` |
| 2026-10-22T05:31:39Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39728429528) | `0f0c7ebd3545` |
| 2026-10-22T05:31:39Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39728429528) | `0f0c7ebd3545` |
| 2026-10-22T05:31:31Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39728429528) | `0f0c7ebd3545` |
| 2026-10-23T05:31:03Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39906097611) | `20fef42474b2` |
| 2026-10-23T05:30:57Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39906097611) | `20fef42474b2` |
| 2026-10-23T05:30:58Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/39906097611) | `20fef42474b2` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

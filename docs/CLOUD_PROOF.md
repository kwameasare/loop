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
| 2026-06-28T06:44:44Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28314147484) | `d7799ba0b695` |
| 2026-06-28T06:44:40Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28314147484) | `d7799ba0b695` |
| 2026-06-28T06:44:39Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28314147484) | `d7799ba0b695` |
| 2026-06-29T06:59:13Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28354336431) | `8a675cc4adf1` |
| 2026-06-29T06:59:17Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28354336431) | `8a675cc4adf1` |
| 2026-06-29T06:59:15Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28354336431) | `8a675cc4adf1` |
| 2026-06-30T06:40:34Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28425425838) | `6d1a275a1e3c` |
| 2026-06-30T06:40:32Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28425425838) | `6d1a275a1e3c` |
| 2026-06-30T06:40:34Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28425425838) | `6d1a275a1e3c` |
| 2026-07-01T06:48:32Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28499075894) | `bf24918460ea` |
| 2026-07-01T06:48:39Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28499075894) | `bf24918460ea` |
| 2026-07-01T06:48:37Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28499075894) | `bf24918460ea` |
| 2026-07-02T06:32:18Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28570331832) | `5bdf1da93198` |
| 2026-07-02T06:32:14Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28570331832) | `5bdf1da93198` |
| 2026-07-02T06:32:08Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28570331832) | `5bdf1da93198` |
| 2026-07-03T06:30:50Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28642882060) | `00ce5fe47fee` |
| 2026-07-03T06:30:48Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28642882060) | `00ce5fe47fee` |
| 2026-07-03T06:31:07Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28642882060) | `00ce5fe47fee` |
| 2026-07-04T06:27:07Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28697665543) | `fc10d4c51c7a` |
| 2026-07-04T06:27:06Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28697665543) | `fc10d4c51c7a` |
| 2026-07-04T06:27:16Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28697665543) | `fc10d4c51c7a` |
| 2026-07-05T06:32:07Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28732062273) | `c4e2fa60d40e` |
| 2026-07-05T06:32:05Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28732062273) | `c4e2fa60d40e` |
| 2026-07-05T06:32:10Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28732062273) | `c4e2fa60d40e` |
| 2026-07-06T06:49:41Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28773253003) | `cfb2713cac92` |
| 2026-07-06T06:49:39Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28773253003) | `cfb2713cac92` |
| 2026-07-06T06:49:42Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28773253003) | `cfb2713cac92` |
| 2026-07-07T06:33:07Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28846488994) | `c8a1a4c00973` |
| 2026-07-07T06:32:58Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28846488994) | `c8a1a4c00973` |
| 2026-07-07T06:33:13Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28846488994) | `c8a1a4c00973` |
| 2026-07-08T06:14:20Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28921739142) | `dd763a377524` |
| 2026-07-08T06:14:10Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28921739142) | `dd763a377524` |
| 2026-07-08T06:14:12Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28921739142) | `dd763a377524` |
| 2026-07-09T06:32:42Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28998916495) | `3a6cde4acc6f` |
| 2026-07-09T06:32:58Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28998916495) | `3a6cde4acc6f` |
| 2026-07-09T06:32:44Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/28998916495) | `3a6cde4acc6f` |
| 2026-07-10T06:32:30Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29074064068) | `27fdfce321bd` |
| 2026-07-10T06:32:27Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29074064068) | `27fdfce321bd` |
| 2026-07-10T06:32:27Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29074064068) | `27fdfce321bd` |
| 2026-07-11T06:04:01Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29142197400) | `00f3808e76a0` |
| 2026-07-11T06:04:03Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29142197400) | `00f3808e76a0` |
| 2026-07-11T06:04:07Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29142197400) | `00f3808e76a0` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

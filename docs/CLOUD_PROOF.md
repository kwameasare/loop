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
| 2026-07-12T06:17:01Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29182397534) | `4fa58c1143c7` |
| 2026-07-12T06:17:01Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29182397534) | `4fa58c1143c7` |
| 2026-07-12T06:16:56Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29182397534) | `4fa58c1143c7` |
| 2026-07-13T06:27:29Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29229016745) | `58019339359a` |
| 2026-07-13T06:27:45Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29229016745) | `58019339359a` |
| 2026-07-13T06:27:43Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29229016745) | `58019339359a` |
| 2026-07-14T06:02:34Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29310131875) | `a33701da15cb` |
| 2026-07-14T06:02:33Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29310131875) | `a33701da15cb` |
| 2026-07-14T06:02:36Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29310131875) | `a33701da15cb` |
| 2026-07-15T06:03:26Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29393065348) | `d4e4d7de79f7` |
| 2026-07-15T06:03:29Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29393065348) | `d4e4d7de79f7` |
| 2026-07-15T06:03:26Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29393065348) | `d4e4d7de79f7` |
| 2026-07-16T06:06:07Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29475677679) | `0d91e237f4cf` |
| 2026-07-16T06:06:03Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29475677679) | `0d91e237f4cf` |
| 2026-07-16T06:06:02Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29475677679) | `0d91e237f4cf` |
| 2026-07-17T06:05:51Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29559037489) | `498ec15bc1cd` |
| 2026-07-17T06:05:52Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29559037489) | `498ec15bc1cd` |
| 2026-07-17T06:05:57Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/29559037489) | `498ec15bc1cd` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

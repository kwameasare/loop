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
| 2026-05-13T06:30:25Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25782471173) | `4fe99585749d` |
| 2026-05-13T06:30:16Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25782471173) | `4fe99585749d` |
| 2026-05-13T06:30:13Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25782471173) | `4fe99585749d` |
| 2026-05-14T06:29:47Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25845571382) | `7fd28ecc4c3f` |
| 2026-05-14T06:29:41Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25845571382) | `7fd28ecc4c3f` |
| 2026-05-14T06:29:37Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25845571382) | `7fd28ecc4c3f` |
| 2026-05-15T06:31:49Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25903998625) | `7cf8cccb7eb2` |
| 2026-05-15T06:31:52Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25903998625) | `7cf8cccb7eb2` |
| 2026-05-15T06:31:46Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25903998625) | `7cf8cccb7eb2` |
| 2026-05-16T06:12:39Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25954688067) | `1c3fff4bab5b` |
| 2026-05-16T06:12:41Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25954688067) | `1c3fff4bab5b` |
| 2026-05-16T06:12:41Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25954688067) | `1c3fff4bab5b` |
| 2026-05-17T06:28:56Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25983497255) | `a2321ed80b57` |
| 2026-05-17T06:28:58Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25983497255) | `a2321ed80b57` |
| 2026-05-17T06:28:59Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/25983497255) | `a2321ed80b57` |
| 2026-05-18T06:40:28Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26017713624) | `b02df1825046` |
| 2026-05-18T06:40:27Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26017713624) | `b02df1825046` |
| 2026-05-18T06:40:27Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26017713624) | `b02df1825046` |
| 2026-05-19T06:36:50Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26080650600) | `4ceb4832e5f0` |
| 2026-05-19T06:36:44Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26080650600) | `4ceb4832e5f0` |
| 2026-05-19T06:36:52Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26080650600) | `4ceb4832e5f0` |
| 2026-05-20T06:36:46Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26145804079) | `4eed0d28b7fd` |
| 2026-05-20T06:36:47Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26145804079) | `4eed0d28b7fd` |
| 2026-05-20T06:36:45Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26145804079) | `4eed0d28b7fd` |
| 2026-05-21T06:38:20Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26209815907) | `8c9991c00ec3` |
| 2026-05-21T06:38:21Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26209815907) | `8c9991c00ec3` |
| 2026-05-21T06:38:19Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26209815907) | `8c9991c00ec3` |
| 2026-05-22T06:36:10Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26272455294) | `520cb7bb8648` |
| 2026-05-22T06:36:10Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26272455294) | `520cb7bb8648` |
| 2026-05-22T06:36:16Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26272455294) | `520cb7bb8648` |
| 2026-05-23T06:21:36Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26325627770) | `1e387e4285e0` |
| 2026-05-23T06:21:39Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26325627770) | `1e387e4285e0` |
| 2026-05-23T06:21:34Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26325627770) | `1e387e4285e0` |
| 2026-05-24T06:32:02Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26354067453) | `eed3dc82cdfd` |
| 2026-05-24T06:32:03Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26354067453) | `eed3dc82cdfd` |
| 2026-05-24T06:32:01Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26354067453) | `eed3dc82cdfd` |
| 2026-05-25T06:49:39Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26387468911) | `fc6517a1453f` |
| 2026-05-25T06:49:36Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26387468911) | `fc6517a1453f` |
| 2026-05-25T06:49:39Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26387468911) | `fc6517a1453f` |
| 2026-05-26T06:34:52Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26436398857) | `918d925858b9` |
| 2026-05-26T06:34:51Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26436398857) | `918d925858b9` |
| 2026-05-26T06:35:07Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26436398857) | `918d925858b9` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

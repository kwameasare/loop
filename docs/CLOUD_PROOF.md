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
| 2026-05-27T06:46:05Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26495448841) | `0508b9975044` |
| 2026-05-27T06:46:07Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26495448841) | `0508b9975044` |
| 2026-05-27T06:46:08Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26495448841) | `0508b9975044` |
| 2026-05-28T06:39:44Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26559050061) | `ff0381c2513e` |
| 2026-05-28T06:39:43Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26559050061) | `ff0381c2513e` |
| 2026-05-28T06:39:47Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26559050061) | `ff0381c2513e` |
| 2026-05-29T06:41:21Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26622401000) | `5a5ebbc09750` |
| 2026-05-29T06:41:29Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26622401000) | `5a5ebbc09750` |
| 2026-05-29T06:41:22Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26622401000) | `5a5ebbc09750` |
| 2026-05-30T06:29:07Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26676884375) | `881bf68f33da` |
| 2026-05-30T06:29:06Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26676884375) | `881bf68f33da` |
| 2026-05-30T06:29:05Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26676884375) | `881bf68f33da` |
| 2026-05-31T06:42:26Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26705618997) | `c3008817da0d` |
| 2026-05-31T06:42:33Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26705618997) | `c3008817da0d` |
| 2026-05-31T06:42:26Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26705618997) | `c3008817da0d` |
| 2026-06-01T07:00:34Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26740119483) | `1e330b3b3f9c` |
| 2026-06-01T07:00:35Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26740119483) | `1e330b3b3f9c` |
| 2026-06-01T07:00:36Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/26740119483) | `1e330b3b3f9c` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

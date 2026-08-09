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
| 2026-08-01T06:15:07Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30687353061) | `5ba5a47a4bfc` |
| 2026-08-01T06:15:04Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30687353061) | `5ba5a47a4bfc` |
| 2026-08-01T06:15:02Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30687353061) | `5ba5a47a4bfc` |
| 2026-08-02T06:16:46Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30735595140) | `e01242d500af` |
| 2026-08-02T06:16:47Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30735595140) | `e01242d500af` |
| 2026-08-02T06:16:47Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30735595140) | `e01242d500af` |
| 2026-08-03T06:29:20Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30790322307) | `462ef06879de` |
| 2026-08-03T06:29:19Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30790322307) | `462ef06879de` |
| 2026-08-03T06:29:15Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30790322307) | `462ef06879de` |
| 2026-08-04T06:13:20Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30883195580) | `da9f07d88976` |
| 2026-08-04T06:13:18Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30883195580) | `da9f07d88976` |
| 2026-08-04T06:13:26Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30883195580) | `da9f07d88976` |
| 2026-08-05T06:10:52Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30980436654) | `b8941ef0aefe` |
| 2026-08-05T06:10:54Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30980436654) | `b8941ef0aefe` |
| 2026-08-05T06:10:57Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/30980436654) | `b8941ef0aefe` |
| 2026-08-06T06:13:05Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31076492540) | `25a1c965caf5` |
| 2026-08-06T06:12:57Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31076492540) | `25a1c965caf5` |
| 2026-08-06T06:14:00Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31076492540) | `25a1c965caf5` |
| 2026-08-07T05:51:46Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31151931464) | `9e560976db37` |
| 2026-08-07T05:51:50Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31151931464) | `9e560976db37` |
| 2026-08-07T05:51:55Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31151931464) | `9e560976db37` |
| 2026-08-08T05:32:40Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31241886414) | `8120475ae3d2` |
| 2026-08-08T05:32:44Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31241886414) | `8120475ae3d2` |
| 2026-08-08T05:32:39Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31241886414) | `8120475ae3d2` |
| 2026-08-09T05:36:23Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31297018363) | `1067071b65d2` |
| 2026-08-09T05:36:23Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31297018363) | `1067071b65d2` |
| 2026-08-09T05:36:29Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31297018363) | `1067071b65d2` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

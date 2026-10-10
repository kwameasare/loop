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
| 2026-09-27T05:29:19Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36297298988) | `129c2c87acde` |
| 2026-09-27T05:29:24Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36297298988) | `129c2c87acde` |
| 2026-09-27T05:29:21Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36297298988) | `129c2c87acde` |
| 2026-09-28T05:33:57Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36382386395) | `729a10a5dafa` |
| 2026-09-28T05:33:46Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36382386395) | `729a10a5dafa` |
| 2026-09-28T05:33:56Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36382386395) | `729a10a5dafa` |
| 2026-09-29T05:32:37Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36526589143) | `f9d01b0f7820` |
| 2026-09-29T05:32:44Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36526589143) | `f9d01b0f7820` |
| 2026-09-29T05:32:39Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36526589143) | `f9d01b0f7820` |
| 2026-09-30T05:32:41Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36673827725) | `0131f3a6bdde` |
| 2026-09-30T05:32:43Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36673827725) | `0131f3a6bdde` |
| 2026-09-30T05:32:43Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36673827725) | `0131f3a6bdde` |
| 2026-10-01T05:32:39Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36820200011) | `804726780442` |
| 2026-10-01T05:32:37Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36820200011) | `804726780442` |
| 2026-10-01T05:32:42Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36820200011) | `804726780442` |
| 2026-10-02T05:32:07Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36969299939) | `89c524cea771` |
| 2026-10-02T05:32:09Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36969299939) | `89c524cea771` |
| 2026-10-02T05:32:05Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/36969299939) | `89c524cea771` |
| 2026-10-03T05:39:02Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37100451527) | `b086c07d8b8e` |
| 2026-10-03T05:39:07Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37100451527) | `b086c07d8b8e` |
| 2026-10-03T05:39:00Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37100451527) | `b086c07d8b8e` |
| 2026-10-04T07:15:04Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37185165569) | `eeafed8b5714` |
| 2026-10-04T07:15:08Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37185165569) | `eeafed8b5714` |
| 2026-10-04T07:15:05Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37185165569) | `eeafed8b5714` |
| 2026-10-05T05:43:43Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37268994058) | `3ff29f50e246` |
| 2026-10-05T05:43:51Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37268994058) | `3ff29f50e246` |
| 2026-10-05T05:43:45Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37268994058) | `3ff29f50e246` |
| 2026-10-06T05:33:04Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37419003036) | `311825ee381a` |
| 2026-10-06T05:32:59Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37419003036) | `311825ee381a` |
| 2026-10-06T05:33:11Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37419003036) | `311825ee381a` |
| 2026-10-07T05:34:13Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37576881287) | `027aec946c4d` |
| 2026-10-07T05:34:08Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37576881287) | `027aec946c4d` |
| 2026-10-07T05:34:12Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37576881287) | `027aec946c4d` |
| 2026-10-08T05:34:04Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37732953118) | `6dc331d7aa7c` |
| 2026-10-08T05:34:07Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37732953118) | `6dc331d7aa7c` |
| 2026-10-08T05:34:04Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37732953118) | `6dc331d7aa7c` |
| 2026-10-09T05:35:10Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37889202577) | `613db241c73b` |
| 2026-10-09T05:35:06Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37889202577) | `613db241c73b` |
| 2026-10-09T05:35:11Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/37889202577) | `613db241c73b` |
| 2026-10-10T05:32:05Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38027780014) | `cae179e68667` |
| 2026-10-10T05:32:04Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38027780014) | `cae179e68667` |
| 2026-10-10T05:32:04Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/38027780014) | `cae179e68667` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

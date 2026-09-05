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
| 2026-08-23T05:29:57Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32620463972) | `90fac401a253` |
| 2026-08-23T05:30:04Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32620463972) | `90fac401a253` |
| 2026-08-23T05:30:07Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32620463972) | `90fac401a253` |
| 2026-08-24T05:31:36Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32693795569) | `e530115c4632` |
| 2026-08-24T05:31:40Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32693795569) | `e530115c4632` |
| 2026-08-24T05:31:42Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32693795569) | `e530115c4632` |
| 2026-08-25T05:30:22Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32813039503) | `b61a0fc9419d` |
| 2026-08-25T05:30:37Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32813039503) | `b61a0fc9419d` |
| 2026-08-25T05:30:25Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32813039503) | `b61a0fc9419d` |
| 2026-08-26T05:30:57Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32934278203) | `832ce066b3c3` |
| 2026-08-26T05:30:57Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32934278203) | `832ce066b3c3` |
| 2026-08-26T05:31:14Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32934278203) | `832ce066b3c3` |
| 2026-08-27T07:59:53Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33051993914) | `bce7b12a3b29` |
| 2026-08-27T07:59:43Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33051993914) | `bce7b12a3b29` |
| 2026-08-27T07:59:41Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33051993914) | `bce7b12a3b29` |
| 2026-08-28T08:01:37Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33153631736) | `02cb50f09a34` |
| 2026-08-28T08:01:38Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33153631736) | `02cb50f09a34` |
| 2026-08-28T08:01:38Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33153631736) | `02cb50f09a34` |
| 2026-08-29T05:25:50Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33236105895) | `199bdb9e1e6f` |
| 2026-08-29T05:25:51Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33236105895) | `199bdb9e1e6f` |
| 2026-08-29T05:25:44Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33236105895) | `199bdb9e1e6f` |
| 2026-08-30T05:26:09Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33294652407) | `d71123af02b9` |
| 2026-08-30T05:26:13Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33294652407) | `d71123af02b9` |
| 2026-08-30T05:26:08Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33294652407) | `d71123af02b9` |
| 2026-08-31T05:29:18Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33360656266) | `86399bda5c4d` |
| 2026-08-31T05:29:20Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33360656266) | `86399bda5c4d` |
| 2026-08-31T05:29:25Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33360656266) | `86399bda5c4d` |
| 2026-09-01T05:29:30Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33473726195) | `b6c89090137b` |
| 2026-09-01T05:29:27Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33473726195) | `b6c89090137b` |
| 2026-09-01T05:29:27Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33473726195) | `b6c89090137b` |
| 2026-09-02T05:32:14Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33595008074) | `08665515ce50` |
| 2026-09-02T05:32:27Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33595008074) | `08665515ce50` |
| 2026-09-02T05:32:18Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33595008074) | `08665515ce50` |
| 2026-09-03T05:49:56Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33720463183) | `18ce1760a4d1` |
| 2026-09-03T05:49:58Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33720463183) | `18ce1760a4d1` |
| 2026-09-03T05:50:18Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33720463183) | `18ce1760a4d1` |
| 2026-09-04T05:28:31Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33840562367) | `ba6f2b104366` |
| 2026-09-04T05:28:28Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33840562367) | `ba6f2b104366` |
| 2026-09-04T05:28:38Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33840562367) | `ba6f2b104366` |
| 2026-09-05T05:26:48Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33947182803) | `6123878d1462` |
| 2026-09-05T05:26:41Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33947182803) | `6123878d1462` |
| 2026-09-05T05:26:45Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/33947182803) | `6123878d1462` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

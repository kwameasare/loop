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
| 2026-11-13T05:23:14Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/43371568391) | `27bffb51394b` |
| 2026-11-13T05:23:00Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/43371568391) | `27bffb51394b` |
| 2026-11-13T05:23:12Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/43371568391) | `27bffb51394b` |
| 2026-11-14T05:23:11Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/43561201632) | `acf9e436041d` |
| 2026-11-14T05:23:15Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/43561201632) | `acf9e436041d` |
| 2026-11-14T05:23:02Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/43561201632) | `acf9e436041d` |
| 2026-11-15T05:23:10Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/43680791283) | `ea134432e0ac` |
| 2026-11-15T05:23:07Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/43680791283) | `ea134432e0ac` |
| 2026-11-15T05:23:12Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/43680791283) | `ea134432e0ac` |
| 2026-11-16T05:25:35Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/43810044932) | `665a7e285311` |
| 2026-11-16T05:25:35Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/43810044932) | `665a7e285311` |
| 2026-11-16T05:25:43Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/43810044932) | `665a7e285311` |
| 2026-11-17T05:23:05Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44023623306) | `4a3127c911af` |
| 2026-11-17T05:23:12Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44023623306) | `4a3127c911af` |
| 2026-11-17T05:23:12Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44023623306) | `4a3127c911af` |
| 2026-11-18T05:23:43Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44243841596) | `e40982985e24` |
| 2026-11-18T05:23:43Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44243841596) | `e40982985e24` |
| 2026-11-18T05:23:46Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44243841596) | `e40982985e24` |
| 2026-11-19T05:23:32Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44464728416) | `c409a5100088` |
| 2026-11-19T05:23:22Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44464728416) | `c409a5100088` |
| 2026-11-19T05:23:29Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44464728416) | `c409a5100088` |
| 2026-11-20T05:23:52Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44680639587) | `f9129547dad2` |
| 2026-11-20T05:23:43Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44680639587) | `f9129547dad2` |
| 2026-11-20T05:23:50Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44680639587) | `f9129547dad2` |
| 2026-11-21T05:23:09Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44870568089) | `734153fa93cb` |
| 2026-11-21T05:23:05Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44870568089) | `734153fa93cb` |
| 2026-11-21T05:23:06Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44870568089) | `734153fa93cb` |
| 2026-11-22T05:23:19Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44989128508) | `047b6d629b64` |
| 2026-11-22T05:23:18Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44989128508) | `047b6d629b64` |
| 2026-11-22T05:23:23Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/44989128508) | `047b6d629b64` |
| 2026-11-23T05:25:44Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/45117619049) | `ce44dbf01ad3` |
| 2026-11-23T05:25:50Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/45117619049) | `ce44dbf01ad3` |
| 2026-11-23T05:25:49Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/45117619049) | `ce44dbf01ad3` |
| 2026-11-24T05:23:52Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/45332920634) | `124e6c3622a9` |
| 2026-11-24T05:23:48Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/45332920634) | `124e6c3622a9` |
| 2026-11-24T05:23:54Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/45332920634) | `124e6c3622a9` |
| 2026-11-25T05:24:39Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/45553258584) | `d93b77b72608` |
| 2026-11-25T05:24:28Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/45553258584) | `d93b77b72608` |
| 2026-11-25T05:24:32Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/45553258584) | `d93b77b72608` |
| 2026-11-26T05:24:17Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/45761261241) | `7d230399d8e3` |
| 2026-11-26T05:24:12Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/45761261241) | `7d230399d8e3` |
| 2026-11-26T05:24:23Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/45761261241) | `7d230399d8e3` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

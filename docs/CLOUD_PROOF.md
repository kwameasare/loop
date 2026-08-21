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
| 2026-08-08T05:32:40Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31241886414) | `8120475ae3d2` |
| 2026-08-08T05:32:44Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31241886414) | `8120475ae3d2` |
| 2026-08-08T05:32:39Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31241886414) | `8120475ae3d2` |
| 2026-08-09T05:36:23Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31297018363) | `1067071b65d2` |
| 2026-08-09T05:36:23Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31297018363) | `1067071b65d2` |
| 2026-08-09T05:36:29Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31297018363) | `1067071b65d2` |
| 2026-08-10T05:49:32Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31359764314) | `9ccc4e7a15ca` |
| 2026-08-10T05:49:16Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31359764314) | `9ccc4e7a15ca` |
| 2026-08-10T05:49:14Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31359764314) | `9ccc4e7a15ca` |
| 2026-08-11T05:39:50Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31462337676) | `054ad2ac1f1c` |
| 2026-08-11T05:39:53Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31462337676) | `054ad2ac1f1c` |
| 2026-08-11T05:39:47Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31462337676) | `054ad2ac1f1c` |
| 2026-08-12T05:49:39Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31567782121) | `c7b8d66f7424` |
| 2026-08-12T05:49:41Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31567782121) | `c7b8d66f7424` |
| 2026-08-12T05:49:40Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31567782121) | `c7b8d66f7424` |
| 2026-08-13T05:50:54Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31671660847) | `776e651e730f` |
| 2026-08-13T05:50:42Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31671660847) | `776e651e730f` |
| 2026-08-13T05:50:36Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31671660847) | `776e651e730f` |
| 2026-08-14T05:49:52Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31774199665) | `104812dda696` |
| 2026-08-14T05:49:52Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31774199665) | `104812dda696` |
| 2026-08-14T05:49:43Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31774199665) | `104812dda696` |
| 2026-08-15T05:29:15Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31867027899) | `90cb6acc64e3` |
| 2026-08-15T05:29:16Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31867027899) | `90cb6acc64e3` |
| 2026-08-15T05:29:12Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31867027899) | `90cb6acc64e3` |
| 2026-08-16T05:29:51Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31929107104) | `68030ed53ba6` |
| 2026-08-16T05:29:50Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31929107104) | `68030ed53ba6` |
| 2026-08-16T05:29:56Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31929107104) | `68030ed53ba6` |
| 2026-08-17T05:30:58Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31998110975) | `a6919a67e5d6` |
| 2026-08-17T05:30:57Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31998110975) | `a6919a67e5d6` |
| 2026-08-17T05:30:57Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/31998110975) | `a6919a67e5d6` |
| 2026-08-18T05:30:08Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32103057479) | `4ed766b5e644` |
| 2026-08-18T05:30:03Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32103057479) | `4ed766b5e644` |
| 2026-08-18T05:30:07Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32103057479) | `4ed766b5e644` |
| 2026-08-19T05:30:13Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32219594195) | `1dfec59504ef` |
| 2026-08-19T05:30:14Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32219594195) | `1dfec59504ef` |
| 2026-08-19T05:30:09Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32219594195) | `1dfec59504ef` |
| 2026-08-20T05:30:18Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32335783277) | `77246578a429` |
| 2026-08-20T05:30:12Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32335783277) | `77246578a429` |
| 2026-08-20T05:30:14Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32335783277) | `77246578a429` |
| 2026-08-21T05:30:39Z | `aws` | `na-east` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32450750550) | `20393a721ac2` |
| 2026-08-21T05:30:37Z | `azure` | `eu-west` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32450750550) | `20393a721ac2` |
| 2026-08-21T05:30:41Z | `gcp` | `apac-sg` | RED | [run](https://github.com/kwameasare/loop/actions/runs/32450750550) | `20393a721ac2` |
<!-- CLOUD_PROOF_HISTORY:END -->

## Evidence sources

- [cross-cloud-smoke workflow](../.github/workflows/cross-cloud-smoke.yml)
  runs the live nightly marks.
- [Cloud portability architecture](../loop_implementation/architecture/CLOUD_PORTABILITY.md)
  defines the service mapping and two-cloud rule.
- [ADR-016](../loop_implementation/adrs/README.md#adr-016--cloud-agnostic-by-default)
  records the no-lock-in decision.

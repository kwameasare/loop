# Regional Deploys

Loop ships a single Helm chart (`infra/helm/loop`) plus per-region
values overlays. The chart is **cloud-agnostic** — every external
dependency is wired through `.externals.*`, so the same overlay
runs on AWS eu-west-1, GCP europe-west1, Azure westeurope, or an
on-prem OVH/Hetzner cluster. The choice of cloud is an ops-time
decision; the chart and application code never branch on it.

See also:

* [CLOUD_PORTABILITY.md](../architecture/CLOUD_PORTABILITY.md) — the
  abstraction contract that keeps regional deploys portable.
* [SECURITY.md](SECURITY.md) — KMS, audit, and data-residency
  requirements.
* `infra/helm/loop/values.yaml` — the base chart defaults.
* `infra/terraform/envs/prod-eu-west/` — Terraform Helm release for
  installing the EU overlay into a pre-provisioned EU Kubernetes cluster.

## Available regions

| Region    | Overlay file                                         | Status   | Residency |
| --------- | ---------------------------------------------------- | -------- | --------- |
| eu-west   | `infra/helm/loop/values-eu-west.yaml`                | GA (S045) | EU        |
| us-east   | (uses base `values.yaml`)                            | GA       | US        |
| ap-south  | _planned (S0xx)_                                     | —        | —         |
| us-gov    | _planned (FedRAMP track)_                            | —        | —         |

## EU-west deploy (S045)

The EU-west overlay enforces three things the base chart does not:

1. **Data residency.** `LOOP_DATA_RESIDENCY=eu` is propagated to
   the control plane and runtime. The control plane refuses to
   schedule a workspace whose primary residency tag is non-EU.
2. **Region pin in network policy.** `networkPolicy.enforceRegionPin=true`
   forces NetworkPolicy templates to drop egress to pods/services
   not labelled `region=eu-west`. This is independent of cloud
   VPC peering — defence in depth.
3. **In-region telemetry & KMS.** OTLP, metrics, logs, traces, and
   KMS keys must all resolve to EU endpoints. The chart's
   `NOTES.txt` preflight fails the install if any of these is
   unset or points outside the region.

### Install

```sh
helm install loop ./infra/helm/loop \
  -f ./infra/helm/loop/values-eu-west.yaml \
  --namespace loop-eu-west \
  --create-namespace \
  --set externals.kms.keyArn=$EU_KMS_ARN
```

### Cloud-specific notes

The overlay is generic. Per cloud, ops fills `.externals.*` as
follows:

| External       | AWS eu-west-1            | GCP europe-west1     | Azure westeurope         | On-prem (OVH)        |
| -------------- | ------------------------ | -------------------- | ------------------------ | -------------------- |
| postgresUrl    | RDS Postgres             | Cloud SQL            | Azure DB for Postgres    | Self-hosted Patroni  |
| redisUrl       | ElastiCache              | Memorystore          | Azure Cache for Redis    | Bitnami Redis chart  |
| qdrantUrl      | Qdrant in EKS/VPC        | Qdrant in GKE/VPC    | Qdrant in AKS/VNet       | Qdrant StatefulSet   |
| natsUrl        | NATS on EKS              | NATS on GKE          | NATS on AKS              | NATS chart           |
| clickhouseUrl  | ClickHouse on EKS        | ClickHouse on GKE    | ClickHouse on AKS        | ClickHouse chart     |
| s3Endpoint     | S3 (eu-west-1 only)      | GCS S3-compatible    | Blob S3-compatible       | MinIO                |
| otelEndpoint   | Managed Grafana Cloud EU | Cloud Trace europe   | App Insights westeurope  | Self-hosted otelcol  |

### Verifying residency

After install, run the preflight:

```sh
kubectl -n loop-eu-west exec deploy/loop-control-plane -- \
  loop-cli admin region verify
```

Expected output: `region=eu-west residency=eu external_endpoints=ok`.
A non-zero exit code aborts CI and pages the on-call per
[RUNBOOKS.md](RUNBOOKS.md).

### Failure modes

* **Cross-region egress detected.** NetworkPolicy alert fires; the
  control plane stops issuing new conversation tokens until the
  policy violation is cleared.
* **KMS key in wrong region.** Preflight fails. No data is written.
* **OTLP collector outside EU.** Preflight fails. No traces are
  exported until corrected.

### Rollback

`helm rollback loop` is safe; the overlay does not run schema
migrations. Schema migrations are gated on the migration job
(see `apps/control-plane/`).

## Adding a new region

1. Copy `values-eu-west.yaml` to `values-<region>.yaml`.
2. Update `global.region`, `global.dataResidency`,
   `*.env.LOOP_REGION`, and every `externals.*` URI.
3. Update `networkPolicy.allowedRegions`.
4. Add a row to the table at the top of this doc.
5. Add a regional preflight check to the `loop-cli admin region
   verify` command and CI.
6. File an ADR in [adrs/](../adrs/) for the residency model.

## Change log

| Date       | Author       | Change                                            |
| ---------- | ------------ | ------------------------------------------------- |
| 2026-05-01 | codex-orion (S595) | Add signed regional image promotion workflow; daily verification keeps NA/EU tags on one digest. |
| 2026-04-30 | GitHub Copilot (S045) | Add EU-west overlay + regional deploy doc. |

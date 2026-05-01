# Loop self-host Helm chart

Single chart that brings up Loop's control-plane, data-plane runtime,
gateway, and optional **dp-tool-host** sandbox tier on Kubernetes >= 1.27.
Goal: feature parity with the managed cloud offering.

## Install

```bash
helm install loop ./infra/helm/loop \
  --set externals.postgresUrl=postgresql://... \
  --set externals.redisUrl=redis://... \
  --set secrets.llmApiKey=$LLM_API_KEY
```

## Layout

| File | Purpose |
| ---- | ------- |
| `Chart.yaml` | chart metadata |
| `values.yaml` | tuneables -- replicas, resources, image refs, externals, secrets, ingress |
| `values.schema.json` | JSON Schema (Draft 2020-12) helm validates `-f` overrides against |
| `templates/_helpers.tpl` | name / label / image helpers |
| `templates/configmap.yaml` | non-secret externals (`POSTGRES_URL`, etc.) |
| `templates/secret.yaml` | LLM API key + JWT signing key |
| `templates/serviceaccount.yaml` | RBAC subject |
| `templates/control-plane.yaml` | Deployment + Service for control-plane |
| `templates/control-plane-hpa.yaml` | HPA (autoscaling/v2) for control-plane (gated on `controlPlane.autoscaling.enabled`) |
| `templates/control-plane-pdb.yaml` | PodDisruptionBudget for control-plane (gated on `controlPlane.pdb.enabled`) |
| `templates/runtime.yaml` | Deployment + Service for runtime |
| `templates/runtime-hpa.yaml` | HPA (autoscaling/v2) for runtime (gated on `runtime.autoscaling.enabled`) |
| `templates/runtime-pdb.yaml` | PodDisruptionBudget for runtime (gated on `runtime.pdb.enabled`) |
| `templates/gateway.yaml` | Deployment + Service for gateway |
| `templates/gateway-hpa.yaml` | HPA (autoscaling/v2) for gateway (gated on `gateway.autoscaling.enabled`) |
| `templates/gateway-pdb.yaml` | PodDisruptionBudget for gateway (gated on `gateway.pdb.enabled`) |
| `templates/ingress.yaml` | optional ingress (`/v1/cp`, `/v1/runtime`, `/v1/llm`) |
| `templates/NOTES.txt` | post-install notes |
| `charts/dp-tool-host/` | local subchart for the tool-host Deployment, Service, service account, and Kata pre-install hook |

## Cloud portability

Every external dependency URI is exposed under `.Values.externals` so a
production install can point at managed services (RDS, ElastiCache, MSK,
etc.) -- see [CLOUD_PORTABILITY.md](../../../loop_implementation/architecture/CLOUD_PORTABILITY.md).

### Bundled dependencies

For a "batteries-included" install (e.g. dev, demo, single-tenant SaaS)
the chart bundles vetted upstream charts as Helm dependencies:

| Dependency | Subchart | Version | Toggle |
| ---------- | -------- | ------- | ------ |
| PostgreSQL | `bitnami/postgresql` | 15.5.38 | `postgresql.enabled` |
| Redis | `bitnami/redis` | 20.3.0 | `redis.enabled` |
| Qdrant | `qdrant/qdrant` | 1.13.6 | `qdrant.enabled` |
| NATS (JetStream) | `nats-io/nats` | 1.2.2 | `nats.enabled` |
| MinIO (S3-compat) | `bitnami/minio` | 14.10.5 | `minio.enabled` |
| ClickHouse | `bitnami/clickhouse` | 6.2.18 | `clickhouse.enabled` |

### Ingress + cert-manager

The chart ships an `Ingress` template gated on `ingress.enabled`. Set
`ingress.className` to either `nginx` (ingress-nginx) or `traefik`.
When `ingress.certManager.enabled=true`, the Ingress is annotated
with `cert-manager.io/cluster-issuer` and a TLS section is rendered
using `ingress.certManager.tlsSecretName`, so a fresh
`helm install --set ingress.enabled=true --set ingress.certManager.enabled=true`
produces TLS-terminated routes (verified on kind).

### dp-tool-host + Kata

The `dp-tool-host` sandbox tier is packaged as a local subchart and is
enabled by default with `toolHost.enabled=true`. The subchart assumes
clusters have the Kata/Firecracker RuntimeClass from
[`infra/k8s/sandbox/runtime-class.yaml`](../../k8s/sandbox/runtime-class.yaml):

| Value | Default | Purpose |
| ----- | ------- | ------- |
| `toolHost.enabled` | `true` | installs or skips the local subchart |
| `toolHost.sandboxRuntimeClassName` | `loop-firecracker` | RuntimeClass used by tool sandbox Pods |
| `toolHost.kata.runtimeClassHandler` | `kata-fc` | expected RuntimeClass handler |
| `toolHost.preInstallCheck.enabled` | `true` | runs a Helm pre-install/pre-upgrade check |

When `toolHost.enabled=true` and the pre-install check is enabled, Helm
runs a hook Job before creating workloads. The Job reads the cluster's
`RuntimeClass` and fails with a clear error if `loop-firecracker` is
missing or not backed by the configured Kata handler. Clusters without
Kata support should set `toolHost.enabled=false`; tool dispatch remains
disabled until the sandbox RuntimeClass is installed.

To use an existing managed Postgres (RDS, Cloud SQL, etc.) set
`postgresql.enabled=false` and override `externals.postgresUrl`. Same
pattern for Redis: set `redis.enabled=false` and point
`externals.redisUrl` at ElastiCache / Memorystore / etc. Run
`helm dependency update infra/helm/loop` once before `helm install`
to pull the pinned subcharts into `infra/helm/loop/charts/`.

## Validation

`tools/check_helm_chart.py` runs a structural check against the chart
on every CI run -- it parses the YAML files (without invoking helm)
and asserts that:

* `Chart.yaml` has the required keys.
* `values.yaml` exposes the components, externals, and secrets the
  templates reference.
* Local file dependencies such as `charts/dp-tool-host/` exist.
* Every template under `templates/` is parseable YAML (after stripping
  helm template directives).

`tests/test_helm_values_schema.py` validates `values.yaml` against
`values.schema.json` (helm itself runs the same schema on every
`helm install` / `helm upgrade`). The schema permits regional overlays
to add governance sections (`audit`, `networkPolicy`, `telemetry`); see
[CLOUD_PORTABILITY.md](../../../loop_implementation/architecture/CLOUD_PORTABILITY.md).

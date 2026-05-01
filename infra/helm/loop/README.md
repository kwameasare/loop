# Loop self-host Helm chart

Single chart that brings up the three Loop services -- **control-plane**,
**runtime**, and **gateway** -- on any Kubernetes >= 1.27. Goal: feature
parity with the managed cloud offering.

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

## Cloud portability

Every external dependency URI is exposed under `.Values.externals` so a
production install can point at managed services (RDS, ElastiCache, MSK,
etc.) -- see [CLOUD_PORTABILITY.md](../../../loop_implementation/architecture/CLOUD_PORTABILITY.md).

## Validation

`tools/check_helm_chart.py` runs a structural check against the chart
on every CI run -- it parses the YAML files (without invoking helm)
and asserts that:

* `Chart.yaml` has the required keys.
* `values.yaml` exposes the components, externals, and secrets the
  templates reference.
* Every template under `templates/` is parseable YAML (after stripping
  helm template directives).

`tests/test_helm_values_schema.py` validates `values.yaml` against
`values.schema.json` (helm itself runs the same schema on every
`helm install` / `helm upgrade`). The schema permits regional overlays
to add governance sections (`audit`, `networkPolicy`, `telemetry`); see
[CLOUD_PORTABILITY.md](../../../loop_implementation/architecture/CLOUD_PORTABILITY.md).

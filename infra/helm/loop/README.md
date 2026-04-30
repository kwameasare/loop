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
| `templates/_helpers.tpl` | name / label / image helpers |
| `templates/configmap.yaml` | non-secret externals (`POSTGRES_URL`, etc.) |
| `templates/secret.yaml` | LLM API key + JWT signing key |
| `templates/serviceaccount.yaml` | RBAC subject |
| `templates/control-plane.yaml` | Deployment + Service for control-plane |
| `templates/runtime.yaml` | Deployment + Service for runtime |
| `templates/gateway.yaml` | Deployment + Service for gateway |
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

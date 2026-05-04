# loop-observability

Helm chart that deploys the Loop observability stack:

- `kube-prometheus-stack` (Prometheus, Alertmanager, Grafana)
- `loki`
- `tempo`
- `falco` with `falcosidekick`

This chart also ships:

- Preloaded Grafana dashboard ConfigMaps from `files/dashboards/`
- Loop SLO burn Prometheus rules from `files/prometheus/slo-burn.yaml`
- Loop Falco custom rules through `falco.customRules`

Install:

```bash
helm dependency update infra/helm/loop-observability
helm upgrade --install loop-observability infra/helm/loop-observability \
  --namespace loop-observability \
  --create-namespace
```

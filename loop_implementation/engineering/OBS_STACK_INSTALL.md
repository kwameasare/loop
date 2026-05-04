# Loop Observability Stack Install Guide

This guide deploys the full observability stack from
`infra/helm/loop-observability/`:

- Prometheus + Alertmanager + Grafana (`kube-prometheus-stack`)
- Loki
- Tempo
- Falco + Falcosidekick

## 1) Prerequisites

```bash
kubectl version --short
helm version
```

Kubernetes 1.27+ is required.

## 2) Install

```bash
helm dependency update infra/helm/loop-observability
helm upgrade --install loop-observability infra/helm/loop-observability \
  --namespace loop-observability \
  --create-namespace \
  --wait \
  --timeout 12m
```

## 3) Access the UIs

```bash
kubectl -n loop-observability port-forward svc/loop-observability-kube-prometheus-stack-grafana 3000:80
kubectl -n loop-observability port-forward svc/loop-observability-kube-prometheus-stack-prometheus 9090:9090
kubectl -n loop-observability port-forward svc/loop-observability-kube-prometheus-stack-alertmanager 9093:9093
```

Grafana dashboards are preloaded from `infra/grafana/*.json`.

## 4) SLO burn alert wiring

- SLO burn rules are loaded from `infra/prometheus/alerts/slo-burn.yaml`.
- Alertmanager route config includes:
  - `pagerduty="true"` -> `pagerduty-slo`
  - `source="falco"` -> `falco-events`

If PagerDuty routing is desired, set `PAGERDUTY_SLO_ROUTING_KEY` in the
Alertmanager environment.

## 5) Falco smoke validation

```bash
kubectl run falco-smoke --image=busybox:1.36 --restart=Never --command -- sleep 180
kubectl wait --for=condition=Ready pod/falco-smoke --timeout=120s
kubectl exec falco-smoke -- sh -lc 'echo smoke-rule'
```

Then verify the alert appears in Alertmanager:

```bash
curl -s http://127.0.0.1:9093/api/v2/alerts | grep shell-spawned-in-pod
```

## 6) What ships in this chart

- `infra/helm/loop-observability/files/dashboards/*`
- `infra/helm/loop-observability/files/prometheus/slo-burn.yaml`
- `infra/helm/loop-observability/files/falco/loop_rules.yaml`

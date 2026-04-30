# dp-tool-host k8s manifests

This directory holds the Kubernetes deployment artifacts for the
Firecracker/Kata sandbox tier behind `dp-tool-host`. They land with
story **S014** and are referenced by ADR-005 (Firecracker microVMs
for tool sandboxing) and ADR-021 (Kata + Firecracker as the chosen
runtime).

| File                    | Purpose                                                             |
|-------------------------|---------------------------------------------------------------------|
| `runtime-class.yaml`    | RuntimeClass `loop-firecracker` pinning Pods to the Kata `kata-fc` shim. |
| `pod-template.yaml`     | Per-sandbox Pod template the warmpool controller stamps out.        |
| `network-policy.yaml`   | Default-deny egress for sandbox Pods. Per-Pod allowlists are added at acquire time. |

## Apply order (per cluster)

1. Install the Kata operator (`kata-deploy`) and label sandbox-capable
   nodes with `loop.run/sandbox=firecracker`.
2. `kubectl apply -f infra/k8s/sandbox/runtime-class.yaml`.
3. `kubectl apply -f infra/k8s/sandbox/network-policy.yaml` to every
   workspace's data-plane namespace.
4. The control plane (`cp-deployer`, S006) is the only thing that
   should ever apply `pod-template.yaml` -- it does so via the
   `loop-tool-host` warmpool when prewarming for a workspace.

## Validation

`runtime-class.yaml` and `pod-template.yaml` are checked for syntactic
validity by the Sprint-0 manifest-lint hook (`tools/lint_manifests.py`,
S031). The full integration smoke against a kind cluster lands with
S028 (real Kubernetes-backed warmpool controller).

## Out of scope

* HorizontalPodAutoscaler -- the warmpool sizes itself by acquire/release
  pressure, not CPU.
* PodDisruptionBudget -- microVMs are short-lived; drains rebuild on demand.
* Service/Ingress -- MCP servers are spoken to over the Kubernetes API
  via `Pod/exec`, not Services.

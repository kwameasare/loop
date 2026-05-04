"""Contract tests for helm pod-security hardening.

Closes P0.6g + P0.6h + P0.6i + the dp-tool-host PDB/HPA gap from the
prod-readiness audit.

These tests pin the *shape* of the chart so a future edit can't silently
revert the security posture. We can't `helm template` here (helm isn't a
test-time dep), so we read each template as raw text and assert that
known anchor strings are present. That's enough to catch deletion or
accidental override at the template level.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHART_DIR = ROOT / "infra" / "helm" / "loop"
TEMPLATES = CHART_DIR / "templates"
TOOL_HOST_TEMPLATES = CHART_DIR / "charts" / "dp-tool-host" / "templates"

# The 4 main service deployments managed by the parent chart, plus the
# dp-tool-host subchart's host pod. All five must carry the same
# baseline hardening.
PARENT_DEPLOYMENTS = [
    TEMPLATES / "control-plane.yaml",
    TEMPLATES / "runtime.yaml",
    TEMPLATES / "gateway.yaml",
    TEMPLATES / "kb-engine.yaml",
]
DP_TOOL_HOST_DEPLOYMENT = TOOL_HOST_TEMPLATES / "deployment.yaml"


@pytest.mark.parametrize("path", PARENT_DEPLOYMENTS)
def test_parent_deployment_uses_pod_security_helper(path: Path) -> None:
    """P0.6g: pod-level securityContext via the shared helper."""
    body = path.read_text(encoding="utf-8")
    assert 'include "loop.podSecurityContext"' in body, (
        f"{path.name}: pod-level securityContext helper missing"
    )


@pytest.mark.parametrize("path", PARENT_DEPLOYMENTS)
def test_parent_deployment_uses_container_security_helper(path: Path) -> None:
    """P0.6g: container-level hardening (readOnlyRootFilesystem,
    drop ALL caps, allowPrivilegeEscalation: false)."""
    body = path.read_text(encoding="utf-8")
    assert 'include "loop.containerSecurityContext"' in body, (
        f"{path.name}: container-level securityContext helper missing"
    )


@pytest.mark.parametrize("path", PARENT_DEPLOYMENTS)
def test_parent_deployment_has_startup_probe(path: Path) -> None:
    """P1: slow Python imports need a startupProbe so the kubelet
    doesn't kill cold-starting pods."""
    body = path.read_text(encoding="utf-8")
    assert 'include "loop.startupProbe"' in body, (
        f"{path.name}: startupProbe helper missing"
    )


@pytest.mark.parametrize("path", PARENT_DEPLOYMENTS)
def test_parent_deployment_has_anti_affinity(path: Path) -> None:
    """P1: pod anti-affinity so the scheduler spreads replicas across
    zones / nodes instead of stacking them on one box."""
    body = path.read_text(encoding="utf-8")
    assert 'include "loop.podAntiAffinity"' in body, (
        f"{path.name}: podAntiAffinity helper missing"
    )


@pytest.mark.parametrize("path", PARENT_DEPLOYMENTS)
def test_parent_deployment_has_pre_stop_drain(path: Path) -> None:
    """P1: 10s preStop sleep + 60s graceful shutdown so SSE streams
    drain instead of being guillotined at the default 30s."""
    body = path.read_text(encoding="utf-8")
    assert 'include "loop.preStopHook"' in body, (
        f"{path.name}: preStop hook helper missing"
    )
    assert 'include "loop.gracefulShutdown"' in body, (
        f"{path.name}: gracefulShutdown helper missing"
    )


def test_helpers_define_all_security_macros() -> None:
    """The helper template must define every macro the deployments
    reference. Catches a missing/typo'd macro before helm-lint."""
    helpers = (TEMPLATES / "_helpers.tpl").read_text(encoding="utf-8")
    required_macros = [
        '"loop.podSecurityContext"',
        '"loop.containerSecurityContext"',
        '"loop.startupProbe"',
        '"loop.podAntiAffinity"',
        '"loop.gracefulShutdown"',
        '"loop.preStopHook"',
        '"loop.writableTmpVolumeMounts"',
        '"loop.writableTmpVolumes"',
    ]
    for macro in required_macros:
        assert f"define {macro}" in helpers, f"missing macro: {macro}"


def test_pod_security_context_runs_nonroot() -> None:
    """The pod-level helper must set `runAsNonRoot: true` and a
    non-zero UID."""
    helpers = (TEMPLATES / "_helpers.tpl").read_text(encoding="utf-8")
    pod_macro_start = helpers.find('define "loop.podSecurityContext"')
    pod_macro_end = helpers.find('{{- end -}}', pod_macro_start)
    pod_macro = helpers[pod_macro_start:pod_macro_end]
    assert "runAsNonRoot: true" in pod_macro
    assert "runAsUser: 65532" in pod_macro
    assert "seccompProfile" in pod_macro
    assert "RuntimeDefault" in pod_macro


def test_container_security_context_drops_all_caps_and_readonly_fs() -> None:
    helpers = (TEMPLATES / "_helpers.tpl").read_text(encoding="utf-8")
    start = helpers.find('define "loop.containerSecurityContext"')
    end = helpers.find('{{- end -}}', start)
    macro = helpers[start:end]
    assert "readOnlyRootFilesystem: true" in macro
    assert "allowPrivilegeEscalation: false" in macro
    assert "drop:" in macro
    assert "- ALL" in macro


def test_dp_tool_host_deployment_is_hardened() -> None:
    """Subchart can't include parent helpers, so we verify the
    inline equivalents are present."""
    body = DP_TOOL_HOST_DEPLOYMENT.read_text(encoding="utf-8")
    # Pod-level
    assert "runAsNonRoot: true" in body
    assert "runAsUser: 65532" in body
    assert "seccompProfile:" in body and "RuntimeDefault" in body
    # Container-level
    assert "readOnlyRootFilesystem: true" in body
    assert "allowPrivilegeEscalation: false" in body
    assert "drop:" in body and "- ALL" in body
    # Startup probe + drain
    assert "startupProbe:" in body
    assert "terminationGracePeriodSeconds: 60" in body
    assert "preStop:" in body


def test_dp_tool_host_has_pdb_template() -> None:
    """Closes P1: dp-tool-host had no PDB template at all."""
    pdb = TOOL_HOST_TEMPLATES / "pdb.yaml"
    assert pdb.is_file(), "dp-tool-host pdb.yaml missing"
    body = pdb.read_text(encoding="utf-8")
    assert "kind: PodDisruptionBudget" in body
    assert "podDisruptionBudget.enabled" in body


def test_dp_tool_host_has_hpa_template() -> None:
    """Closes P1: dp-tool-host had no HPA template at all."""
    hpa = TOOL_HOST_TEMPLATES / "hpa.yaml"
    assert hpa.is_file(), "dp-tool-host hpa.yaml missing"
    body = hpa.read_text(encoding="utf-8")
    assert "kind: HorizontalPodAutoscaler" in body
    assert "autoscaling.enabled" in body


def test_network_policies_template_exists() -> None:
    """P0.6h: NetworkPolicy template must exist and cover all 4 main
    services."""
    np = TEMPLATES / "network-policies.yaml"
    assert np.is_file(), "network-policies.yaml missing"
    body = np.read_text(encoding="utf-8")
    assert "kind: NetworkPolicy" in body
    for component in ("control-plane", "runtime", "gateway", "kb-engine"):
        assert f"app.kubernetes.io/component: {component}" in body, (
            f"NetworkPolicy missing component selector for {component}"
        )
    # Default-deny is implied via policyTypes; assert both directions
    # are gated on every policy.
    assert body.count("policyTypes:") >= 4
    assert body.count("- Ingress") >= 4
    assert body.count("- Egress") >= 4


def test_network_policies_have_skip_toggle() -> None:
    """Operators in CNI-less clusters must be able to disable."""
    body = (TEMPLATES / "network-policies.yaml").read_text(encoding="utf-8")
    assert "networkPolicies.enabled" in body


def test_values_includes_network_policies_block() -> None:
    """The values.yaml must declare the new networkPolicies key with
    an explicit default so `helm install --debug` doesn't render
    `<no value>`."""
    body = (CHART_DIR / "values.yaml").read_text(encoding="utf-8")
    assert "networkPolicies:" in body
    assert "enabled: true" in body

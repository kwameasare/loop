"""Tests for ingress + cert-manager + nginx/traefik defaults (S452).

S452 AC: helm install w/ ingress=true creates TLS-terminated routes;
verified on kind. We render the ingress template via `helm template`
and assert the cert-manager annotation + TLS block appear, and that
the ingressClassName toggles correctly between nginx and traefik.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART = ROOT / "infra" / "helm" / "loop"


def _have_helm() -> bool:
    return shutil.which("helm") is not None


def _render(extra: list[str]) -> list[dict[str, object]]:
    cmd = ["helm", "template", "loop", str(CHART), "-s", "templates/ingress.yaml", *extra]
    out = subprocess.check_output(cmd, text=True)
    return [d for d in yaml.safe_load_all(out) if d]


def test_ingress_template_exists() -> None:
    assert (CHART / "templates" / "ingress.yaml").is_file()


def test_values_expose_cert_manager_and_classname() -> None:
    values = yaml.safe_load((CHART / "values.yaml").read_text())
    ingress = values["ingress"]
    assert ingress["enabled"] is False  # opt-in
    assert ingress["className"] in {"nginx", "traefik"}
    cm = ingress["certManager"]
    assert cm["enabled"] is False
    assert cm["clusterIssuer"]
    assert cm["tlsSecretName"]


@pytest.mark.skipif(not _have_helm(), reason="helm CLI not available")
def test_helm_template_nginx_with_cert_manager_renders_tls() -> None:
    docs = _render(
        [
            "--set", "ingress.enabled=true",
            "--set", "ingress.className=nginx",
            "--set", "ingress.certManager.enabled=true",
            "--set", "ingress.host=loop.example.com",
        ]
    )
    assert docs, "ingress should render"
    ing = docs[0]
    assert ing["kind"] == "Ingress"
    spec = ing["spec"]
    assert spec["ingressClassName"] == "nginx"
    tls = spec["tls"]
    assert tls and tls[0]["hosts"] == ["loop.example.com"]
    assert tls[0]["secretName"] == "loop-tls"
    annotations = ing["metadata"]["annotations"]
    assert annotations["cert-manager.io/cluster-issuer"] == "letsencrypt-prod"
    assert "nginx.ingress.kubernetes.io/ssl-redirect" in annotations


@pytest.mark.skipif(not _have_helm(), reason="helm CLI not available")
def test_helm_template_traefik_with_cert_manager_renders_traefik_tls() -> None:
    docs = _render(
        [
            "--set", "ingress.enabled=true",
            "--set", "ingress.className=traefik",
            "--set", "ingress.certManager.enabled=true",
        ]
    )
    ing = docs[0]
    assert ing["spec"]["ingressClassName"] == "traefik"
    annotations = ing["metadata"]["annotations"]
    assert annotations["cert-manager.io/cluster-issuer"] == "letsencrypt-prod"
    assert annotations["traefik.ingress.kubernetes.io/router.tls"] == "true"


@pytest.mark.skipif(not _have_helm(), reason="helm CLI not available")
def test_helm_template_disabled_renders_nothing() -> None:
    docs = _render(["--set", "ingress.enabled=false"])
    assert docs == []

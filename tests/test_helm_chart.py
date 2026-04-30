"""Smoke tests for tools/check_helm_chart.py (S036)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import check_helm_chart  # type: ignore[import-not-found]


def test_committed_chart_is_structurally_sound() -> None:
    errors = check_helm_chart.check_chart()
    assert errors == [], f"helm chart errors: {errors}"


def test_missing_required_value_is_caught(tmp_path: Path) -> None:
    """If we strip a required key from values.yaml, the validator complains."""
    chart_dir = ROOT / "infra" / "helm" / "loop"
    target = tmp_path / "loop"
    target.mkdir()
    (target / "Chart.yaml").write_text((chart_dir / "Chart.yaml").read_text())
    # values.yaml without the required `externals.postgresUrl`
    (target / "values.yaml").write_text(
        "global:\n"
        "  imageRegistry: x\n"
        "  imagePullPolicy: IfNotPresent\n"
        "controlPlane: {enabled: true, replicaCount: 1, "
        "image: {repository: cp, tag: v}, "
        "service: {port: 8080}, resources: {}}\n"
        "runtime: {enabled: true, image: {repository: rt, tag: v}, "
        "service: {port: 8081}}\n"
        "gateway: {enabled: true, image: {repository: gw, tag: v}, "
        "service: {port: 8082}}\n"
        "externals:\n"
        "  redisUrl: r\n"
        "  qdrantUrl: q\n"
        "  natsUrl: n\n"
        "  s3Endpoint: s\n"
        "  otelEndpoint: o\n"
        "secrets: {llmApiKey: '', jwtSigningKey: ''}\n"
        "ingress: {enabled: false}\n"
        "serviceAccount: {create: true}\n"
    )
    # Empty templates dir -> all template files are missing.
    (target / "templates").mkdir()

    errors = check_helm_chart.check_chart(target)
    assert any("externals.postgresUrl" in e for e in errors), errors
    assert any("missing template: templates/control-plane.yaml" in e for e in errors), errors

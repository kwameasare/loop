"""Shape checks for the loop-observability Helm chart and bundled assets."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
CHART_DIR = ROOT / "infra" / "helm" / "loop-observability"
CHART_YAML = CHART_DIR / "Chart.yaml"
VALUES_YAML = CHART_DIR / "values.yaml"


def _load_yaml(path: Path) -> dict[Any, Any]:
    return cast(dict[Any, Any], yaml.safe_load(path.read_text()))


def test_chart_pins_required_observability_dependencies() -> None:
    chart = _load_yaml(CHART_YAML)
    deps = cast(list[dict[str, str]], chart["dependencies"])
    dep_names = {dep["name"] for dep in deps}

    assert dep_names == {"kube-prometheus-stack", "loki", "tempo", "falco"}
    assert all(dep.get("version") for dep in deps)


def test_values_wire_alertmanager_and_falco_sidekick() -> None:
    values = VALUES_YAML.read_text()

    assert "source=\"falco\"" in values
    assert "receiver: falco-events" in values
    assert "falcosidekick:" in values
    assert "hostport: loop-observability-kube-prometheus-stack-alertmanager:9093" in values


def test_chart_bundles_and_syncs_canonical_rule_and_dashboard_files() -> None:
    assert (ROOT / "infra" / "falco" / "loop_rules.yaml").read_text() == (
        CHART_DIR / "files" / "falco" / "loop_rules.yaml"
    ).read_text()
    assert (ROOT / "infra" / "prometheus" / "alerts" / "slo-burn.yaml").read_text() == (
        CHART_DIR / "files" / "prometheus" / "slo-burn.yaml"
    ).read_text()
    assert (ROOT / "infra" / "grafana" / "loop-platform-overview.json").read_text() == (
        CHART_DIR / "files" / "dashboards" / "loop-platform-overview.json"
    ).read_text()
    assert (ROOT / "infra" / "grafana" / "loop-slo-burn.json").read_text() == (
        CHART_DIR / "files" / "dashboards" / "loop-slo-burn.json"
    ).read_text()


def test_shell_spawned_smoke_rule_exists_in_falco_rules() -> None:
    text = (ROOT / "infra" / "falco" / "loop_rules.yaml").read_text()

    assert "- rule: shell-spawned-in-pod" in text
    assert "k8s.pod.name startswith \"falco-smoke\"" in text

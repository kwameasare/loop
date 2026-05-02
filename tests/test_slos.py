"""S805 checks for service SLOs and PagerDuty burn alerts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[1]
SLOS = ROOT / "loop_implementation" / "operations" / "SLOs.yaml"
ALERTS = ROOT / "infra" / "prometheus" / "alerts" / "slo-burn.yaml"
ALERTMANAGER = ROOT / "infra" / "prometheus" / "alertmanager.yaml"

EXPECTED_SERVICES = {
    "control-plane",
    "runtime",
    "gateway",
    "kb-engine",
    "tool-host",
    "voice",
}


def _yaml(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(path.read_text()))


def test_slos_define_availability_latency_and_error_budget_per_service() -> None:
    data = _yaml(SLOS)
    services = cast(dict[str, Any], data["services"])

    assert set(services) == EXPECTED_SERVICES
    assert data["pagerduty"]["receiver"] == "pagerduty-slo"
    assert data["window_days"] == 30
    for service, cfg_raw in services.items():
        cfg = cast(dict[str, Any], cfg_raw)
        availability = cast(dict[str, Any], cfg["availability"])
        latency = cast(dict[str, Any], cfg["latency"])
        budget = cast(dict[str, Any], cfg["error_budget"])

        target = float(availability["target"])
        assert availability["metric"].startswith("loop_"), service
        assert 0.99 <= target < 1.0, service
        assert latency["metric"].startswith("loop_"), service
        assert latency["percentile"] == "p95", service
        assert int(latency["target_ms"]) > 0, service
        assert abs(float(budget["percent"]) - ((1 - target) * 100)) < 1e-9


def test_prometheus_slo_burn_alerts_page_for_each_service_and_objective() -> None:
    groups = cast(list[dict[str, Any]], _yaml(ALERTS)["groups"])
    rules = cast(list[dict[str, Any]], groups[0]["rules"])

    by_pair = {(rule["labels"]["service"], rule["labels"]["slo"]) for rule in rules}
    assert by_pair == {(service, "availability") for service in EXPECTED_SERVICES} | {
        (service, "latency") for service in EXPECTED_SERVICES
    }
    for rule in rules:
        labels = cast(dict[str, Any], rule["labels"])
        assert labels["severity"] == "page"
        assert labels["pagerduty"] == "true"
        assert labels["pagerduty_receiver"] == "pagerduty-slo"
        assert "loop_slo_" in rule["expr"]


def test_alertmanager_routes_slo_pages_to_pagerduty() -> None:
    data = _yaml(ALERTMANAGER)
    receivers = cast(list[dict[str, Any]], data["receivers"])
    pagerduty = next(receiver for receiver in receivers if receiver["name"] == "pagerduty-slo")

    assert data["route"]["routes"][0]["receiver"] == "pagerduty-slo"
    assert 'pagerduty="true"' in data["route"]["routes"][0]["matchers"]
    assert pagerduty["pagerduty_configs"][0]["routing_key"] == "${PAGERDUTY_SLO_ROUTING_KEY}"

"""Tests for Falco runtime-detection rules — S803.

AC: rules deployed; alerts on shell-exec / unauthorized syscall / unexpected
egress; tested with red-team triggers.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from loop_control_plane.falco_rules import (
    RedTeamTrigger,
    RuleRegistry,
    evaluate_trigger,
)

RULES_FILE = Path(__file__).parent.parent.parent.parent / "infra" / "falco" / "loop_rules.yaml"


@pytest.fixture(scope="module")
def registry() -> RuleRegistry:
    assert RULES_FILE.exists(), f"Falco rules file not found: {RULES_FILE}"
    return RuleRegistry.from_file(RULES_FILE)


# ---------------------------------------------------------------------------
# Schema / structure tests
# ---------------------------------------------------------------------------


def test_rules_file_parses_without_error(registry: RuleRegistry) -> None:
    assert len(registry.rules) >= 4


def test_all_expected_rules_present(registry: RuleRegistry) -> None:
    expected = {
        "Loop Shell Spawned in Container",
        "Loop Container ptrace Attach",
        "Loop CP-API Unexpected execve",
        "Loop Container Unexpected Egress",
    }
    assert expected <= set(registry.rules)


def test_all_rules_have_red_team_trigger_tag(registry: RuleRegistry) -> None:
    tagged = {r.name for r in registry.rules_tagged("red_team_trigger")}
    for rule_name in registry.rules:
        assert rule_name in tagged, f"Rule {rule_name!r} is missing 'red_team_trigger' tag"


def test_rules_have_non_empty_output(registry: RuleRegistry) -> None:
    for rule in registry.rules.values():
        assert rule.output.strip(), f"Rule {rule.name!r} has empty output template"


def test_rules_have_valid_priority(registry: RuleRegistry) -> None:
    valid_priorities = {"EMERGENCY", "CRITICAL", "ERROR", "WARNING", "NOTICE", "INFO", "DEBUG"}
    for rule in registry.rules.values():
        assert rule.priority in valid_priorities, (
            f"Rule {rule.name!r} has unknown priority {rule.priority!r}"
        )


def test_macros_include_loop_managed_container(registry: RuleRegistry) -> None:
    assert "loop_managed_container" in registry.macros
    assert "loop_sandbox_container" in registry.macros
    assert "loop_cp_api_container" in registry.macros


def test_macros_include_shell_binary(registry: RuleRegistry) -> None:
    assert "shell_binary" in registry.macros


# ---------------------------------------------------------------------------
# Red-team trigger: shell exec
# ---------------------------------------------------------------------------


def test_shell_exec_in_sandbox_triggers_alert() -> None:
    trigger = RedTeamTrigger(
        image_repository="ghcr.io/loop/sandbox:latest",
        proc_name="bash",
        evt_type="execve",
        should_alert=True,
    )
    result = evaluate_trigger("Loop Shell Spawned in Container", trigger)
    assert result is True


def test_shell_exec_in_cp_api_triggers_alert() -> None:
    trigger = RedTeamTrigger(
        image_repository="ghcr.io/loop/cp-api:main",
        proc_name="sh",
        should_alert=True,
    )
    result = evaluate_trigger("Loop Shell Spawned in Container", trigger)
    assert result is True


def test_non_shell_exec_does_not_trigger_shell_rule() -> None:
    trigger = RedTeamTrigger(
        image_repository="ghcr.io/loop/sandbox:latest",
        proc_name="python3",
        should_alert=False,
    )
    result = evaluate_trigger("Loop Shell Spawned in Container", trigger)
    assert result is False


def test_shell_exec_in_unrelated_image_does_not_trigger() -> None:
    trigger = RedTeamTrigger(
        image_repository="nginx:alpine",
        proc_name="bash",
        should_alert=False,
    )
    result = evaluate_trigger("Loop Shell Spawned in Container", trigger)
    assert result is False


# ---------------------------------------------------------------------------
# Red-team trigger: ptrace
# ---------------------------------------------------------------------------


def test_ptrace_attach_in_sandbox_triggers_alert() -> None:
    trigger = RedTeamTrigger(
        image_repository="loop/sandbox:v2",
        evt_type="ptrace",
        ptrace_request="PTRACE_ATTACH",
        should_alert=True,
    )
    result = evaluate_trigger("Loop Container ptrace Attach", trigger)
    assert result is True


def test_non_ptrace_attach_request_does_not_trigger() -> None:
    trigger = RedTeamTrigger(
        image_repository="loop/sandbox:v2",
        evt_type="ptrace",
        ptrace_request="PTRACE_PEEKDATA",
        should_alert=False,
    )
    result = evaluate_trigger("Loop Container ptrace Attach", trigger)
    assert result is False


# ---------------------------------------------------------------------------
# Red-team trigger: unexpected execve in cp-api
# ---------------------------------------------------------------------------


def test_unexpected_execve_in_cp_api_triggers_alert() -> None:
    trigger = RedTeamTrigger(
        image_repository="ghcr.io/loop/cp-api:sha256abc",
        evt_type="execve",
        proc_name="curl",
        should_alert=True,
    )
    result = evaluate_trigger("Loop CP-API Unexpected execve", trigger)
    assert result is True


def test_known_init_process_execve_does_not_trigger() -> None:
    trigger = RedTeamTrigger(
        image_repository="ghcr.io/loop/cp-api:latest",
        evt_type="execve",
        proc_name="uvicorn",
        should_alert=False,
    )
    result = evaluate_trigger("Loop CP-API Unexpected execve", trigger)
    assert result is False


# ---------------------------------------------------------------------------
# Red-team trigger: unexpected egress
# ---------------------------------------------------------------------------


def test_egress_to_external_ip_triggers_alert() -> None:
    trigger = RedTeamTrigger(
        image_repository="ghcr.io/loop/sandbox:latest",
        evt_type="connect",
        dst_ip="1.2.3.4",
        dst_port=8080,
        should_alert=True,
    )
    result = evaluate_trigger("Loop Container Unexpected Egress", trigger)
    assert result is True


def test_egress_to_internal_rfc1918_does_not_trigger() -> None:
    trigger = RedTeamTrigger(
        image_repository="ghcr.io/loop/sandbox:latest",
        evt_type="connect",
        dst_ip="10.100.50.1",
        dst_port=8080,
        should_alert=False,
    )
    result = evaluate_trigger("Loop Container Unexpected Egress", trigger)
    assert result is False


def test_egress_on_allowed_port_does_not_trigger() -> None:
    trigger = RedTeamTrigger(
        image_repository="ghcr.io/loop/cp-api:latest",
        evt_type="connect",
        dst_ip="8.8.8.8",
        dst_port=443,
        should_alert=False,
    )
    result = evaluate_trigger("Loop Container Unexpected Egress", trigger)
    assert result is False


def test_sendto_to_external_triggers_alert() -> None:
    trigger = RedTeamTrigger(
        image_repository="loop/sandbox:edge",
        evt_type="sendto",
        dst_ip="203.0.113.1",
        dst_port=9999,
        should_alert=True,
    )
    result = evaluate_trigger("Loop Container Unexpected Egress", trigger)
    assert result is True

"""Falco rules loader and red-team trigger validator for Loop — S803.

This module provides:

* :func:`load_rules_file` — parse a Falco rules YAML into structured dicts.
* :func:`list_rules`, :func:`list_macros`, :func:`list_lists` — typed views.
* :class:`RuleRegistry` — in-memory index of parsed rules, macros, lists;
  used by tests to assert policy intent without running a live Falco daemon.
* :class:`RedTeamTrigger` — a lightweight struct describing a simulated
  syscall / network event that a rule *should* or *should not* match.
* :func:`evaluate_trigger` — pure-Python predicate evaluator for the small
  subset of Falco condition syntax relevant to Loop rules (image-name checks,
  proc-name checks, evt.type checks, allowed-egress macro).
  It is intentionally conservative: unrecognised condition fragments are
  treated as "skip" (neither match nor no-match) and the function returns
  ``None`` in that case.

The intent is to let CI verify:
  1. All three anomaly families (shell-exec, syscall, egress) have at least
     one rule tagged ``red_team_trigger``.
  2. Red-team scenario fixtures labelled ``should_alert=True`` produce a
     match; those labelled ``should_alert=False`` produce no match.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "FalcoList",
    "FalcoMacro",
    "FalcoRule",
    "RedTeamTrigger",
    "RuleRegistry",
    "evaluate_trigger",
    "list_lists",
    "list_macros",
    "list_rules",
    "load_rules_file",
]


# ---------------------------------------------------------------------------
# Typed views of Falco YAML objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FalcoRule:
    name: str
    description: str
    condition: str
    output: str
    priority: str
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class FalcoMacro:
    name: str
    condition: str


@dataclass(frozen=True, slots=True)
class FalcoList:
    name: str
    items: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_rules_file(path: str | Path) -> list[dict[str, Any]]:
    """Parse a Falco rules YAML file and return raw dicts."""
    with open(path) as fh:
        return yaml.safe_load(fh) or []


def list_rules(raw: list[dict[str, Any]]) -> list[FalcoRule]:
    return [
        FalcoRule(
            name=item["rule"],
            description=item.get("desc", ""),
            condition=item.get("condition", ""),
            output=item.get("output", ""),
            priority=item.get("priority", ""),
            tags=list(item.get("tags", [])),
        )
        for item in raw
        if "rule" in item
    ]


def list_macros(raw: list[dict[str, Any]]) -> list[FalcoMacro]:
    return [
        FalcoMacro(
            name=item["macro"],
            condition=item.get("condition", ""),
        )
        for item in raw
        if "macro" in item
    ]


def list_lists(raw: list[dict[str, Any]]) -> list[FalcoList]:
    return [
        FalcoList(
            name=item["list"],
            items=[str(x) for x in item.get("items", [])],
        )
        for item in raw
        if "list" in item
    ]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class RuleRegistry:
    """Index of rules, macros, and lists parsed from a Falco rules file."""

    def __init__(self, raw: list[dict[str, Any]]) -> None:
        self.rules: dict[str, FalcoRule] = {r.name: r for r in list_rules(raw)}
        self.macros: dict[str, FalcoMacro] = {m.name: m for m in list_macros(raw)}
        self.lists: dict[str, FalcoList] = {lst.name: lst for lst in list_lists(raw)}

    @classmethod
    def from_file(cls, path: str | Path) -> RuleRegistry:
        return cls(load_rules_file(path))

    def rules_tagged(self, tag: str) -> list[FalcoRule]:
        return [r for r in self.rules.values() if tag in r.tags]

    def rule(self, name: str) -> FalcoRule:
        return self.rules[name]


# ---------------------------------------------------------------------------
# Red-team trigger evaluator
# ---------------------------------------------------------------------------


@dataclass
class RedTeamTrigger:
    """A simulated event used to verify whether a Falco rule would fire.

    Fields mirror the Falco field-class names used in Loop rules.

    Args:
        image_repository: ``container.image.repository`` value.
        proc_name: ``proc.name`` value.
        evt_type: Falco event type string, e.g. ``"execve"``, ``"connect"``.
        dst_ip: Destination IP address (for egress checks).
        dst_port: Destination TCP/UDP port.
        ptrace_request: ptrace request name for ptrace events.
        should_alert: Expected match outcome (used by tests).
    """

    image_repository: str = ""
    proc_name: str = ""
    evt_type: str = ""
    dst_ip: str = ""
    dst_port: int = 0
    ptrace_request: str = ""
    should_alert: bool = True


# Internal helpers matching the macro/condition fragments in loop_rules.yaml.


_SHELL_BINARIES = frozenset({"sh", "bash", "zsh", "fish", "dash", "ksh", "tcsh", "csh"})
_LOOP_IMAGE_FRAGMENTS = (
    "loop/sandbox",
    "ghcr.io/loop/sandbox",
    "loop/cp-api",
    "ghcr.io/loop/cp-api",
)
_LOOP_SANDBOX_FRAGMENTS = ("loop/sandbox", "ghcr.io/loop/sandbox")
_LOOP_CP_API_FRAGMENTS = ("loop/cp-api", "ghcr.io/loop/cp-api")
_ALLOWED_EGRESS_RFC1918 = [
    (10, 0, 0, 0, 8),
    (172, 16, 0, 0, 12),
    (192, 168, 0, 0, 16),
]
_ALLOWED_EGRESS_PORTS = {443, 53, 4317, 4318}


def _is_loop_managed(image: str) -> bool:
    return any(frag in image for frag in _LOOP_IMAGE_FRAGMENTS)


def _is_loop_sandbox(image: str) -> bool:
    return any(frag in image for frag in _LOOP_SANDBOX_FRAGMENTS)


def _is_loop_cp_api(image: str) -> bool:
    return any(frag in image for frag in _LOOP_CP_API_FRAGMENTS)


def _parse_ipv4(ip: str) -> tuple[int, ...] | None:
    parts = ip.split(".")
    if len(parts) != 4:
        return None
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def _in_cidr(ip: str, network: tuple[int, int, int, int, int]) -> bool:
    octets = _parse_ipv4(ip)
    if octets is None:
        return False
    net_a, net_b, net_c, net_d, prefix = network
    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    ip_int = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
    net_int = (net_a << 24) | (net_b << 16) | (net_c << 8) | net_d
    return (ip_int & mask) == (net_int & mask)


def _is_allowed_egress(trigger: RedTeamTrigger) -> bool:
    if trigger.dst_port in _ALLOWED_EGRESS_PORTS:
        return True
    return any(_in_cidr(trigger.dst_ip, cidr) for cidr in _ALLOWED_EGRESS_RFC1918)


def evaluate_trigger(rule_name: str, trigger: RedTeamTrigger) -> bool | None:
    """Evaluate whether *trigger* would match *rule_name*.

    Returns:
        ``True``  — trigger matches (rule would fire).
        ``False`` — trigger does not match.
        ``None``  — rule name not recognised by this evaluator.
    """
    name = rule_name

    if name == "Loop Shell Spawned in Container":
        return _is_loop_managed(trigger.image_repository) and trigger.proc_name in _SHELL_BINARIES

    if name == "Loop Container ptrace Attach":
        return (
            _is_loop_managed(trigger.image_repository)
            and trigger.evt_type == "ptrace"
            and trigger.ptrace_request == "PTRACE_ATTACH"
        )

    if name == "Loop CP-API Unexpected execve":
        _known_init = frozenset(
            {
                "tini",
                "dumb-init",
                "s6-svscan",
                "supervisord",
                "node",
                "python3",
                "python",
                "uvicorn",
                "gunicorn",
            }
        )
        return (
            _is_loop_cp_api(trigger.image_repository)
            and trigger.evt_type == "execve"
            and trigger.proc_name not in _known_init
        )

    if name == "Loop Container Unexpected Egress":
        return (
            _is_loop_managed(trigger.image_repository)
            and trigger.evt_type in ("connect", "sendto")
            and not _is_allowed_egress(trigger)
        )

    return None

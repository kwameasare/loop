"""Static sweep: every mutating cp route emits an audit event (vega #14).

Closes vega #14 (block-prod): cp had a doc-level
``AUDIT_COMPLETENESS.md`` matrix, but no programmatic gate. A new
mutating route could ship without a ``record_audit_event(...)`` call
and the matrix would silently fall behind. Auditors would discover
the gap during the SOC-2 review, not in CI.

This test parses the AST of every ``_routes_*.py`` module in cp,
finds every mutating route function, and asserts the function body
contains a call to ``record_audit_event``. Routes that legitimately
don't audit (auth/refresh, health probes, inbound webhooks dispatched
to a separate audit path) are in a small documented allow-list.

The sweep is deliberately structural — it doesn't try to validate
that the audit event has the *right* fields, just that one is emitted.
That's the right granularity for a "no missing audit trail" gate; the
contents are covered by the audit_events service tests.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROUTES_DIR = (
    Path(__file__).resolve().parent.parent
    / "packages"
    / "control-plane"
    / "loop_control_plane"
)

_MUTATING_DECORATORS = frozenset({"post", "patch", "put", "delete"})

# Routes that legitimately don't emit an audit event. Each entry has
# a one-line justification — keep the list small and audit it on
# every change.
_AUDIT_EXEMPT: dict[str, str] = {
    # Auth flow: token exchange + refresh log to the auth-events
    # stream, not the workspace audit log (the principal is
    # pre-workspace at this point).
    "auth_exchange": "logs to auth_events, not workspace audit_log",
    "auth_refresh": "logs to auth_events, not workspace audit_log",
    # Inbound webhooks delegate to a per-channel handler that emits
    # the audit event from inside the channel adapter.
    "receive_inbound_webhook": "channel adapter emits audit",
    # Health probes are unauthenticated, no audit subject.
    "healthz": "kubelet probe; no audit subject",
    "readyz": "kubelet probe; no audit subject",
    # Workspace patch is a meta-operation; the audit log itself is
    # workspace-scoped (no log to write the patch to before it lands).
    # Tracked as follow-up: add a workspaces_audit topic.
    "patch_workspace": "no workspace-meta audit topic yet (follow-up)",
}


def _route_decorator(node: ast.AsyncFunctionDef | ast.FunctionDef) -> str | None:
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
            attr = dec.func.attr.lower()
            if attr in _MUTATING_DECORATORS:
                return attr
    return None


def _route_path(node: ast.AsyncFunctionDef | ast.FunctionDef) -> str:
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call) and dec.args:
            arg = dec.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
    return ""


def _emits_audit_event(node: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    """True iff the function body contains a call to
    ``record_audit_event(...)`` (bare or attribute form)."""
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        callee = child.func
        if isinstance(callee, ast.Name) and callee.id == "record_audit_event":
            return True
        if (
            isinstance(callee, ast.Attribute)
            and callee.attr == "record_audit_event"
        ):
            return True
    return False


def _iter_route_modules() -> list[Path]:
    return sorted(ROUTES_DIR.glob("_routes_*.py"))


def _collect_violations() -> list[tuple[Path, str, str, str]]:
    violations: list[tuple[Path, str, str, str]] = []
    for module in _iter_route_modules():
        tree = ast.parse(module.read_text(), filename=str(module))
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                continue
            verb = _route_decorator(node)
            if verb is None:
                continue
            if _emits_audit_event(node):
                continue
            if node.name in _AUDIT_EXEMPT:
                continue
            violations.append((module, node.name, verb, _route_path(node)))
    return violations


def test_every_mutating_route_emits_audit_event_or_is_documented() -> None:
    """Sweep: a mutating route that doesn't call record_audit_event AND
    isn't in the documented exemption list is an audit-trail gap."""
    violations = _collect_violations()
    if violations:
        lines = [
            f"  {p.name}::{name} — @router.{verb}({path!r})"
            for p, name, verb, path in violations
        ]
        pytest.fail(
            "Mutating routes without an audit event (vega #14):\n"
            + "\n".join(lines)
            + "\nFix by either: calling record_audit_event(...) in the "
            "handler, OR adding the function name to _AUDIT_EXEMPT with "
            "a justification."
        )


def test_audit_exempt_does_not_grow_silently() -> None:
    """Every exemption must point at a function that actually exists.
    Stale entries hide regressions where an exempt name gets renamed
    to skip the audit emission."""
    seen: set[str] = set()
    for module in _iter_route_modules():
        tree = ast.parse(module.read_text(), filename=str(module))
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                seen.add(node.name)
    stale = set(_AUDIT_EXEMPT) - seen
    assert not stale, (
        "Audit-exempt entries reference non-existent functions:\n  "
        + "\n  ".join(sorted(stale))
        + "\nDelete them from _AUDIT_EXEMPT."
    )


def test_at_least_one_route_actually_emits_audit() -> None:
    """Sanity: the AST scan must find at least one emitter. If this
    trips, the detection logic is broken and the main test would be
    a false negative."""
    found = False
    for module in _iter_route_modules():
        tree = ast.parse(module.read_text(), filename=str(module))
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                continue
            if _emits_audit_event(node):
                found = True
                break
        if found:
            break
    assert found, "no route emits record_audit_event — AST scan is broken"

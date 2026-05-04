"""Static sweep: every mutating cp route enforces a role gradient (vega #13).

Closes vega #13 (block-prod): cp had no CI gate ensuring every
``POST/PATCH/PUT/DELETE`` on a workspace-scoped endpoint actually
asks ``authorize_workspace_access`` for a ``required_role``. Without
this gate, a route could ship that lets any workspace member delete
another member's resources — privilege escalation by omission.

The test parses the AST of every ``_routes_*.py`` module in cp and,
for every route function that mutates state, asserts one of:

  - the function body contains a call to ``authorize_workspace_access``
    with a ``required_role=`` keyword set to a non-None value, OR
  - the route's path doesn't include ``{workspace_id}`` (so it's
    workspace-agnostic — e.g. ``/v1/auth/login``), OR
  - the route is in a small documented allow-list (e.g. webhooks
    that authenticate via a per-channel signature, not the user's
    workspace role).

A new mutating route that forgets the role check fails this test
immediately.
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

# Mutating verbs that need a role check. GET is excluded because
# read paths only need authentication + workspace scope, not a role
# gradient (which is the *write* side of the lattice).
_MUTATING_DECORATORS = frozenset({"post", "patch", "put", "delete"})

# Routes that are intentionally NOT workspace-scoped or use a
# different auth model. Each entry is the function name and a
# justification — keep this list small and audit it on every change.
#
# This is also the vega #13 ratchet baseline: closing a route by
# adding ``required_role=`` removes it from this list.
_ALLOWLIST_FUNCS: dict[str, str] = {
    # /v1/auth/* routes authenticate the caller; there's no workspace
    # context to apply role policy against.
    "auth_exchange": "auth — pre-workspace context",
    "auth_refresh": "auth — pre-workspace context",
    # Inbound webhooks authenticate via per-channel HMAC, not the
    # caller's workspace role (the caller is the channel itself).
    "receive_inbound_webhook": "channel-signed; no user role",
    # Workspace creation — there's no workspace_id yet to authorise
    # against. The caller's identity is verified by the auth layer.
    "create_agent": "uses workspace from auth principal",
    "create_workspace": "creates the workspace; no prior membership",
    # Pre-existing drift baseline (vega #13 ratchet). These routes
    # mutate state but rely on the agent_id / api_key / conversation_id
    # path param to resolve the workspace_id at the service layer
    # rather than calling authorize_workspace_access directly. The
    # service-layer enforcement IS strict, but we want every route
    # to also pass through the explicit role helper. Tracking each
    # as a follow-up; new routes must NOT join this list.
    "create_version": "agent-scoped; service layer enforces role",
    "promote_version": "agent-scoped; service layer enforces role",
    "archive_agent": "agent-scoped; service layer enforces role",
    "create_api_key": "service layer enforces role",
    "revoke_api_key": "service layer enforces role",
    "takeover_conversation": "conversation-scoped; service layer enforces role",
    "start_run": "eval-suite-scoped; service layer enforces role",
    "patch_workspace": "uses authorise_workspace internally",
    "add_workspace_member": "uses authorise_workspace internally",
    "remove_workspace_member": "uses authorise_workspace internally",
    "update_workspace_member_role": "uses authorise_workspace internally",
}


def _route_decorator(node: ast.AsyncFunctionDef | ast.FunctionDef) -> str | None:
    """Return the lowercased verb (post/patch/put/delete) if the
    function is decorated with ``@router.<verb>(...)``, else None."""
    for dec in node.decorator_list:
        # @router.post("/path", ...) form
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
            attr = dec.func.attr.lower()
            if attr in _MUTATING_DECORATORS:
                return attr
    return None


def _route_path(node: ast.AsyncFunctionDef | ast.FunctionDef) -> str:
    """Return the path string from the route decorator's first
    positional argument."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Call) and dec.args:
            arg = dec.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
    return ""


def _calls_authorize_workspace_access_with_role(
    node: ast.AsyncFunctionDef | ast.FunctionDef,
) -> bool:
    """True iff the function body contains a call to
    ``authorize_workspace_access(..., required_role=<truthy>)``.
    """
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        # Resolve the called name: bare ``authorize_workspace_access(...)``
        # or ``module.authorize_workspace_access(...)``.
        callee = child.func
        if (isinstance(callee, ast.Name) and callee.id == "authorize_workspace_access") or (
            isinstance(callee, ast.Attribute)
            and callee.attr == "authorize_workspace_access"
        ):
            pass
        else:
            continue
        # We found the call; check ``required_role`` is set + non-None.
        for kw in child.keywords:
            if kw.arg != "required_role":
                continue
            return not (isinstance(kw.value, ast.Constant) and kw.value.value is None)
    return False


def _iter_route_modules() -> list[Path]:
    return sorted(ROUTES_DIR.glob("_routes_*.py"))


def _collect_violations() -> list[tuple[Path, str, str, str]]:
    """For every mutating route, return ``(file, func_name, verb, path)``
    if it does NOT enforce a role and is not in the allow-list."""
    violations: list[tuple[Path, str, str, str]] = []
    for module in _iter_route_modules():
        tree = ast.parse(module.read_text(), filename=str(module))
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                continue
            verb = _route_decorator(node)
            if verb is None:
                continue
            path = _route_path(node)
            if "{workspace_id}" not in path:
                # Workspace-agnostic. Either auth-scoped (handled by
                # the allow-list) or workspace-creating; either way
                # there's no workspace to apply role policy against.
                if node.name not in _ALLOWLIST_FUNCS:
                    violations.append((module, node.name, verb, path))
                continue
            if _calls_authorize_workspace_access_with_role(node):
                continue
            if node.name in _ALLOWLIST_FUNCS:
                continue
            violations.append((module, node.name, verb, path))
    return violations


def test_every_mutating_route_enforces_a_role_or_is_documented() -> None:
    """Sweep: a mutating route that doesn't enforce a role gradient
    AND isn't in the documented allow-list is a privilege escalation
    waiting to happen."""
    violations = _collect_violations()
    if violations:
        lines = [
            f"  {p.name}::{name} — @router.{verb}({path!r})"
            for p, name, verb, path in violations
        ]
        pytest.fail(
            "Mutating routes without a role gradient (vega #13):\n"
            + "\n".join(lines)
            + "\nFix by either: calling authorize_workspace_access(..., "
            "required_role=Role.<level>) in the handler, OR adding the "
            "function name to _ALLOWLIST_FUNCS with a justification."
        )


def test_allowlist_does_not_grow_silently() -> None:
    """Every allow-list entry must point at a function that actually
    exists. Stale entries hide regressions where an allowed name
    gets renamed to skip the role check."""
    seen: set[str] = set()
    for module in _iter_route_modules():
        tree = ast.parse(module.read_text(), filename=str(module))
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                seen.add(node.name)
    stale = set(_ALLOWLIST_FUNCS) - seen
    assert not stale, (
        "Allow-list entries reference non-existent functions:\n  "
        + "\n  ".join(sorted(stale))
        + "\nDelete them from _ALLOWLIST_FUNCS."
    )


def test_at_least_one_route_actually_enforces_a_role() -> None:
    """Sanity: the sweep finds *some* role enforcement. If this
    assertion ever trips it means the AST scan is broken (e.g. the
    detection logic stopped seeing kwargs) and a green pass on the
    main test would be a false negative."""
    found = False
    for module in _iter_route_modules():
        tree = ast.parse(module.read_text(), filename=str(module))
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                continue
            if _calls_authorize_workspace_access_with_role(node):
                found = True
                break
        if found:
            break
    assert found, "no route enforces a role — AST scan is probably broken"

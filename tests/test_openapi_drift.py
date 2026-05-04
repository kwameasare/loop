"""Contract test: ``openapi.yaml`` matches the cp + dp FastAPI apps' actual routes.

vega #12 (block-prod): the public OpenAPI spec at
``loop_implementation/api/openapi.yaml`` is the source of truth for SDK
generation, schemathesis fuzzing, and partner integrations. Without
a CI gate it drifts silently — a route lands in cp without a spec
update, partner SDKs miss the endpoint, schemathesis stops covering
it, and the next breaking change ships without anyone noticing.

This test loads the YAML spec and the FastAPI-generated OpenAPI for
both cp + dp, then asserts:

  1. Every path in the YAML spec is implemented by cp or dp (modulo
     a documented allow-list for paths that are aliased / pending
     implementation).
  2. Every public ``/v1/...`` path implemented by cp or dp is in the
     YAML spec (modulo a documented baseline of pre-existing drift).

The allow-lists are explicit and tracked. New drift fails CI; closing
existing drift is a separate workstream that gradually shrinks the
allow-list to zero.
"""

from __future__ import annotations

from pathlib import Path

import yaml

# Paths that exist in cp/dp for ops/probe reasons but are NOT part of
# the public contract — they must NOT be in the YAML spec.
_OPS_PATHS = frozenset({
    "/healthz",
    "/livez",
    "/readyz",
    "/metrics",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/docs/oauth2-redirect",
})

# Spec-declared health paths the test tolerates: the YAML happens to
# include /v1/healthz + /v1/readyz so external monitoring suites can
# discover them via the spec, but they're served at the prefix-less
# /healthz on the actual apps. Kept narrow on purpose — anything not
# in this set must obey the "no ops paths in spec" rule.
_SPEC_OPS_ALLOWED = frozenset({"/v1/healthz", "/v1/readyz"})

# Pre-existing drift baseline (vega #12 ratchet). New drift FAILS CI;
# closing existing items shrinks this set toward {} as a separate
# workstream tracked by /loop. Each entry is a route that exists in
# cp or dp but is not yet declared in openapi.yaml.
_DRIFT_BASELINE_APP_NOT_IN_SPEC: frozenset[str] = frozenset({
    "/v1/agents/{agent_id}/versions/{version_id}/promote",
    "/v1/auth/refresh",
    "/v1/webhooks/incoming/_supported",
    "/v1/webhooks/incoming/{channel}",
    "/v1/workspaces/{workspace_id}/api-keys/{key_id}",
    "/v1/workspaces/{workspace_id}/budgets",
    "/v1/workspaces/{workspace_id}/data-deletion",
    "/v1/workspaces/{workspace_id}/data-deletion/{request_id_path}",
    "/v1/workspaces/{workspace_id}/eval-suites",
    "/v1/workspaces/{workspace_id}/kb/documents",
    "/v1/workspaces/{workspace_id}/kb/documents/{document_id}",
    "/v1/workspaces/{workspace_id}/kb/refresh",
    "/v1/workspaces/{workspace_id}/members/{user_sub}",
    "/v1/workspaces/{workspace_id}/secrets/{name}",
    "/v1/workspaces/{workspace_id}/secrets/{name}/rotate",
    "/v1/workspaces/{workspace_id}/traces",
    "/v1/workspaces/{workspace_id}/usage",
})

# Spec paths that don't (yet) have an implementing route. Most of
# these are the in-flight P0.4 surfaces where the route is declared
# in YAML but the wiring landed in a workspace-prefixed shape — the
# rename is part of the same drift-closure workstream above.
_DRIFT_BASELINE_SPEC_NOT_IN_APP: frozenset[str] = frozenset({
    "/v1/agents/{agent_id}/invoke",
    "/v1/budgets",
    "/v1/conversations/{conversation_id}/messages",
    "/v1/eval-runs/{run_id}",
    "/v1/eval-suites",
    "/v1/eval-suites/{suite_id}/cases",
    "/v1/kb",
    "/v1/kb/{kb_id}/ingest",
    "/v1/kb/{kb_id}/search",
    "/v1/mcp",
    "/v1/traces/search",
    "/v1/traces/{turn_id}",
    "/v1/usage",
    "/v1/webhooks/incoming",
    "/v1/workspaces/{workspace_id}/secrets",
})


def _spec_paths() -> set[str]:
    """Paths declared in the public OpenAPI YAML, normalised to the
    ``/v1/...`` shape the FastAPI apps use. The YAML's ``servers``
    section pre-applies ``/v1``, so spec paths are relative to that.
    """
    spec_path = (
        Path(__file__).resolve().parent.parent
        / "loop_implementation"
        / "api"
        / "openapi.yaml"
    )
    with spec_path.open(encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    return {f"/v1{path}" for path in spec.get("paths", {})}


def _app_paths(app: object) -> set[str]:
    """Public ``/v1/...`` paths exposed by a FastAPI app.

    We pull from the generated OpenAPI rather than ``app.routes`` so
    routes that are explicitly excluded from the schema
    (``include_in_schema=False`` — typically ops probes) are filtered
    out for free.
    """
    schema = app.openapi()  # type: ignore[attr-defined]
    return {p for p in schema.get("paths", {}) if p.startswith("/v1/")}


def _all_app_paths() -> set[str]:
    """Combined public-facing paths from cp + dp."""
    from loop_control_plane.app import create_app as create_cp
    from loop_data_plane.runtime_app import create_app as create_dp

    cp = create_cp()
    dp = create_dp()
    return _app_paths(cp) | _app_paths(dp)


def test_no_new_app_paths_missing_from_spec() -> None:
    """If a service exposes a public ``/v1/...`` route, it MUST be in
    the public contract OR the documented drift baseline. The failure
    mode this catches: a route lands in cp without an OpenAPI update,
    partner SDKs miss it, and schemathesis stops covering it because
    it's not in the spec.
    """
    spec = _spec_paths()
    apps = _all_app_paths()
    drift = apps - spec
    new_drift = drift - _DRIFT_BASELINE_APP_NOT_IN_SPEC
    assert not new_drift, (
        "New /v1/* paths landed in cp/dp without a matching openapi.yaml entry:\n  "
        + "\n  ".join(sorted(new_drift))
        + "\nAdd them to the spec OR (only as a temporary measure) to "
        "_DRIFT_BASELINE_APP_NOT_IN_SPEC with an explanation."
    )


def test_drift_baseline_does_not_grow_silently() -> None:
    """Symmetric guard: if we close a drift item by adding the path
    to the spec OR removing the route, the baseline must shrink to
    match. Otherwise stale entries hide future regressions of the
    same path."""
    spec = _spec_paths()
    apps = _all_app_paths()
    actual_drift = apps - spec
    stale = _DRIFT_BASELINE_APP_NOT_IN_SPEC - actual_drift
    assert not stale, (
        "_DRIFT_BASELINE_APP_NOT_IN_SPEC has stale entries (the path "
        "either landed in the spec or was removed from the app):\n  "
        + "\n  ".join(sorted(stale))
        + "\nDelete them from the baseline."
    )


def test_no_new_spec_paths_missing_from_apps() -> None:
    """Symmetric guard for the other direction: a path in the public
    contract that no app implements is a partner-facing 404. The
    baseline tracks pre-existing drift; new drift fails."""
    spec = _spec_paths()
    apps = _all_app_paths()
    drift = spec - apps - _SPEC_OPS_ALLOWED
    new_drift = drift - _DRIFT_BASELINE_SPEC_NOT_IN_APP
    assert not new_drift, (
        "New paths in openapi.yaml that no service implements:\n  "
        + "\n  ".join(sorted(new_drift))
        + "\nEither implement them in cp/dp or remove them from the spec."
    )


def test_spec_not_in_app_baseline_is_not_stale() -> None:
    spec = _spec_paths()
    apps = _all_app_paths()
    actual_drift = spec - apps - _SPEC_OPS_ALLOWED
    stale = _DRIFT_BASELINE_SPEC_NOT_IN_APP - actual_drift
    assert not stale, (
        "_DRIFT_BASELINE_SPEC_NOT_IN_APP has stale entries:\n  "
        + "\n  ".join(sorted(stale))
        + "\nDelete them from the baseline."
    )


def test_spec_does_not_declare_unauthorised_ops_paths() -> None:
    """Apart from the small allow-list, ops paths must stay out of
    the public contract. They're kubelet probes; declaring them in
    the spec creates a contract obligation we don't actually want."""
    spec = _spec_paths()
    leaked = {
        p for p in spec
        if any(p.endswith(ops) for ops in _OPS_PATHS)
        and p not in _SPEC_OPS_ALLOWED
    }
    assert not leaked, (
        f"openapi.yaml leaks ops paths: {sorted(leaked)}; remove them."
    )

"""FastAPI entrypoint for the control-plane service (S901)."""

from __future__ import annotations

from fastapi import FastAPI

from loop_control_plane._app_common import domain_error, package_version
from loop_control_plane._app_state import CpApiState
from loop_control_plane._routes_agent_versions import (
    router as agent_versions_router,
)
from loop_control_plane._routes_agents import router as agents_router
from loop_control_plane._routes_api_keys import router as api_keys_router
from loop_control_plane._routes_audit import router as audit_router
from loop_control_plane._routes_auth import router as auth_router
from loop_control_plane._routes_budgets import router as budgets_router
from loop_control_plane._routes_conversations import (
    router_agents_conv as agent_conversations_router,
)
from loop_control_plane._routes_conversations import (
    router_conversations as conversations_router,
)
from loop_control_plane._routes_dsr import router as dsr_router
from loop_control_plane._routes_evals import (
    router_suites as eval_suites_router,
)
from loop_control_plane._routes_evals import (
    router_workspaces as workspace_evals_router,
)
from loop_control_plane._routes_health import router as health_router
from loop_control_plane._routes_kb import router as kb_router
from loop_control_plane._routes_secrets import router as secrets_router
from loop_control_plane._routes_traces_usage import router as telemetry_router
from loop_control_plane._routes_workspaces import router as workspaces_router
from loop_control_plane.auth import AuthError
from loop_control_plane.auth_exchange import AuthExchangeError
from loop_control_plane.authorize import AuthorisationError
from loop_control_plane.metrics import install_metrics
from loop_control_plane.paseto import PasetoError
from loop_control_plane.tracing import install_tracing
from loop_control_plane.workspaces import WorkspaceError


def create_app(state: CpApiState | None = None) -> FastAPI:
    app = FastAPI(title="Loop Control Plane", version=package_version())
    app.state.cp = state or CpApiState()
    # `errors.map_to_loop_api_error` already maps every domain error
    # below to a clean LOOP-API-* envelope; we just wire up the
    # exception handlers. Adding `AuthorisationError` here closes a
    # gap surfaced during P0.8b — the GDPR DSR routes raise it on
    # missing-role and previously the exception escaped uncaught.
    for exc in (
        AuthError,
        WorkspaceError,
        AuthExchangeError,
        PasetoError,
        AuthorisationError,
    ):
        app.add_exception_handler(exc, domain_error)
    for router in (
        health_router,
        auth_router,
        workspaces_router,
        agents_router,
        audit_router,
        # P0.8b: GDPR DSR (Art-17 erasure) endpoints.
        dsr_router,
        # P0.4: workspace API-key + secrets routes.
        api_keys_router,
        secrets_router,
        # P0.4: traces search + usage list routes.
        telemetry_router,
        # P0.4: agent version create/list/promote.
        agent_versions_router,
        # P0.4: conversation list + read + takeover.
        agent_conversations_router,
        conversations_router,
        # P0.4: workspace budgets (daily/hard limits).
        budgets_router,
        # P0.4: KB document CRUD + refresh.
        kb_router,
        # P0.4: eval suites + runs.
        workspace_evals_router,
        eval_suites_router,
    ):
        app.include_router(router)
    # P0.7b: Prometheus middleware + /metrics endpoint. The
    # `slo-burn.yaml` alerts target the metrics this emits; before
    # this wiring shipped, those alerts had no input series and
    # PagerDuty would never fire.
    install_metrics(app)
    # P0.7c: OpenTelemetry tracing — every request gets a span,
    # propagated to dp-runtime + gateway + upstream LLM via
    # traceparent. Skipped when LOOP_OTEL_ENDPOINT=disabled.
    install_tracing(app, service_name="cp-api")
    return app


app = create_app()


__all__ = ["CpApiState", "app", "create_app"]

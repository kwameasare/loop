"""FastAPI entrypoint for the control-plane service (S901)."""

from __future__ import annotations

from fastapi import FastAPI

from loop_control_plane._app_common import domain_error, package_version
from loop_control_plane._app_state import CpApiState
from loop_control_plane._routes_agents import router as agents_router
from loop_control_plane._routes_audit import router as audit_router
from loop_control_plane._routes_auth import router as auth_router
from loop_control_plane._routes_health import router as health_router
from loop_control_plane._routes_workspaces import router as workspaces_router
from loop_control_plane.auth import AuthError
from loop_control_plane.auth_exchange import AuthExchangeError
from loop_control_plane.paseto import PasetoError
from loop_control_plane.workspaces import WorkspaceError


def create_app(state: CpApiState | None = None) -> FastAPI:
    app = FastAPI(title="Loop Control Plane", version=package_version())
    app.state.cp = state or CpApiState()
    for exc in (AuthError, WorkspaceError, AuthExchangeError, PasetoError):
        app.add_exception_handler(exc, domain_error)
    for router in (health_router, auth_router, workspaces_router, agents_router, audit_router):
        app.include_router(router)
    return app


app = create_app()


__all__ = ["CpApiState", "app", "create_app"]

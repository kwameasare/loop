"""Offline-render the cp + dp Alembic migrations and assert the core DDL.

We don't spin up Postgres in this test — instead we use ``alembic upgrade
--sql`` (offline mode) so CI stays fast and dependency-free. A live-DB
round-trip lives in the integration suite (story S007).
"""

from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stdout
from importlib.resources import files
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config


def _render(ini_resource: str) -> str:
    """Run ``alembic upgrade --sql head`` against ``ini_resource`` and capture stdout."""

    ini_path = Path(str(files(ini_resource).joinpath("alembic.ini")))
    cfg = Config(file_=str(ini_path), ini_section="alembic")
    # Pin a deterministic DSN so SQL rendering doesn't depend on host env.
    cfg.set_main_option("sqlalchemy.url", "postgresql+psycopg://loop:loop@localhost:5432/loop")
    buf = io.StringIO()
    with redirect_stdout(buf):
        command.upgrade(cfg, "head", sql=True)
    return buf.getvalue()


@pytest.fixture
def cp_sql() -> str:
    # Ensure the package is importable when tests run from the repo root.
    sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "control-plane"))
    os.environ.pop("LOOP_CP_DB_URL", None)
    return _render("loop_control_plane.migrations")


@pytest.fixture
def dp_sql() -> str:
    sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "data-plane"))
    os.environ.pop("LOOP_RUNTIME_DB_URL", None)
    return _render("loop_data_plane.migrations")


# ---------------------------------------------------------------------------
# Control plane
# ---------------------------------------------------------------------------


def test_cp_creates_core_identity_tables(cp_sql: str) -> None:
    for table in (
        "workspaces",
        "users",
        "workspace_members",
        "api_keys",
        "agents",
        "agent_versions",
    ):
        assert f"CREATE TABLE {table}" in cp_sql, f"cp migration missing table {table}"


def test_cp_enables_rls_on_tenanted_tables(cp_sql: str) -> None:
    for table in ("api_keys", "agent_secrets", "agents", "agent_versions"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in cp_sql
        assert f"CREATE POLICY tenant_isolation ON {table}" in cp_sql


def test_cp_enables_required_extensions(cp_sql: str) -> None:
    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" in cp_sql
    assert "CREATE EXTENSION IF NOT EXISTS citext" in cp_sql


def test_cp_creates_mcp_marketplace_tables(cp_sql: str) -> None:
    for table in (
        "mcp_servers",
        "mcp_server_versions",
        "mcp_agent_installs",
        "mcp_server_reviews",
        "mcp_server_usage",
    ):
        assert f"CREATE TABLE {table}" in cp_sql


def test_cp_enables_marketplace_rls(cp_sql: str) -> None:
    for table in ("mcp_agent_installs", "mcp_server_reviews", "mcp_server_usage"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in cp_sql
        assert f"CREATE POLICY {table}_tenant_isolation" in cp_sql
        assert f"ON {table}" in cp_sql


# ---------------------------------------------------------------------------
# Data plane
# ---------------------------------------------------------------------------


def test_dp_creates_runtime_tables(dp_sql: str) -> None:
    for table in ("conversations", "turns", "memory_user", "memory_bot", "tool_calls"):
        assert f"CREATE TABLE {table}" in dp_sql, f"dp migration missing table {table}"


def test_dp_every_tenanted_table_has_rls_policy(dp_sql: str) -> None:
    # ADR-020: workspace_id NOT NULL + RLS on every data-plane table.
    for table in ("conversations", "turns", "memory_user", "memory_bot", "tool_calls"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in dp_sql
        assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY" in dp_sql
        assert f"CREATE POLICY tenant_isolation ON {table}" in dp_sql


def test_dp_workspace_id_is_not_null(dp_sql: str) -> None:
    # Spot-check: the column must appear with NOT NULL on each tenanted table.
    # Alembic's --sql output preserves our literal CREATE TABLE bodies.
    for table_marker in (
        "CREATE TABLE conversations",
        "CREATE TABLE turns",
        "CREATE TABLE tool_calls",
    ):
        idx = dp_sql.index(table_marker)
        body = dp_sql[idx : idx + 1500]
        assert "workspace_id" in body and "NOT NULL" in body


# ---------------------------------------------------------------------------
# cp_0005_audit_log: append-only audit table (S630)
# ---------------------------------------------------------------------------


def test_cp_creates_audit_log_table(cp_sql: str) -> None:
    assert "CREATE TABLE audit_log" in cp_sql


def test_cp_audit_log_has_required_columns(cp_sql: str) -> None:
    idx = cp_sql.index("CREATE TABLE audit_log")
    body = cp_sql[idx : idx + 2000]
    for col in ("workspace_id", "actor_user_id", "action", "resource_type",
                "entry_hash", "previous_hash", "created_at"):
        assert col in body, f"audit_log missing column {col!r}"


def test_cp_audit_log_indexes(cp_sql: str) -> None:
    for idx_name in (
        "idx_audit_workspace_action",
        "idx_audit_resource",
        "idx_audit_actor",
    ):
        assert idx_name in cp_sql, f"audit_log missing index {idx_name!r}"

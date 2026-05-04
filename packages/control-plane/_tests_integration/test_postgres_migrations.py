from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

pytestmark = pytest.mark.integration

CP_HEAD_REVISION = "cp_0010_audit_log_no_ws_fk"
DP_INITIAL_REVISION = "dp_0001_initial"


def _table_names(engine: Engine) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT table_name
                  FROM information_schema.tables
                 WHERE table_schema = 'public'
                """
            )
        )
        return {str(row.table_name) for row in rows}


def test_fixture_applies_initial_control_and_data_plane_migrations(
    migrated_postgres_engine: Engine,
) -> None:
    tables = _table_names(migrated_postgres_engine)

    assert {"workspaces", "users", "api_keys", "agents"}.issubset(tables)
    assert {"audit_log", "audit_events", "refresh_tokens"}.issubset(tables)
    assert {"conversations", "turns", "memory_user", "memory_bot", "tool_calls"}.issubset(tables)
    assert {"alembic_version_cp", "alembic_version_dp"}.issubset(tables)


def test_fixture_records_separate_migration_heads(migrated_postgres_engine: Engine) -> None:
    with migrated_postgres_engine.connect() as conn:
        cp_revision = conn.scalar(text("SELECT version_num FROM alembic_version_cp"))
        dp_revision = conn.scalar(text("SELECT version_num FROM alembic_version_dp"))

    assert cp_revision == CP_HEAD_REVISION
    assert dp_revision == DP_INITIAL_REVISION


def test_data_plane_rls_hides_rows_from_other_workspace(
    migrated_postgres_engine: Engine,
) -> None:
    workspace_a = uuid4()
    workspace_b = uuid4()
    conversation_id = uuid4()
    agent_id = uuid4()

    with migrated_postgres_engine.begin() as conn:
        conn.execute(
            text("SELECT set_config('loop.workspace_id', :workspace_id, true)"),
            {"workspace_id": str(workspace_a)},
        )
        conn.execute(
            text(
                """
                INSERT INTO conversations (
                    id, workspace_id, agent_id, channel_type, user_id, metadata_json
                )
                VALUES (
                    :id, :workspace_id, :agent_id, 'web', 'user-a', '{}'::jsonb
                )
                """
            ),
            {
                "id": conversation_id,
                "workspace_id": workspace_a,
                "agent_id": agent_id,
            },
        )
        visible_to_a = conn.scalar(text("SELECT count(*) FROM conversations"))

        conn.execute(
            text("SELECT set_config('loop.workspace_id', :workspace_id, true)"),
            {"workspace_id": str(workspace_b)},
        )
        visible_to_b = conn.scalar(text("SELECT count(*) FROM conversations"))

    assert visible_to_a == 1
    assert visible_to_b == 0

from __future__ import annotations

from collections.abc import Iterator
from importlib.resources import files
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from testcontainers.postgres import PostgresContainer

pytestmark = pytest.mark.integration

CP_INITIAL_REVISION = "cp_0001_initial"
DP_INITIAL_REVISION = "dp_0001_initial"
APP_DB_USER = "loop_app"
APP_DB_PASSWORD = "loop_app"  # noqa: S105 - ephemeral testcontainers role.


def _migration_config(resource: str, url: str, *, version_table: str) -> Config:
    ini_path = Path(str(files(resource).joinpath("alembic.ini")))
    cfg = Config(file_=str(ini_path), ini_section="alembic")
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.set_main_option("version_table", version_table)
    return cfg


@pytest.fixture(scope="session")
def migrated_postgres_engine() -> Iterator[Engine]:
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        command.upgrade(
            _migration_config(
                "loop_control_plane.migrations",
                url,
                version_table="alembic_version_cp",
            ),
            CP_INITIAL_REVISION,
        )
        command.upgrade(
            _migration_config(
                "loop_data_plane.migrations",
                url,
                version_table="alembic_version_dp",
            ),
            DP_INITIAL_REVISION,
        )
        admin_engine = create_engine(url)
        with admin_engine.begin() as conn:
            conn.execute(text(f"CREATE ROLE {APP_DB_USER} LOGIN PASSWORD '{APP_DB_PASSWORD}'"))
            conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {APP_DB_USER}"))
            conn.execute(
                text(
                    f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_DB_USER}"
                )
            )
        admin_engine.dispose()

        app_url = make_url(url).set(username=APP_DB_USER, password=APP_DB_PASSWORD)
        engine = create_engine(app_url)
        try:
            yield engine
        finally:
            engine.dispose()


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
    assert {"conversations", "turns", "memory_user", "memory_bot", "tool_calls"}.issubset(tables)
    assert {"alembic_version_cp", "alembic_version_dp"}.issubset(tables)


def test_fixture_records_separate_migration_heads(migrated_postgres_engine: Engine) -> None:
    with migrated_postgres_engine.connect() as conn:
        cp_revision = conn.scalar(text("SELECT version_num FROM alembic_version_cp"))
        dp_revision = conn.scalar(text("SELECT version_num FROM alembic_version_dp"))

    assert cp_revision == CP_INITIAL_REVISION
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

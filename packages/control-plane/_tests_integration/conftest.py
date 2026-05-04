"""Shared fixtures for cp-api Postgres integration tests.

The session-scoped :func:`migrated_postgres_engine` fixture spins up
one ephemeral Postgres container per test session, applies the cp +
dp migrations, and yields a sync :class:`~sqlalchemy.engine.Engine`
bound to the unprivileged ``loop_app`` role (mirrors the role we
hand to the cp-api in production — RLS policies kick in here).

Tests that want to operate as the unprivileged tenant role use the
yielded engine directly. Tests that need superuser access (e.g. to
bypass append-only RULEs to verify they fire) should construct a
fresh admin engine from ``engine.url.set(username='postgres', ...)``.
"""

from __future__ import annotations

from collections.abc import Iterator
from importlib.resources import files
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from testcontainers.postgres import PostgresContainer

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
            "head",
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
            conn.execute(
                text(f"CREATE ROLE {APP_DB_USER} LOGIN PASSWORD '{APP_DB_PASSWORD}'")
            )
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

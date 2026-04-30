"""Data-plane Alembic migrations.

Run with::

    uv run python -m loop_data_plane.migrations upgrade head

The DSN is read from ``LOOP_RUNTIME_DB_URL`` (default
``postgresql+psycopg://loop:loop@localhost:5432/loop``).
"""

from loop_data_plane.migrations._runner import main

__all__ = ["main"]

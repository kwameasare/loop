"""Control-plane Alembic migrations.

Run with::

    uv run python -m loop_control_plane.migrations upgrade head

The DSN is read from ``LOOP_CP_DB_URL`` (default
``postgresql+psycopg://loop:loop@localhost:5432/loop``).
"""

from loop_control_plane.migrations._runner import main

__all__ = ["main"]

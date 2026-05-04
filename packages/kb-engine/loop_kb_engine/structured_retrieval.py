"""Structured-data retrieval: SQL-on-the-fly for CSV, JSON, and Excel (S827).

Agents can upload spreadsheets / JSON datasets and then issue natural-language
or SQL queries against them.  This module:

* Loads CSV / JSON into an in-process SQLite database using stdlib csv/json.
* Optionally loads Excel via openpyxl (if installed).
* Exposes ``StructuredStore`` — a per-session store that maps dataset names
  to SQLite tables.
* Provides ``sql_query`` — executes a SQL statement and returns rows as a
  list of dicts (safe read-only execution).

Design constraints:
- Only SELECT statements are permitted (no DDL/DML from callers).
- Dataset names are validated to prevent SQL injection via table name
  substitution (alphanumeric + underscore, max 64 chars).
- All data is kept in-process; no files are persisted after the call.
- No external dependencies for CSV/JSON; openpyxl is optional for Excel.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
from typing import Any

__all__ = [
    "DatasetError",
    "StructuredStore",
    "load_csv",
    "load_json",
    "sql_query",
]

_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$")


class DatasetError(ValueError):
    """Raised for invalid dataset names or unsupported file types."""


def _validate_name(name: str) -> str:
    if not _NAME_RE.match(name):
        raise DatasetError(
            f"Dataset name {name!r} is invalid. "
            "Must match ^[a-zA-Z_][a-zA-Z0-9_]{{0,63}}$"
        )
    return name


def _coerce(value: str) -> Any:
    """Try to parse a CSV string cell as int/float, fallback to str."""
    try:
        return int(value)
    except (ValueError, TypeError):
        pass
    try:
        return float(value)
    except (ValueError, TypeError):
        pass
    return value


class StructuredStore:
    """An in-process SQLite store that holds uploaded structured datasets.

    Each dataset becomes a table in a shared in-memory SQLite connection.
    The store is intentionally single-threaded; use one instance per request
    context / session.

    Usage::

        store = StructuredStore()
        store.load_csv("sales", csv_bytes)
        rows = store.query("SELECT region, SUM(amount) FROM sales GROUP BY region")
    """

    def __init__(self) -> None:
        self._conn: sqlite3.Connection = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._tables: set[str] = set()

    # ------------------------------------------------------------------
    # Loaders
    # ------------------------------------------------------------------

    def load_csv(self, name: str, data: bytes | str) -> int:
        """Load CSV data into a table named *name*.

        Returns the number of rows loaded.
        """
        _validate_name(name)
        if isinstance(data, bytes):
            data = data.decode()
        reader = csv.DictReader(io.StringIO(data))
        rows = list(reader)
        if not rows:
            # Create empty table with no rows
            self._tables.add(name)
            return 0
        cols = list(rows[0].keys())
        col_defs = ", ".join(f'"{c}" TEXT' for c in cols)
        self._conn.execute(f'DROP TABLE IF EXISTS "{name}"')
        self._conn.execute(f'CREATE TABLE "{name}" ({col_defs})')
        placeholders = ", ".join("?" for _ in cols)
        for row in rows:
            values = [_coerce(row.get(c, "")) for c in cols]
            # `name` is validated by ``_validate_name`` against ``_NAME_RE``
            # before reaching this line; ``placeholders`` is a static comma-
            # separated string of ``?`` markers. Values bind through the
            # standard parameterised path. S608 false positive.
            self._conn.execute(f'INSERT INTO "{name}" VALUES ({placeholders})', values)  # noqa: S608
        self._conn.commit()
        self._tables.add(name)
        return len(rows)

    def load_json(self, name: str, data: bytes | str) -> int:
        """Load a JSON array-of-objects into a table named *name*.

        Returns the number of rows loaded.
        """
        _validate_name(name)
        if isinstance(data, bytes):
            data = data.decode()
        records: list[dict[str, Any]] = json.loads(data)
        if not records:
            self._tables.add(name)
            return 0
        cols = list(records[0].keys())
        col_defs = ", ".join(f'"{c}" TEXT' for c in cols)
        self._conn.execute(f'DROP TABLE IF EXISTS "{name}"')
        self._conn.execute(f'CREATE TABLE "{name}" ({col_defs})')
        placeholders = ", ".join("?" for _ in cols)
        for record in records:
            values = [record.get(c) for c in cols]
            # `name` is validated by ``_validate_name`` against ``_NAME_RE``
            # before reaching this line; ``placeholders`` is a static comma-
            # separated string of ``?`` markers. Values bind through the
            # standard parameterised path. S608 false positive.
            self._conn.execute(f'INSERT INTO "{name}" VALUES ({placeholders})', values)  # noqa: S608
        self._conn.commit()
        self._tables.add(name)
        return len(records)

    def load_excel(self, name: str, data: bytes, sheet: str | int = 0) -> int:
        """Load an Excel sheet into a table named *name*.

        Requires ``openpyxl``.  Returns the number of rows loaded.
        """
        try:
            import openpyxl
        except ImportError as exc:
            raise ImportError(
                "openpyxl is required for Excel support. "
                "Install it with: pip install openpyxl"
            ) from exc

        _validate_name(name)
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.worksheets[sheet] if isinstance(sheet, int) else wb[sheet]
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(h) for h in next(rows_iter)]
        col_defs = ", ".join(f'"{c}" TEXT' for c in headers)
        self._conn.execute(f'DROP TABLE IF EXISTS "{name}"')
        self._conn.execute(f'CREATE TABLE "{name}" ({col_defs})')
        placeholders = ", ".join("?" for _ in headers)
        count = 0
        for row in rows_iter:
            # See INSERT comment above: name is _validate_name'd; values bind via ?.
            self._conn.execute(f'INSERT INTO "{name}" VALUES ({placeholders})', list(row))  # noqa: S608
            count += 1
        self._conn.commit()
        self._tables.add(name)
        return count

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(self, sql: str) -> list[dict[str, Any]]:
        """Execute a read-only SQL SELECT and return rows as dicts.

        Raises:
            DatasetError: If the statement is not a SELECT.
            sqlite3.Error: For SQL syntax or runtime errors.
        """
        _assert_select(sql)
        cursor = self._conn.execute(sql)
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description or []]
        return [dict(zip(cols, row, strict=False)) for row in rows]

    @property
    def tables(self) -> frozenset[str]:
        """Names of all loaded tables."""
        return frozenset(self._tables)

    def close(self) -> None:
        """Release the SQLite connection."""
        self._conn.close()


# ---------------------------------------------------------------------------
# Module-level helpers (for callers who manage their own connection)
# ---------------------------------------------------------------------------


def _assert_select(sql: str) -> None:
    stripped = sql.strip().upper()
    if not stripped.startswith("SELECT"):
        raise DatasetError(
            f"Only SELECT statements are permitted; got: {sql[:60]!r}"
        )


def load_csv(name: str, data: bytes | str) -> StructuredStore:
    """Convenience: create a fresh store and load a single CSV dataset."""
    store = StructuredStore()
    store.load_csv(name, data)
    return store


def load_json(name: str, data: bytes | str) -> StructuredStore:
    """Convenience: create a fresh store and load a single JSON dataset."""
    store = StructuredStore()
    store.load_json(name, data)
    return store


def sql_query(store: StructuredStore, sql: str) -> list[dict[str, Any]]:
    """Execute *sql* against *store* and return rows as dicts."""
    return store.query(sql)

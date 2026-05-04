"""Tests for S827 — structured-data retrieval (CSV/Excel/JSON with SQL-on-the-fly).

Covers:
- DatasetError on invalid table names
- load_csv / load_json round-trips
- sql_query returns correct rows as dicts
- SELECT-only enforcement
- tables property
- GROUP BY, WHERE, ORDER BY
- Integration: upload spreadsheet, tool can SQL it
"""

from __future__ import annotations

import json

import pytest
from loop_kb_engine.structured_retrieval import (
    DatasetError,
    StructuredStore,
    load_csv,
    load_json,
    sql_query,
)

# ── helpers ───────────────────────────────────────────────────────────────

CSV_DATA = """name,region,amount
Alice,North,100
Bob,South,200
Carol,North,150
Dave,South,50
"""

JSON_DATA = json.dumps([
    {"product": "widget", "units": 10, "price": 9.99},
    {"product": "gadget", "units": 5, "price": 49.99},
    {"product": "widget", "units": 3, "price": 9.99},
])


# ── DatasetError / name validation ───────────────────────────────────────

def test_invalid_name_with_space_raises():
    store = StructuredStore()
    with pytest.raises(DatasetError, match="invalid"):
        store.load_csv("bad name", CSV_DATA)


def test_invalid_name_with_hyphen_raises():
    store = StructuredStore()
    with pytest.raises(DatasetError, match="invalid"):
        store.load_csv("bad-name", CSV_DATA)


def test_invalid_name_starting_with_digit_raises():
    store = StructuredStore()
    with pytest.raises(DatasetError, match="invalid"):
        store.load_csv("1table", CSV_DATA)


def test_valid_name_underscore_and_digits():
    store = StructuredStore()
    rows = store.load_csv("sales_2025", CSV_DATA)
    assert rows == 4


# ── load_csv ──────────────────────────────────────────────────────────────

def test_load_csv_returns_row_count():
    store = StructuredStore()
    count = store.load_csv("sales", CSV_DATA)
    assert count == 4


def test_load_csv_bytes():
    store = StructuredStore()
    count = store.load_csv("sales", CSV_DATA.encode())
    assert count == 4


def test_load_csv_table_registered():
    store = StructuredStore()
    store.load_csv("sales", CSV_DATA)
    assert "sales" in store.tables


# ── load_json ─────────────────────────────────────────────────────────────

def test_load_json_returns_row_count():
    store = StructuredStore()
    count = store.load_json("products", JSON_DATA)
    assert count == 3


def test_load_json_bytes():
    store = StructuredStore()
    count = store.load_json("products", JSON_DATA.encode())
    assert count == 3


def test_load_json_table_registered():
    store = StructuredStore()
    store.load_json("products", JSON_DATA)
    assert "products" in store.tables


# ── sql_query / SELECT enforcement ───────────────────────────────────────

def test_sql_query_returns_dicts():
    store = load_csv("sales", CSV_DATA)
    rows = store.query("SELECT name, amount FROM sales WHERE region='North'")
    assert isinstance(rows, list)
    assert all(isinstance(r, dict) for r in rows)
    names = {r["name"] for r in rows}
    assert names == {"Alice", "Carol"}


def test_sql_query_group_by():
    store = load_csv("sales", CSV_DATA)
    rows = store.query(
        "SELECT region, SUM(amount) as total FROM sales GROUP BY region ORDER BY region"
    )
    totals = {r["region"]: r["total"] for r in rows}
    assert totals["North"] == 250
    assert totals["South"] == 250


def test_sql_query_order_by():
    store = load_csv("sales", CSV_DATA)
    rows = store.query("SELECT name FROM sales ORDER BY CAST(amount AS REAL) DESC")
    assert rows[0]["name"] == "Bob"


def test_non_select_raises():
    store = load_csv("sales", CSV_DATA)
    with pytest.raises(DatasetError, match="Only SELECT"):
        store.query("DROP TABLE sales")


def test_insert_raises():
    store = load_csv("sales", CSV_DATA)
    with pytest.raises(DatasetError):
        store.query("INSERT INTO sales VALUES ('Eve','East',999)")


def test_sql_query_helper():
    store = load_json("products", JSON_DATA)
    rows = sql_query(store, "SELECT product, SUM(units) as total FROM products GROUP BY product ORDER BY product")
    products = {r["product"]: r["total"] for r in rows}
    assert products["widget"] == 13
    assert products["gadget"] == 5


# ── multiple tables ───────────────────────────────────────────────────────

def test_multiple_tables_in_store():
    store = StructuredStore()
    store.load_csv("sales", CSV_DATA)
    store.load_json("products", JSON_DATA)
    assert "sales" in store.tables
    assert "products" in store.tables
    assert len(store.tables) == 2


def test_load_csv_convenience_helper():
    store = load_csv("sales", CSV_DATA)
    assert "sales" in store.tables


def test_load_json_convenience_helper():
    store = load_json("products", JSON_DATA)
    assert "products" in store.tables


# ── integration test: agent uploads spreadsheet, tool can SQL it ──────────

def test_integration_upload_csv_and_sql_query():
    """Integration: simulates agent uploading a CSV and running SQL."""
    csv_bytes = b"item,qty,unit_price\nwidget,10,1.50\ngadget,3,25.00\ndoodad,7,5.00\n"
    store = StructuredStore()
    rows_loaded = store.load_csv("inventory", csv_bytes)
    assert rows_loaded == 3

    # SQL: total value per item, sorted descending
    results = store.query(
        "SELECT item, qty * unit_price AS total_value FROM inventory ORDER BY total_value DESC"
    )
    assert results[0]["item"] == "gadget"
    assert results[0]["total_value"] == pytest.approx(75.0)
    assert results[1]["item"] == "doodad"

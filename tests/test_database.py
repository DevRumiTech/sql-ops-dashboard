"""Database rebuild, integrity, relationship, and schema tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts.init_db import initialize_database


def test_database_initializes_from_sql_files(tmp_path: Path) -> None:
    database = tmp_path / "nested" / "portfolio.db"

    initialize_database(database)

    assert database.is_file()
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_schema
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                """
            )
        }
        views = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'view'"
            )
        }

    assert tables == {
        "categories",
        "customers",
        "inventory_movements",
        "order_items",
        "orders",
        "products",
        "suppliers",
    }
    assert {
        "dashboard_summary",
        "margin_by_product",
        "product_revenue_rank",
        "revenue_by_category",
        "revenue_by_product",
    }.issubset(views)


def test_sqlite_integrity_check(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()

    assert result == ("ok",)


def test_foreign_key_integrity(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        issues = connection.execute("PRAGMA foreign_key_check").fetchall()

    assert issues == []

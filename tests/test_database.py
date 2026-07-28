"""Database generation, distribution, integrity, and schema tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts.generate_demo_data import generate_demo_database
from scripts.init_db import initialize_database


def _database_dump(path: Path) -> list[str]:
    with sqlite3.connect(path) as connection:
        return list(connection.iterdump())


def test_database_generation_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.db"
    second = tmp_path / "second.db"

    generate_demo_database(first)
    generate_demo_database(second)

    assert _database_dump(first) == _database_dump(second)


def test_database_initializes_with_expected_schema(tmp_path: Path) -> None:
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
        indexes = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_schema
                WHERE type = 'index'
                  AND name NOT LIKE 'sqlite_%'
                """
            )
        }

    assert tables == {"categories", "order_items", "orders", "products"}
    assert {
        "completed_order_lines",
        "dashboard_summary",
        "margin_by_product",
        "monthly_performance",
        "product_revenue_rank",
        "revenue_by_category",
        "revenue_by_product",
    }.issubset(views)
    assert indexes == {
        "idx_order_items_order_id",
        "idx_order_items_product_id",
        "idx_orders_status_date",
        "idx_products_category_active",
    }


def test_generated_record_counts_and_statuses(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        count_row = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM categories),
                (SELECT COUNT(*) FROM products),
                (SELECT COUNT(*) FROM orders),
                (SELECT COUNT(*) FROM order_items)
            """
        ).fetchone()
        counts = {
            "categories": count_row[0],
            "products": count_row[1],
            "orders": count_row[2],
            "order_items": count_row[3],
        }
        statuses = dict(
            connection.execute(
                """
                SELECT order_status, COUNT(*)
                FROM orders
                GROUP BY order_status
                """
            )
        )
        active_products = connection.execute(
            "SELECT COUNT(*) FROM products WHERE active = 1"
        ).fetchone()[0]

    assert counts["categories"] == 5
    assert counts["products"] == 20
    assert counts["orders"] == 408
    assert counts["order_items"] >= 700
    assert statuses == {"CANCELLED": 24, "COMPLETED": 360, "PENDING": 24}
    assert active_products == 18


def test_completed_records_cover_24_months_and_every_category(
    database_path: Path,
) -> None:
    with sqlite3.connect(database_path) as connection:
        bounds = connection.execute(
            """
            SELECT
                MIN(order_date),
                MAX(order_date),
                COUNT(DISTINCT SUBSTR(order_date, 1, 7))
            FROM orders
            WHERE order_status = 'COMPLETED'
            """
        ).fetchone()
        categories = connection.execute(
            """
            SELECT COUNT(DISTINCT category_id)
            FROM completed_order_lines
            """
        ).fetchone()[0]
        monthly_categories = connection.execute(
            """
            SELECT
                SUBSTR(order_date, 1, 7) AS month,
                COUNT(DISTINCT category_id)
            FROM completed_order_lines
            GROUP BY month
            """
        ).fetchall()

    assert bounds == ("2024-07-01", "2026-06-30", 24)
    assert categories == 5
    assert len(monthly_categories) == 24
    assert all(category_count == 5 for _, category_count in monthly_categories)


def test_noncompleted_orders_do_not_contribute_to_analytics(
    database_path: Path,
) -> None:
    with sqlite3.connect(database_path) as connection:
        completed_view_orders = connection.execute(
            "SELECT COUNT(DISTINCT order_id) FROM completed_order_lines"
        ).fetchone()[0]
        all_orders = connection.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]

    assert completed_view_orders == 360
    assert all_orders > completed_view_orders


def test_sqlite_integrity_and_foreign_keys(database_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        foreign_key_issues = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

    assert integrity == ("ok",)
    assert foreign_key_issues == []

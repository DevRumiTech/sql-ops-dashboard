"""Page and JSON API routes for dashboard analytics."""

from __future__ import annotations

import sqlite3

from flask import Blueprint, jsonify, render_template

from .db import query_all, query_one

dashboard = Blueprint("dashboard", __name__)

SUMMARY_SQL = """
    SELECT
        total_revenue,
        total_gross_margin,
        valid_orders,
        active_products
    FROM dashboard_summary
"""

REVENUE_BY_PRODUCT_SQL = """
    SELECT
        revenue.product_id,
        revenue.product_name,
        categories.category_name,
        ROUND(revenue.revenue, 2) AS revenue
    FROM revenue_by_product AS revenue
    JOIN products
        ON products.product_id = revenue.product_id
    JOIN categories
        ON categories.category_id = products.category_id
    ORDER BY revenue.revenue DESC, revenue.product_name ASC
"""

REVENUE_BY_CATEGORY_SQL = """
    SELECT
        category_name,
        ROUND(revenue, 2) AS revenue
    FROM revenue_by_category
    ORDER BY revenue DESC, category_name ASC
"""

MARGINS_BY_PRODUCT_SQL = """
    SELECT
        product_id,
        product_name,
        ROUND(revenue, 2) AS revenue,
        ROUND(total_cost, 2) AS total_cost,
        ROUND(gross_margin, 2) AS gross_margin,
        CASE
            WHEN revenue > 0
                THEN ROUND((gross_margin / revenue) * 100.0, 1)
            ELSE 0.0
        END AS gross_margin_rate
    FROM margin_by_product
    ORDER BY gross_margin DESC, product_name ASC
"""

PRODUCT_RANKINGS_SQL = """
    SELECT
        product_id,
        product_name,
        ROUND(revenue, 2) AS revenue,
        revenue_rank
    FROM product_revenue_rank
    ORDER BY revenue_rank ASC, product_name ASC
"""


@dashboard.get("/")
def home() -> str:
    """Render the single-page dashboard."""
    return render_template("index.html")


@dashboard.get("/health")
def health():
    """Confirm that Flask can query the configured SQLite database."""
    result = query_one(
        """
        SELECT COUNT(*) AS table_count
        FROM sqlite_schema
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        """
    )
    table_count = int(result["table_count"]) if result else 0

    if table_count == 0:
        raise sqlite3.DatabaseError("Database schema is unavailable")

    return jsonify(
        {
            "application": "SQL Ops Dashboard",
            "database": "available",
            "status": "ok",
            "table_count": table_count,
        }
    )


@dashboard.get("/api/summary")
def summary():
    """Return top-level operational metrics."""
    result = query_one(SUMMARY_SQL)
    if result is None:
        raise sqlite3.DatabaseError("Summary view returned no result")
    return jsonify({"generated_data": True, "summary": result})


@dashboard.get("/api/revenue/products")
def revenue_by_product():
    """Return recognized revenue grouped by product."""
    return _data_response(query_all(REVENUE_BY_PRODUCT_SQL))


@dashboard.get("/api/revenue/categories")
def revenue_by_category():
    """Return recognized revenue grouped by category."""
    return _data_response(query_all(REVENUE_BY_CATEGORY_SQL))


@dashboard.get("/api/margins/products")
def margins_by_product():
    """Return product-level revenue, cost, and gross margin."""
    return _data_response(query_all(MARGINS_BY_PRODUCT_SQL))


@dashboard.get("/api/rankings/products")
def product_rankings():
    """Return product revenue rankings in rank order."""
    return _data_response(query_all(PRODUCT_RANKINGS_SQL))


def _data_response(rows: list[dict[str, object]]):
    """Wrap a result list in one predictable API envelope."""
    return jsonify({"count": len(rows), "data": rows, "generated_data": True})

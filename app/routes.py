"""Page, health, metadata, and filtered analytics API routes."""

from __future__ import annotations

import calendar
import sqlite3
from datetime import date, timedelta
from typing import Any, Literal

from flask import Blueprint, Response, jsonify, render_template

from .db import query_all, query_one
from .filters import (
    AnalyticsFilters,
    line_filter_sql,
    parse_analytics_filters,
)

dashboard = Blueprint("dashboard", __name__)
TrendGranularity = Literal["daily", "weekly", "monthly"]


@dashboard.get("/")
def home() -> str:
    """Render the read-only single-page dashboard."""
    return render_template("index.html")


@dashboard.get("/health")
def health() -> Response:
    """Confirm that Flask can open and query the configured database."""
    result = query_one(
        """
        SELECT
            COUNT(*) AS table_count,
            (
                SELECT COUNT(*)
                FROM completed_order_lines
            ) AS completed_order_lines
        FROM sqlite_schema
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        """
    )
    if not result or int(result["table_count"]) == 0:
        raise sqlite3.DatabaseError("Database schema is unavailable")
    return jsonify(
        {
            "application": "SQL Ops Dashboard",
            "database": "available",
            "status": "ok",
            "table_count": int(result["table_count"]),
        }
    )


@dashboard.get("/api/meta")
def metadata() -> Response:
    """Return global dataset bounds, counts, and filter categories."""
    meta = query_one(
        """
        SELECT
            MIN(order_date) AS minimum_completed_order_date,
            MAX(order_date) AS maximum_completed_order_date,
            COUNT(DISTINCT order_id) AS completed_order_count,
            COUNT(*) AS completed_order_line_count,
            (
                SELECT COUNT(*)
                FROM products
            ) AS product_count,
            (
                SELECT COUNT(*)
                FROM products
                WHERE active = 1
            ) AS active_product_count
        FROM completed_order_lines
        """
    )
    categories = query_all(
        """
        SELECT category_name
        FROM categories
        ORDER BY category_name
        """
    )
    if meta is None:
        raise sqlite3.DatabaseError("Metadata query returned no result")
    meta["available_categories"] = [
        row["category_name"] for row in categories
    ]
    return jsonify({"generated_data": True, "meta": meta})


@dashboard.get("/api/summary")
def summary() -> Response:
    """Return selected metrics and equal-length prior-period comparisons."""
    filters = parse_analytics_filters()
    selected = _summary_values(filters)
    previous_filters = filters.previous_period()
    previous = (
        _summary_values(previous_filters) if previous_filters else None
    )
    comparison = {
        "completed_orders_pct": _percentage_change(
            selected["completed_orders"],
            previous["completed_orders"] if previous else None,
        ),
        "gross_margin_pct": _percentage_change(
            selected["gross_margin"],
            previous["gross_margin"] if previous else None,
        ),
        "recognized_revenue_pct": _percentage_change(
            selected["recognized_revenue"],
            previous["recognized_revenue"] if previous else None,
        ),
    }
    return jsonify(
        {
            "comparison": comparison,
            "filters": filters.as_dict(),
            "generated_data": True,
            "previous_period": (
                previous_filters.as_dict() if previous_filters else None
            ),
            "summary": selected,
        }
    )


@dashboard.get("/api/revenue/products")
def revenue_by_product() -> Response:
    """Return selected recognized revenue grouped by product."""
    filters = parse_analytics_filters()
    performance_sql, parameters = _product_performance_sql(filters)
    rows = query_all(
        f"""
        {performance_sql}
        SELECT
            product_id,
            product_name,
            category_name,
            revenue
        FROM product_performance
        ORDER BY revenue DESC, product_name ASC
        """,
        parameters,
    )
    return _data_response(rows, filters)


@dashboard.get("/api/revenue/categories")
def revenue_by_category() -> Response:
    """Return selected recognized revenue grouped by category."""
    filters = parse_analytics_filters()
    where_clause, parameters = line_filter_sql(filters)
    rows = query_all(
        f"""
        SELECT
            line.category_name,
            ROUND(
                SUM(line.recognized_revenue_cents) / 100.0,
                2
            ) AS revenue
        FROM completed_order_lines AS line
        {where_clause}
        GROUP BY line.category_id, line.category_name
        HAVING SUM(line.recognized_revenue_cents) > 0
        ORDER BY revenue DESC, line.category_name ASC
        """,
        parameters,
    )
    return _data_response(rows, filters)


@dashboard.get("/api/margins/products")
def margins_by_product() -> Response:
    """Return selected product revenue, cost, margin, and margin rate."""
    filters = parse_analytics_filters()
    performance_sql, parameters = _product_performance_sql(filters)
    rows = query_all(
        f"""
        {performance_sql}
        SELECT
            product_id,
            product_name,
            category_name,
            revenue,
            total_cost,
            gross_margin,
            gross_margin_rate
        FROM product_performance
        ORDER BY gross_margin DESC, product_name ASC
        """,
        parameters,
    )
    return _data_response(rows, filters)


@dashboard.get("/api/rankings/products")
def product_rankings() -> Response:
    """Return selected product performance in ranked revenue order."""
    filters = parse_analytics_filters()
    performance_sql, parameters = _product_performance_sql(filters)
    rows = query_all(
        f"""
        {performance_sql},
        ranked_products AS (
            SELECT
                product_id,
                product_name,
                category_name,
                revenue,
                total_cost,
                gross_margin,
                gross_margin_rate,
                RANK() OVER (
                    ORDER BY revenue DESC
                ) AS revenue_rank
            FROM product_performance
        )
        SELECT *
        FROM ranked_products
        ORDER BY revenue_rank ASC, product_name ASC
        """,
        parameters,
    )
    return _data_response(rows, filters)


@dashboard.get("/api/trends/monthly")
def monthly_trends() -> Response:
    """Return a complete daily, weekly, or monthly performance series."""
    filters = parse_analytics_filters()
    start_date, end_date = _trend_date_range(filters)
    granularity = _trend_granularity(start_date, end_date)
    where_clause, parameters = line_filter_sql(filters)
    rows = query_all(
        f"""
        SELECT
            line.order_date,
            SUM(line.recognized_revenue_cents) AS revenue_cents,
            SUM(line.gross_margin_cents) AS gross_margin_cents,
            COUNT(DISTINCT line.order_id) AS completed_orders,
            COUNT(*) AS order_lines
        FROM completed_order_lines AS line
        {where_clause}
        GROUP BY line.order_date
        ORDER BY line.order_date
        """,
        parameters,
    )
    trend_rows = _complete_trend_rows(
        rows,
        start_date,
        end_date,
        granularity,
    )
    return jsonify(
        {
            "count": len(trend_rows),
            "data": trend_rows,
            "end_date": end_date.isoformat(),
            "filters": filters.as_dict(),
            "generated_data": True,
            "granularity": granularity,
            "start_date": start_date.isoformat(),
        }
    )


def _summary_values(filters: AnalyticsFilters) -> dict[str, int | float]:
    where_clause, parameters = line_filter_sql(filters)
    result = query_one(
        f"""
        SELECT
            ROUND(
                COALESCE(SUM(line.recognized_revenue_cents), 0)
                / 100.0,
                2
            ) AS recognized_revenue,
            ROUND(
                COALESCE(SUM(line.gross_margin_cents), 0)
                / 100.0,
                2
            ) AS gross_margin,
            COUNT(DISTINCT line.order_id) AS completed_orders,
            COUNT(
                DISTINCT CASE
                    WHEN line.active = 1 THEN line.product_id
                END
            ) AS active_products,
            COUNT(line.order_item_id) AS order_lines_analyzed
        FROM completed_order_lines AS line
        {where_clause}
        """,
        parameters,
    )
    if result is None:
        raise sqlite3.DatabaseError("Summary query returned no result")
    return result


def _product_performance_sql(
    filters: AnalyticsFilters,
) -> tuple[str, tuple[Any, ...]]:
    where_clause, parameters = line_filter_sql(filters)
    return (
        f"""
        WITH product_performance AS (
            SELECT
                line.product_id,
                line.product_name,
                line.category_name,
                ROUND(
                    SUM(line.recognized_revenue_cents) / 100.0,
                    2
                ) AS revenue,
                ROUND(
                    SUM(line.cost_of_goods_cents) / 100.0,
                    2
                ) AS total_cost,
                ROUND(
                    SUM(line.gross_margin_cents) / 100.0,
                    2
                ) AS gross_margin,
                CASE
                    WHEN SUM(line.recognized_revenue_cents) > 0
                        THEN ROUND(
                            SUM(line.gross_margin_cents)
                            * 100.0
                            / SUM(line.recognized_revenue_cents),
                            1
                        )
                    ELSE NULL
                END AS gross_margin_rate
            FROM completed_order_lines AS line
            {where_clause}
            GROUP BY
                line.product_id,
                line.product_name,
                line.category_name
            HAVING SUM(line.recognized_revenue_cents) > 0
        )
        """,
        parameters,
    )


def _percentage_change(
    current_value: int | float,
    previous_value: int | float | None,
) -> float | None:
    if previous_value is None or previous_value == 0:
        return None
    return round(
        (float(current_value) - float(previous_value))
        * 100.0
        / abs(float(previous_value)),
        1,
    )


def _trend_date_range(filters: AnalyticsFilters) -> tuple[date, date]:
    """Resolve optional filter dates against completed-order dataset bounds."""
    bounds = query_one(
        """
        SELECT
            MIN(order_date) AS start_date,
            MAX(order_date) AS end_date
        FROM completed_order_lines
        """
    )
    if not bounds or not bounds["start_date"] or not bounds["end_date"]:
        raise sqlite3.DatabaseError("Completed-order date bounds are unavailable")

    dataset_start = date.fromisoformat(bounds["start_date"])
    dataset_end = date.fromisoformat(bounds["end_date"])
    start_date = filters.start_date or dataset_start
    end_date = filters.end_date or dataset_end
    if start_date > end_date:
        if filters.start_date and filters.end_date is None:
            end_date = start_date
        elif filters.end_date and filters.start_date is None:
            start_date = end_date
    return start_date, end_date


def _trend_granularity(
    start_date: date, end_date: date
) -> TrendGranularity:
    """Choose a trend grain from the inclusive selected-period length."""
    day_count = (end_date - start_date).days + 1
    if day_count <= 45:
        return "daily"
    if day_count <= 180:
        return "weekly"
    return "monthly"


def _complete_trend_rows(
    rows: list[dict[str, Any]],
    start_date: date,
    end_date: date,
    granularity: TrendGranularity,
) -> list[dict[str, Any]]:
    """Fill every selected period and aggregate daily SQL results into it."""
    rows_by_date = {date.fromisoformat(row["order_date"]): row for row in rows}
    completed: list[dict[str, Any]] = []
    for period, label, period_start, period_end in _trend_periods(
        start_date,
        end_date,
        granularity,
    ):
        period_rows = [
            rows_by_date[day]
            for day in _date_sequence(period_start, period_end)
            if day in rows_by_date
        ]
        revenue_cents = sum(int(row["revenue_cents"]) for row in period_rows)
        margin_cents = sum(
            int(row["gross_margin_cents"]) for row in period_rows
        )
        completed.append(
            {
                "gross_margin": round(margin_cents / 100.0, 2),
                "has_completed_orders": any(
                    int(row["completed_orders"]) > 0 for row in period_rows
                ),
                "label": label,
                "period": period,
                "revenue": round(revenue_cents / 100.0, 2),
            }
        )
    return completed


def _trend_periods(
    start_date: date,
    end_date: date,
    granularity: TrendGranularity,
) -> list[tuple[str, str, date, date]]:
    """Return ordered period keys, labels, and inclusive date boundaries."""
    if granularity == "daily":
        return [
            (day.isoformat(), _day_label(day), day, day)
            for day in _date_sequence(start_date, end_date)
        ]

    periods: list[tuple[str, str, date, date]] = []
    if granularity == "weekly":
        period_start = start_date
        while period_start <= end_date:
            period_end = min(period_start + timedelta(days=6), end_date)
            periods.append(
                (
                    period_start.isoformat(),
                    _week_label(period_start, period_end),
                    period_start,
                    period_end,
                )
            )
            period_start = period_end + timedelta(days=1)
        return periods

    month_start = start_date.replace(day=1)
    while month_start <= end_date:
        month_end = month_start.replace(
            day=calendar.monthrange(month_start.year, month_start.month)[1]
        )
        periods.append(
            (
                f"{month_start.year:04d}-{month_start.month:02d}",
                _month_label(month_start),
                max(start_date, month_start),
                min(end_date, month_end),
            )
        )
        month_start = (month_end + timedelta(days=1)).replace(day=1)
    return periods


def _date_sequence(start_date: date, end_date: date) -> list[date]:
    """Return every calendar date in one inclusive range."""
    return [
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days + 1)
    ]


def _day_label(value: date) -> str:
    return f"{calendar.month_abbr[value.month]} {value.day}"


def _week_label(start_date: date, end_date: date) -> str:
    start_month = calendar.month_abbr[start_date.month]
    end_month = calendar.month_abbr[end_date.month]
    if start_date.year != end_date.year:
        return (
            f"{start_month} {start_date.day}, {start_date.year}"
            f"–{end_month} {end_date.day}, {end_date.year}"
        )
    if start_date.month == end_date.month:
        return f"{start_month} {start_date.day}–{end_date.day}"
    return f"{start_month} {start_date.day}–{end_month} {end_date.day}"


def _month_label(value: date) -> str:
    return f"{calendar.month_abbr[value.month]} {value.year % 100:02d}"


def _data_response(
    rows: list[dict[str, Any]], filters: AnalyticsFilters
) -> Response:
    return jsonify(
        {
            "count": len(rows),
            "data": rows,
            "filters": filters.as_dict(),
            "generated_data": True,
        }
    )

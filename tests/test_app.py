"""Dashboard page, API, filter, read-only, and error-response tests."""

from __future__ import annotations

import hashlib
import importlib.util
import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.db import get_db

SECURITY_HEADERS = {
    "Content-Security-Policy",
    "Permissions-Policy",
    "Referrer-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
}


def test_application_creation(database_path: Path) -> None:
    application = create_app({"DATABASE": database_path, "TESTING": True})

    assert application.name == "app"
    assert application.config["DATABASE"] == database_path
    assert application.static_url_path == ""


def test_vercel_entry_file_exports_flask_app() -> None:
    entry_path = Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("vercel_entry", entry_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert isinstance(module.app, Flask)


def test_home_page_content_and_controls(client: FlaskClient) -> None:
    response = client.get("/")
    html = response.get_data(as_text=True)
    normalized = " ".join(html.split())

    assert response.status_code == 200
    assert (
        "A dashboard for tracking recognized revenue, product margins, and "
        "category performance using Flask APIs and SQLite."
    ) in normalized
    assert "<h1>SQL Ops Dashboard</h1>" in html
    assert "Retail Operations Analytics" in html
    assert "Local demonstration" not in html
    assert "Portfolio demo" not in html
    assert "Dashboard loaded" not in html
    assert html.count("All records are generated demonstration data.") == 1
    assert 'id="dashboard-status"' in html
    assert 'aria-live="polite"' in html
    assert "Loading dashboard data…" in html
    assert 'id="period-preset"' in html
    assert '<label for="period-preset">Date period</label>' in html
    assert "<option value=\"30-days\">Latest 30 days</option>" in html
    assert "<option value=\"90-days\">Latest 90 days</option>" in html
    assert (
        '<option value="12-months" selected>Latest 12 months</option>'
        in html
    )
    assert "<option value=\"all\">All available data</option>" in html
    assert "<option value=\"custom\">Custom range</option>" in html
    assert 'id="latest-data-notice"' in html
    assert "Determining latest data date…" in html
    assert "Data through June 30, 2026" not in html
    for control_id in ("start-date", "end-date"):
        date_input = re.search(
            rf'<input[^>]+id="{control_id}"[^>]*>',
            html,
        )
        assert date_input
        date_input_markup = date_input.group(0)
        assert "readonly" in date_input_markup
        assert "disabled" not in date_input_markup
        assert 'aria-describedby="date-range-helper"' in date_input_markup
    assert 'id="date-range-helper"' in html
    assert "Dates are set automatically by the selected period." in html
    assert 'id="category-filter"' in html
    assert 'id="reset-filters"' in html
    assert 'id="download-csv"' in html
    assert html.count('class="sort-button"') == 6
    assert 'aria-sort="descending"' in html
    assert "Product Revenue Ranking" not in html
    assert 'id="ranking-list"' not in html
    assert "Showing the top 10 products by recognized revenue." in html
    assert "Showing the top 8 products by gross margin." in html


@pytest.mark.parametrize(
    ("path", "content_type"),
    [
        ("/styles.css", "text/css"),
        ("/app.js", "text/javascript"),
        ("/favicon.svg", "image/svg+xml"),
    ],
)
def test_public_assets_return_200(
    client: FlaskClient, path: str, content_type: str
) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.content_type.startswith(content_type)


def test_frontend_assets_include_required_behaviors(client: FlaskClient) -> None:
    javascript = client.get("/app.js").get_data(as_text=True)
    css = client.get("/styles.css").get_data(as_text=True)

    assert "Dashboard data could not be loaded. Please try again." in javascript
    assert "Dashboard loaded" not in javascript
    assert 'showStatus("Loading dashboard data…")' in javascript
    assert "statusRegion.hidden = true" in javascript
    assert "bar.style.width" in javascript
    assert "AbortController" in javascript
    assert "setTimeout(renderProductTable, 180)" in javascript
    assert "text/csv;charset=utf-8" in javascript
    assert "createElementNS" in javascript
    assert "const PRODUCT_MIX_LIMIT = 10;" in javascript
    assert ".slice(0, PRODUCT_MIX_LIMIT)" in javascript
    assert "const MARGIN_CARD_LIMIT = 8;" in javascript
    assert ".slice(0, MARGIN_CARD_LIMIT)" in javascript
    assert "renderRankings" not in javascript
    assert "rankingList" not in javascript
    assert "state.products.filter" in javascript
    assert "state.displayedProducts = filtered;" in javascript
    assert "payload.meta.maximum_completed_order_date" in javascript
    assert "Data date unavailable" in javascript
    assert "Data through ${formattedDate}" in javascript
    assert "fullDateFormatter.format(parseIsoDate(value))" in javascript
    assert "renderLatestDataNotice(null);" in javascript
    assert 'applyPreset("12-months");' in javascript
    assert 'shiftUtcDays(maximum, -29)' in javascript
    assert 'shiftUtcDays(maximum, -89)' in javascript
    assert "maximum.getUTCMonth(), 1" in javascript
    assert "elements.startDate.readOnly = !custom;" in javascript
    assert "elements.endDate.readOnly = !custom;" in javascript
    assert "elements.startDate.disabled" not in javascript
    assert "elements.endDate.disabled" not in javascript
    assert 'elements.periodPreset.addEventListener("change"' in javascript
    assert "applyPreset(elements.periodPreset.value);" in javascript
    assert "Choose a start and end date." in javascript
    assert "Dates are set automatically by the selected period." in javascript
    assert "let start = minimum;" in javascript
    assert "let end = maximum;" in javascript
    assert 'if (preset !== "all")' in javascript
    assert "elements.trend.getBoundingClientRect().width" in javascript
    assert "Math.min(900, Math.max(320, availableWidth || 900))" in javascript
    assert "const edgePadding = compact ? 24 : 32;" in javascript
    assert "const dataLeft = plot.left + edgePadding;" in javascript
    assert "const dataRight = plot.right - edgePadding;" in javascript
    assert "Daily Revenue and Gross Margin" in javascript
    assert "Weekly Revenue and Gross Margin" in javascript
    assert "Monthly Revenue and Gross Margin" in javascript
    assert "Recognized revenue and gross margin by calendar day." in javascript
    assert (
        "Recognized revenue and gross margin by selected seven-day period."
        in javascript
    )
    assert "Recognized revenue and gross margin by calendar month." in javascript
    assert "row.has_completed_orders" in javascript
    assert 'label.textContent = row.label;' in javascript
    assert 'renderTrend(payload);' in javascript
    assert "const points = rows.map" in javascript
    assert ".dashboard-status[hidden]" in css
    readonly_date_rule = re.search(
        r'input\[type="date"\]\[readonly\]\s*\{([^}]*)\}',
        css,
    )
    assert readonly_date_rule
    readonly_date_styles = readonly_date_rule.group(1)
    assert "background: #f0f2f3;" in readonly_date_styles
    assert "color: var(--ink);" in readonly_date_styles
    assert "cursor: default;" in readonly_date_styles
    assert "box-shadow" not in readonly_date_styles
    assert "border-left" not in readonly_date_styles
    assert "gradient" not in readonly_date_styles
    assert "opacity" not in readonly_date_styles
    assert "border: 1px solid #aab4bc;" in css
    assert ".date-range-helper" in css
    assert ".latest-data-notice" in css
    assert ".sort-button" in css
    assert ".environment-badge" not in css
    assert ".ranking-list" not in css
    assert ".ranking-item" not in css
    assert "min-width: 320px;" not in css
    assert "min-width: 700px;" not in css
    assert "border-inline-start" not in css
    assert "padding-inline-start" not in css
    assert "gradient(" not in css
    assert css.count("overflow-x: auto;") == 1
    assert "width: min(calc(100% - 40px), 1200px);" in css
    assert "@media (max-width: 1080px)" in css
    assert "@media (max-width: 900px)" in css
    assert "@media (max-width: 760px)" in css
    assert "@media (max-width: 420px)" in css

    table_wrap_rule = re.search(r"\.table-wrap\s*\{([^}]*)\}", css)
    trend_scroll_rule = re.search(r"\.trend-scroll\s*\{([^}]*)\}", css)
    trend_svg_rule = re.search(r"\.trend-scroll svg\s*\{([^}]*)\}", css)
    site_header_rule = re.search(r"\.site-header\s*\{([^}]*)\}", css)
    assert table_wrap_rule
    assert trend_scroll_rule
    assert trend_svg_rule
    assert site_header_rule
    assert "overflow-x: auto;" in table_wrap_rule.group(1)
    assert "overflow: hidden;" in trend_scroll_rule.group(1)
    assert "min-width: 0;" in trend_svg_rule.group(1)
    assert "background: var(--surface);" in site_header_rule.group(1)
    assert "gradient" not in site_header_rule.group(1)
    assert (
        '"Helvetica Neue", Helvetica, Arial, system-ui, -apple-system, '
        "sans-serif"
    ) in css
    assert "--accent: #e85d3f;" in css
    assert "--accent-hover: #cc4c32;" in css
    assert "--teal: #147a6c;" in css
    assert "--blue-dark: #24435a;" in css
    assert ".trend-line-revenue" in css
    assert "stroke: var(--accent);" in css
    assert ".trend-line.trend-line-margin" in css
    assert "stroke-dasharray: 8 5;" in css
    assert "border-top: 3px dashed var(--teal);" in css
    assert "background: var(--accent);" in css
    assert "background: var(--teal);" in css
    assert 'th[aria-sort="descending"] .sort-button' in css


def test_default_period_keeps_all_products_for_table_and_apis(
    client: FlaskClient,
) -> None:
    query = {
        "end_date": "2026-06-30",
        "start_date": "2025-07-01",
    }
    revenue_rows = client.get(
        "/api/revenue/products", query_string=query
    ).get_json()["data"]
    margin_rows = client.get(
        "/api/margins/products", query_string=query
    ).get_json()["data"]
    table_rows = client.get(
        "/api/rankings/products", query_string=query
    ).get_json()["data"]

    assert len(revenue_rows) == 20
    assert len(margin_rows) == 20
    assert len(table_rows) == 20
    assert [row["revenue"] for row in revenue_rows] == sorted(
        (row["revenue"] for row in revenue_rows),
        reverse=True,
    )
    assert [row["gross_margin"] for row in margin_rows] == sorted(
        (row["gross_margin"] for row in margin_rows),
        reverse=True,
    )


def test_health_and_metadata_routes(client: FlaskClient) -> None:
    health_response = client.get("/health")
    health = health_response.get_json()
    meta_response = client.get("/api/meta")
    meta = meta_response.get_json()["meta"]

    assert health_response.status_code == 200
    assert health == {
        "application": "SQL Ops Dashboard",
        "database": "available",
        "status": "ok",
        "table_count": 4,
    }
    assert meta_response.status_code == 200
    assert meta["minimum_completed_order_date"] == "2024-07-01"
    assert meta["maximum_completed_order_date"] == "2026-06-30"
    assert meta["completed_order_count"] == 360
    assert meta["completed_order_line_count"] > 500
    assert meta["product_count"] == 20
    assert meta["active_product_count"] == 18
    assert len(meta["available_categories"]) == 5


@pytest.mark.parametrize(
    ("path", "required_keys"),
    [
        (
            "/api/revenue/products",
            {"product_id", "product_name", "category_name", "revenue"},
        ),
        (
            "/api/revenue/categories",
            {"category_name", "revenue"},
        ),
        (
            "/api/margins/products",
            {
                "category_name",
                "gross_margin",
                "gross_margin_rate",
                "product_id",
                "product_name",
                "revenue",
                "total_cost",
            },
        ),
        (
            "/api/rankings/products",
            {
                "category_name",
                "gross_margin",
                "gross_margin_rate",
                "product_id",
                "product_name",
                "revenue",
                "revenue_rank",
                "total_cost",
            },
        ),
        (
            "/api/trends/monthly",
            {
                "gross_margin",
                "has_completed_orders",
                "label",
                "period",
                "revenue",
            },
        ),
    ],
)
def test_list_api_contracts(
    client: FlaskClient, path: str, required_keys: set[str]
) -> None:
    response = client.get(path)
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["generated_data"] is True
    assert payload["count"] == len(payload["data"])
    assert payload["data"]
    assert required_keys.issubset(payload["data"][0])


def test_summary_api_contract_and_numeric_values(client: FlaskClient) -> None:
    response = client.get("/api/summary")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["generated_data"] is True
    assert set(payload["summary"]) == {
        "active_products",
        "completed_orders",
        "gross_margin",
        "order_lines_analyzed",
        "recognized_revenue",
    }
    assert all(
        isinstance(value, (int, float))
        for value in payload["summary"].values()
    )
    assert payload["previous_period"] is None
    assert all(value is None for value in payload["comparison"].values())


def test_product_revenue_and_default_trends_are_ordered(
    client: FlaskClient,
) -> None:
    product_rows = client.get("/api/revenue/products").get_json()["data"]
    trend_payload = client.get("/api/trends/monthly").get_json()
    trend_rows = trend_payload["data"]

    revenues = [row["revenue"] for row in product_rows]
    period_keys = [row["period"] for row in trend_rows]
    assert revenues == sorted(revenues, reverse=True)
    assert trend_payload["granularity"] == "monthly"
    assert period_keys == sorted(period_keys)
    assert len(period_keys) == 24
    assert all(
        isinstance(row["revenue"], (int, float)) for row in trend_rows
    )


def test_date_filtering_and_previous_period_comparisons(
    client: FlaskClient,
) -> None:
    query = {"start_date": "2026-06-01", "end_date": "2026-06-30"}
    payload = client.get("/api/summary", query_string=query).get_json()
    trends = client.get("/api/trends/monthly", query_string=query).get_json()

    assert payload["summary"]["completed_orders"] == 15
    assert payload["summary"]["order_lines_analyzed"] > 15
    assert payload["previous_period"] == {
        "category": None,
        "end_date": "2026-05-31",
        "start_date": "2026-05-02",
    }
    assert all(
        isinstance(value, (int, float))
        for value in payload["comparison"].values()
    )
    assert trends["granularity"] == "daily"
    assert trends["start_date"] == "2026-06-01"
    assert trends["end_date"] == "2026-06-30"
    assert trends["count"] == 30
    assert [row["period"] for row in trends["data"]] == [
        (date(2026, 6, 1) + timedelta(days=offset)).isoformat()
        for offset in range(30)
    ]
    assert trends["data"][0]["label"] == "Jun 1"
    assert trends["data"][-1]["label"] == "Jun 30"
    assert any(
        not row["has_completed_orders"] for row in trends["data"]
    )
    assert sum(row["revenue"] for row in trends["data"]) == pytest.approx(
        payload["summary"]["recognized_revenue"]
    )
    assert sum(
        row["gross_margin"] for row in trends["data"]
    ) == pytest.approx(payload["summary"]["gross_margin"])


def test_ninety_day_trend_uses_complete_weekly_periods(
    client: FlaskClient,
) -> None:
    query = {"start_date": "2026-04-02", "end_date": "2026-06-30"}
    trend = client.get(
        "/api/trends/monthly", query_string=query
    ).get_json()
    summary = client.get("/api/summary", query_string=query).get_json()[
        "summary"
    ]

    assert trend["granularity"] == "weekly"
    assert trend["count"] == 13
    assert trend["data"][0] == {
        "gross_margin": 508.16,
        "has_completed_orders": True,
        "label": "Apr 2–8",
        "period": "2026-04-02",
        "revenue": 1054.16,
    }
    assert trend["data"][-1]["label"] == "Jun 25–30"
    assert trend["data"][-1]["period"] == "2026-06-25"
    assert [row["period"] for row in trend["data"]] == sorted(
        row["period"] for row in trend["data"]
    )
    assert all(
        isinstance(row["revenue"], (int, float))
        and isinstance(row["gross_margin"], (int, float))
        for row in trend["data"]
    )
    assert sum(row["revenue"] for row in trend["data"]) == pytest.approx(
        summary["recognized_revenue"]
    )
    assert sum(
        row["gross_margin"] for row in trend["data"]
    ) == pytest.approx(summary["gross_margin"])


def test_latest_twelve_months_returns_twelve_monthly_records(
    client: FlaskClient,
) -> None:
    query = {"start_date": "2025-07-01", "end_date": "2026-06-30"}
    payload = client.get(
        "/api/trends/monthly", query_string=query
    ).get_json()

    assert payload["granularity"] == "monthly"
    assert payload["count"] == 12
    assert payload["start_date"] == "2025-07-01"
    assert payload["end_date"] == "2026-06-30"
    assert payload["data"][0]["period"] == "2025-07"
    assert payload["data"][0]["label"] == "Jul 25"
    assert payload["data"][-1]["period"] == "2026-06"
    assert payload["data"][-1]["label"] == "Jun 26"


@pytest.mark.parametrize(
    ("day_count", "granularity"),
    [
        (45, "daily"),
        (46, "weekly"),
        (180, "weekly"),
        (181, "monthly"),
    ],
)
def test_custom_range_selects_granularity_by_inclusive_length(
    client: FlaskClient,
    day_count: int,
    granularity: str,
) -> None:
    start = date(2026, 1, 1)
    end = start + timedelta(days=day_count - 1)
    response = client.get(
        "/api/trends/monthly",
        query_string={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.get_json()["granularity"] == granularity


def test_missing_daily_and_weekly_periods_are_zero_filled(
    client: FlaskClient,
) -> None:
    daily = client.get(
        "/api/trends/monthly",
        query_string={
            "start_date": "2030-01-01",
            "end_date": "2030-01-31",
        },
    ).get_json()
    weekly = client.get(
        "/api/trends/monthly",
        query_string={
            "start_date": "2030-01-01",
            "end_date": "2030-03-01",
        },
    ).get_json()

    assert daily["granularity"] == "daily"
    assert daily["count"] == 31
    assert weekly["granularity"] == "weekly"
    assert weekly["count"] == 9
    for row in daily["data"] + weekly["data"]:
        assert row["revenue"] == 0.0
        assert row["gross_margin"] == 0.0
        assert row["has_completed_orders"] is False


@pytest.mark.parametrize(
    "query",
    [
        {"start_date": "2026-06-01", "end_date": "2026-06-30"},
        {"start_date": "2026-04-02", "end_date": "2026-06-30"},
        {"start_date": "2025-07-01", "end_date": "2026-06-30"},
        {},
        {"start_date": "2026-01-01", "end_date": "2026-02-15"},
    ],
    ids=[
        "latest-30-days",
        "latest-90-days",
        "latest-12-months",
        "all-available-data",
        "custom-range",
    ],
)
@pytest.mark.parametrize(
    "category",
    [None, "Office", "Home Technology", "Kitchen", "Fitness", "Audio"],
)
def test_trend_totals_match_summary_for_ranges_and_categories(
    client: FlaskClient,
    query: dict[str, str],
    category: str | None,
) -> None:
    selected_query = dict(query)
    if category:
        selected_query["category"] = category

    trend_response = client.get(
        "/api/trends/monthly", query_string=selected_query
    )
    summary_response = client.get(
        "/api/summary", query_string=selected_query
    )
    trend = trend_response.get_json()
    summary = summary_response.get_json()["summary"]

    assert trend_response.status_code == 200
    assert summary_response.status_code == 200
    assert trend["filters"]["category"] == category
    assert sum(row["revenue"] for row in trend["data"]) == pytest.approx(
        summary["recognized_revenue"],
        abs=0.01,
    )
    assert sum(
        row["gross_margin"] for row in trend["data"]
    ) == pytest.approx(summary["gross_margin"], abs=0.01)


def test_category_and_combined_filtering(client: FlaskClient) -> None:
    category_query = {"category": "Office"}
    category_rows = client.get(
        "/api/revenue/products", query_string=category_query
    ).get_json()["data"]
    combined_query = {
        "category": "Fitness",
        "end_date": "2026-03-31",
        "start_date": "2026-01-01",
    }
    combined_rows = client.get(
        "/api/rankings/products", query_string=combined_query
    ).get_json()["data"]
    summary = client.get(
        "/api/summary", query_string=combined_query
    ).get_json()["summary"]

    assert category_rows
    assert {row["category_name"] for row in category_rows} == {"Office"}
    assert combined_rows
    assert {row["category_name"] for row in combined_rows} == {"Fitness"}
    assert summary["completed_orders"] <= 45


@pytest.mark.parametrize(
    "query",
    [
        {"start_date": "06-01-2026"},
        {"end_date": "2026-13-01"},
        {"start_date": "2026-07-01", "end_date": "2026-06-30"},
        {"category": "Unknown Category"},
        {"category": "x" * 81},
        [("category", "Office"), ("category", "Fitness")],
        {"unsupported": "value"},
    ],
)
def test_invalid_filters_return_controlled_400(
    client: FlaskClient, query
) -> None:
    response = client.get("/api/summary", query_string=query)
    payload = response.get_json()
    response_text = response.get_data(as_text=True).lower()

    assert response.status_code == 400
    assert payload["error"]["code"] == "invalid_filter"
    assert "traceback" not in response_text
    assert "select " not in response_text


def test_valid_no_data_responses_are_empty_or_zero(client: FlaskClient) -> None:
    query = {"start_date": "2030-01-01", "end_date": "2030-01-31"}

    for path in (
        "/api/revenue/products",
        "/api/revenue/categories",
        "/api/margins/products",
        "/api/rankings/products",
    ):
        response = client.get(path, query_string=query)
        assert response.status_code == 200
        assert response.get_json()["data"] == []

    summary = client.get("/api/summary", query_string=query).get_json()
    assert summary["summary"] == {
        "active_products": 0,
        "completed_orders": 0,
        "gross_margin": 0.0,
        "order_lines_analyzed": 0,
        "recognized_revenue": 0.0,
    }
    assert all(value is None for value in summary["comparison"].values())


def test_invalid_trend_dates_return_controlled_400(
    client: FlaskClient,
) -> None:
    response = client.get(
        "/api/trends/monthly",
        query_string={
            "start_date": "2026-07-01",
            "end_date": "2026-06-30",
        },
    )
    response_text = response.get_data(as_text=True).lower()

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_filter"
    assert "traceback" not in response_text
    assert "select " not in response_text


def test_first_period_comparison_avoids_division_by_zero(
    client: FlaskClient,
) -> None:
    response = client.get(
        "/api/summary",
        query_string={
            "start_date": "2024-07-01",
            "end_date": "2024-07-31",
        },
    )

    assert response.status_code == 200
    assert all(value is None for value in response.get_json()["comparison"].values())


def test_summary_matches_independent_database_calculation(
    client: FlaskClient, database_path: Path
) -> None:
    with sqlite3.connect(database_path) as connection:
        direct = connection.execute(
            """
            SELECT
                SUM(
                    order_items.quantity * order_items.sale_price_cents
                ) / 100.0,
                SUM(
                    order_items.quantity
                    * (
                        order_items.sale_price_cents
                        - order_items.unit_cost_cents
                    )
                ) / 100.0,
                COUNT(DISTINCT orders.order_id),
                COUNT(
                    DISTINCT CASE
                        WHEN products.active = 1 THEN products.product_id
                    END
                ),
                COUNT(order_items.order_item_id)
            FROM orders
            JOIN order_items
                ON order_items.order_id = orders.order_id
            JOIN products
                ON products.product_id = order_items.product_id
            WHERE orders.order_status = 'COMPLETED'
            """
        ).fetchone()

    summary = client.get("/api/summary").get_json()["summary"]
    assert summary["recognized_revenue"] == pytest.approx(direct[0])
    assert summary["gross_margin"] == pytest.approx(direct[1])
    assert summary["completed_orders"] == direct[2]
    assert summary["active_products"] == direct[3]
    assert summary["order_lines_analyzed"] == direct[4]


def test_application_connections_are_read_only(app: Flask) -> None:
    with app.app_context(), pytest.raises(
        sqlite3.OperationalError, match="readonly"
    ):
        get_db().execute(
            """
            INSERT INTO categories (category_name)
            VALUES (?)
            """,
            ("Should Not Persist",),
        )


def test_dashboard_requests_do_not_change_database_checksum(
    client: FlaskClient, database_path: Path
) -> None:
    before = hashlib.sha256(database_path.read_bytes()).hexdigest()

    for path in (
        "/",
        "/health",
        "/api/meta",
        "/api/summary",
        "/api/revenue/products",
        "/api/revenue/categories",
        "/api/margins/products",
        "/api/rankings/products",
        "/api/trends/monthly",
    ):
        assert client.get(path).status_code == 200

    after = hashlib.sha256(database_path.read_bytes()).hexdigest()
    assert after == before


def test_security_headers_are_applied(client: FlaskClient) -> None:
    for path in ("/", "/api/summary", "/does-not-exist"):
        response = client.get(path)
        assert all(header in response.headers for header in SECURITY_HEADERS)
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "unsafe-inline" not in response.headers["Content-Security-Policy"]


def test_unknown_route_returns_404(client: FlaskClient) -> None:
    assert client.get("/does-not-exist").status_code == 404


@pytest.mark.parametrize("path", ["/api/summary", "/health"])
def test_database_failures_return_controlled_500(
    tmp_path: Path, path: str
) -> None:
    missing_database = tmp_path / "missing.db"
    application = create_app(
        {
            "DATABASE": missing_database,
            "TESTING": True,
        }
    )

    response = application.test_client().get(path)
    response_text = response.get_data(as_text=True).lower()

    assert response.status_code == 500
    assert "traceback" not in response_text
    assert "sqlite3" not in response_text
    assert str(missing_database).lower() not in response_text


def test_unexpected_api_failure_is_controlled(
    app: Flask,
) -> None:
    @app.get("/api/unexpected")
    def unexpected() -> None:
        raise RuntimeError("internal detail")

    app.config["PROPAGATE_EXCEPTIONS"] = False
    response = app.test_client().get("/api/unexpected")

    assert response.status_code == 500
    assert response.get_json() == {
        "error": {
            "code": "internal_error",
            "message": "Dashboard data is temporarily unavailable.",
        }
    }

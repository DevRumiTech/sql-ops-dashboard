"""HTTP, API contract, ordering, total, and failure-response tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from flask.testing import FlaskClient

from app import create_app


def test_application_creation(database_path: Path) -> None:
    application = create_app({"DATABASE": database_path, "TESTING": True})

    assert application.name == "app"
    assert application.config["DATABASE"] == database_path


def test_home_page_returns_200(client: FlaskClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert b"SQL Ops Dashboard" in response.data


def test_health_route_returns_database_status(client: FlaskClient) -> None:
    response = client.get("/health")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["database"] == "available"
    assert payload["table_count"] == 7


@pytest.mark.parametrize(
    ("path", "content_type"),
    [
        ("/static/styles.css", "text/css"),
        ("/static/app.js", "text/javascript"),
    ],
)
def test_static_assets_return_200(
    client: FlaskClient, path: str, content_type: str
) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.content_type.startswith(content_type)


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
                "product_id",
                "product_name",
                "revenue",
                "total_cost",
                "gross_margin",
                "gross_margin_rate",
            },
        ),
        (
            "/api/rankings/products",
            {"product_id", "product_name", "revenue", "revenue_rank"},
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


def test_summary_api_contract(client: FlaskClient) -> None:
    response = client.get("/api/summary")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["generated_data"] is True
    assert set(payload["summary"]) == {
        "active_products",
        "total_gross_margin",
        "total_revenue",
        "valid_orders",
    }
    assert all(
        isinstance(value, (int, float))
        for value in payload["summary"].values()
    )


def test_product_revenue_is_descending(client: FlaskClient) -> None:
    response = client.get("/api/revenue/products")
    revenues = [row["revenue"] for row in response.get_json()["data"]]

    assert revenues == sorted(revenues, reverse=True)


def test_summary_matches_direct_database_totals(
    client: FlaskClient, database_path: Path
) -> None:
    with sqlite3.connect(database_path) as connection:
        direct = connection.execute(
            """
            SELECT
                SUM(
                    order_items.quantity * order_items.sale_price_cents
                ) / 100.0 AS total_revenue,
                SUM(
                    order_items.quantity
                    * (
                        order_items.sale_price_cents
                        - products.cost_cents
                    )
                ) / 100.0 AS total_gross_margin,
                COUNT(DISTINCT orders.order_id) AS valid_orders,
                (
                    SELECT COUNT(*)
                    FROM products
                    WHERE active = 1
                ) AS active_products
            FROM orders
            JOIN order_items
                ON order_items.order_id = orders.order_id
            JOIN products
                ON products.product_id = order_items.product_id
            WHERE orders.order_status IN ('PAID', 'SHIPPED')
            """
        ).fetchone()

    summary = client.get("/api/summary").get_json()["summary"]
    assert summary["total_revenue"] == pytest.approx(direct[0])
    assert summary["total_gross_margin"] == pytest.approx(direct[1])
    assert summary["valid_orders"] == direct[2]
    assert summary["active_products"] == direct[3]


def test_unknown_route_returns_404(client: FlaskClient) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404


def test_database_failure_returns_controlled_500(tmp_path: Path) -> None:
    directory_instead_of_database = tmp_path / "not-a-database"
    directory_instead_of_database.mkdir()
    application = create_app(
        {
            "DATABASE": directory_instead_of_database,
            "TESTING": True,
        }
    )

    response = application.test_client().get("/api/summary")
    payload = response.get_json()
    response_text = response.get_data(as_text=True).lower()

    assert response.status_code == 500
    assert payload == {
        "error": {
            "code": "database_error",
            "message": "Dashboard data is temporarily unavailable.",
        }
    }
    assert "traceback" not in response_text
    assert "sqlite3" not in response_text

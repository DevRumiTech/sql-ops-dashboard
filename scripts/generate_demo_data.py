"""Generate the deterministic SQL Ops Dashboard demonstration database."""

from __future__ import annotations

import argparse
import calendar
import os
import random
import sqlite3
import sys
import tempfile
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "ops.db"
SQL_DIRECTORY = PROJECT_ROOT / "sql"
DEFAULT_SEED = 42
DEFAULT_ENDING_DATE = date(2026, 6, 30)
DEFAULT_MONTHS = 24
COMPLETED_ORDERS_PER_MONTH = 15
PENDING_ORDERS_PER_MONTH = 1
CANCELLED_ORDERS_PER_MONTH = 1


def parse_iso_date(value: str) -> date:
    """Parse one strict ISO calendar date for command-line arguments."""
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("dates must use YYYY-MM-DD") from error
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError("dates must use YYYY-MM-DD")
    return parsed


def first_month_date(ending_date: date, months: int) -> date:
    """Return the first day in an inclusive sequence of complete months."""
    if months < 1:
        raise ValueError("months must be at least 1")
    month_index = ending_date.year * 12 + ending_date.month - months
    return date(month_index // 12, month_index % 12 + 1, 1)


def month_starts(starting_date: date, months: int) -> list[date]:
    """Return consecutive month starts beginning with ``starting_date``."""
    result: list[date] = []
    month_index = starting_date.year * 12 + starting_date.month - 1
    for offset in range(months):
        current = month_index + offset
        result.append(date(current // 12, current % 12 + 1, 1))
    return result


def generate_demo_database(
    database_path: Path,
    *,
    seed: int = DEFAULT_SEED,
    ending_date: date = DEFAULT_ENDING_DATE,
    months: int = DEFAULT_MONTHS,
    sql_directory: Path = SQL_DIRECTORY,
) -> None:
    """Build, validate, and atomically replace a demonstration database."""
    expected_month_end = calendar.monthrange(
        ending_date.year, ending_date.month
    )[1]
    if ending_date.day != expected_month_end:
        raise ValueError("ending date must be the final day of a month")

    starting_date = first_month_date(ending_date, months)
    target = database_path.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)

    try:
        _build_database(
            temporary_path,
            seed=seed,
            starting_date=starting_date,
            ending_date=ending_date,
            months=months,
            sql_directory=sql_directory,
        )
        temporary_path.replace(target)
    except (OSError, sqlite3.Error, ValueError):
        temporary_path.unlink(missing_ok=True)
        raise


def _build_database(
    database_path: Path,
    *,
    seed: int,
    starting_date: date,
    ending_date: date,
    months: int,
    sql_directory: Path,
) -> None:
    """Populate one new database file and run integrity validation."""
    schema_sql = (sql_directory / "schema.sql").read_text(encoding="utf-8")
    seed_sql = (sql_directory / "seed.sql").read_text(encoding="utf-8")
    views_sql = (sql_directory / "views.sql").read_text(encoding="utf-8")

    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema_sql)
        connection.executescript(seed_sql)
        _insert_transactions(
            connection,
            random.Random(seed),
            starting_date,
            ending_date,
            months,
        )
        connection.executescript(views_sql)
        connection.execute("PRAGMA user_version = 1")
        connection.commit()
        _validate_database(connection)


def _insert_transactions(
    connection: sqlite3.Connection,
    generator: random.Random,
    starting_date: date,
    ending_date: date,
    months: int,
) -> None:
    """Insert deterministic completed, pending, and cancelled transactions."""
    products = connection.execute(
        """
        SELECT
            product_id,
            category_id,
            unit_cost_cents,
            list_price_cents,
            active
        FROM products
        ORDER BY product_id
        """
    ).fetchall()
    products_by_category = {
        category_id: [
            product
            for product in products
            if product["category_id"] == category_id
        ]
        for category_id in range(1, 6)
    }

    order_id = 1
    order_item_id = 1
    for month_offset, month_start in enumerate(
        month_starts(starting_date, months)
    ):
        statuses = (
            ["COMPLETED"] * COMPLETED_ORDERS_PER_MONTH
            + ["PENDING"] * PENDING_ORDERS_PER_MONTH
            + ["CANCELLED"] * CANCELLED_ORDERS_PER_MONTH
        )
        for status_index, status in enumerate(statuses):
            order_date = _order_date(
                generator,
                month_start,
                ending_date,
                month_offset,
                months,
                status_index,
                status,
            )
            channel = generator.choices(
                ["ONLINE", "STORE", "PARTNER"],
                weights=[58, 31, 11],
                k=1,
            )[0]
            connection.execute(
                """
                INSERT INTO orders (
                    order_id,
                    order_date,
                    order_status,
                    sales_channel
                )
                VALUES (?, ?, ?, ?)
                """,
                (order_id, order_date.isoformat(), status, channel),
            )

            item_count = generator.choices(
                [1, 2, 3, 4],
                weights=[22, 42, 26, 10],
                k=1,
            )[0]
            forced_category = (
                status_index + 1
                if status == "COMPLETED" and status_index < 5
                else None
            )
            selected_products = _select_products(
                generator,
                products,
                products_by_category,
                month_start.month,
                item_count,
                forced_category,
            )
            for product in selected_products:
                quantity = _quantity(generator, month_start.month)
                sale_price = _sale_price(
                    generator,
                    product["list_price_cents"],
                    product["unit_cost_cents"],
                    month_start.month,
                )
                connection.execute(
                    """
                    INSERT INTO order_items (
                        order_item_id,
                        order_id,
                        product_id,
                        quantity,
                        sale_price_cents,
                        unit_cost_cents
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_item_id,
                        order_id,
                        product["product_id"],
                        quantity,
                        sale_price,
                        product["unit_cost_cents"],
                    ),
                )
                order_item_id += 1
            order_id += 1


def _order_date(
    generator: random.Random,
    month_start: date,
    ending_date: date,
    month_offset: int,
    months: int,
    status_index: int,
    status: str,
) -> date:
    """Choose an order date while fixing the overall completed-date bounds."""
    if month_offset == 0 and status == "COMPLETED" and status_index == 0:
        return month_start
    if (
        month_offset == months - 1
        and status == "COMPLETED"
        and status_index == COMPLETED_ORDERS_PER_MONTH - 1
    ):
        return ending_date
    last_day = calendar.monthrange(month_start.year, month_start.month)[1]
    return month_start.replace(day=generator.randint(1, last_day))


def _select_products(
    generator: random.Random,
    products: list[sqlite3.Row],
    products_by_category: dict[int, list[sqlite3.Row]],
    month: int,
    item_count: int,
    forced_category: int | None,
) -> list[sqlite3.Row]:
    """Select distinct products with stable seasonal weighting."""
    selected: list[sqlite3.Row] = []
    if forced_category is not None:
        selected.append(generator.choice(products_by_category[forced_category]))

    while len(selected) < item_count:
        candidates = [
            product
            for product in products
            if product["product_id"]
            not in {selected_product["product_id"] for selected_product in selected}
        ]
        weights = [_product_weight(product, month) for product in candidates]
        selected.append(generator.choices(candidates, weights=weights, k=1)[0])
    return selected


def _product_weight(product: sqlite3.Row, month: int) -> float:
    """Return a plausible category and season-sensitive selection weight."""
    category_id = int(product["category_id"])
    weight = 1.0 + (int(product["product_id"]) % 4) * 0.08
    if not product["active"]:
        weight *= 0.35
    if month in {11, 12} and category_id in {4, 5}:
        weight *= 1.55
    if month in {1, 2} and category_id == 3:
        weight *= 1.45
    if month in {8, 9} and category_id == 1:
        weight *= 1.35
    if month in {4, 5} and category_id == 2:
        weight *= 1.22
    return weight


def _quantity(generator: random.Random, month: int) -> int:
    """Generate realistic low unit quantities with modest holiday uplift."""
    weights = [67, 25, 8] if month not in {11, 12} else [54, 32, 14]
    return generator.choices([1, 2, 3], weights=weights, k=1)[0]


def _sale_price(
    generator: random.Random,
    list_price_cents: int,
    unit_cost_cents: int,
    month: int,
) -> int:
    """Apply deterministic, varied discounts without selling below cost."""
    discounts = [0, 250, 400, 600, 800, 1000]
    weights = (
        [20, 17, 20, 19, 15, 9]
        if month not in {11, 12}
        else [9, 12, 17, 21, 23, 18]
    )
    discount_basis_points = generator.choices(
        discounts, weights=weights, k=1
    )[0]
    discounted = round(
        list_price_cents * (10_000 - discount_basis_points) / 10_000
    )
    return max(unit_cost_cents, discounted)


def _validate_database(connection: sqlite3.Connection) -> None:
    """Raise when SQLite integrity or relationship validation fails."""
    foreign_key_issues = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()
    if foreign_key_issues:
        raise sqlite3.IntegrityError(
            "Foreign-key validation failed during generation"
        )
    integrity_result = connection.execute("PRAGMA integrity_check").fetchone()
    if integrity_result is None or integrity_result[0] != "ok":
        raise sqlite3.DatabaseError(
            "SQLite integrity check failed during generation"
        )


def _parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the deterministic SQL Ops Dashboard demonstration data."
        )
    )
    parser.add_argument(
        "database",
        nargs="?",
        type=Path,
        default=DEFAULT_DATABASE,
        help="Optional output database path (default: data/ops.db)",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--ending-date",
        type=parse_iso_date,
        default=DEFAULT_ENDING_DATE,
        help="Final day of the generated period in YYYY-MM-DD format",
    )
    parser.add_argument("--months", type=int, default=DEFAULT_MONTHS)
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """Generate the requested database and return a process exit status."""
    args = _parse_args(arguments)
    try:
        generate_demo_database(
            args.database,
            seed=args.seed,
            ending_date=args.ending_date,
            months=args.months,
        )
    except (OSError, sqlite3.Error, ValueError) as error:
        print(f"Database generation failed: {error}", file=sys.stderr)
        return 1

    print(
        "SQL Ops Dashboard demonstration database generated at "
        f"{args.database.expanduser().resolve()} "
        f"(seed={args.seed}, ending_date={args.ending_date}, months={args.months})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

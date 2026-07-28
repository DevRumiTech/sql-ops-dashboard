"""Initialize SQL Ops Dashboard data through the deterministic generator."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path
from typing import Sequence

if __package__:
    from .generate_demo_data import (
        DEFAULT_DATABASE,
        DEFAULT_ENDING_DATE,
        DEFAULT_MONTHS,
        DEFAULT_SEED,
        generate_demo_database,
        parse_iso_date,
    )
else:
    from generate_demo_data import (  # type: ignore[no-redef]
        DEFAULT_DATABASE,
        DEFAULT_ENDING_DATE,
        DEFAULT_MONTHS,
        DEFAULT_SEED,
        generate_demo_database,
        parse_iso_date,
    )


def initialize_database(
    database_path: Path,
    *,
    seed: int = DEFAULT_SEED,
    ending_date: date = DEFAULT_ENDING_DATE,
    months: int = DEFAULT_MONTHS,
) -> None:
    """Build a validated database without maintaining a second seed system."""
    generate_demo_database(
        database_path,
        seed=seed,
        ending_date=ending_date,
        months=months,
    )


def _parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild the SQL Ops Dashboard database from SQL reference data "
            "and deterministic generated transactions."
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
    )
    parser.add_argument("--months", type=int, default=DEFAULT_MONTHS)
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run database initialization and return a process exit status."""
    args = _parse_args(arguments)
    try:
        initialize_database(
            args.database,
            seed=args.seed,
            ending_date=args.ending_date,
            months=args.months,
        )
    except (OSError, sqlite3.Error, ValueError) as error:
        print(f"Database initialization failed: {error}", file=sys.stderr)
        return 1

    print(
        "SQL Ops Dashboard database initialized successfully at "
        f"{args.database.expanduser().resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

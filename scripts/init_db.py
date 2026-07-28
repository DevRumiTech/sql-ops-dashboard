"""Rebuild a SQL Ops Dashboard SQLite database from versioned SQL files."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "ops.db"
SQL_DIRECTORY = PROJECT_ROOT / "sql"
SQL_FILES = ("schema.sql", "seed.sql", "views.sql")


def initialize_database(
    database_path: Path, sql_directory: Path = SQL_DIRECTORY
) -> None:
    """Build a validated database and atomically replace the target file."""
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
        with closing(sqlite3.connect(temporary_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")

            for sql_file in SQL_FILES:
                script_path = sql_directory / sql_file
                connection.executescript(script_path.read_text(encoding="utf-8"))

            foreign_key_issues = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
            if foreign_key_issues:
                raise sqlite3.IntegrityError(
                    "Foreign-key validation failed during initialization"
                )

            integrity_result = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()
            if integrity_result is None or integrity_result[0] != "ok":
                raise sqlite3.DatabaseError(
                    "SQLite integrity check failed during initialization"
                )

        temporary_path.replace(target)
    except (OSError, sqlite3.Error):
        temporary_path.unlink(missing_ok=True)
        raise


def _parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild the SQL Ops Dashboard database from schema, seed, "
            "and view SQL files."
        )
    )
    parser.add_argument(
        "database",
        nargs="?",
        type=Path,
        default=DEFAULT_DATABASE,
        help="Optional output database path (default: data/ops.db)",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run database initialization and return a process exit status."""
    args = _parse_args(arguments)

    try:
        initialize_database(args.database)
    except (OSError, sqlite3.Error) as error:
        print(f"Database initialization failed: {error}", file=sys.stderr)
        return 1

    print(
        "SQL Ops Dashboard database initialized successfully at "
        f"{args.database.expanduser().resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

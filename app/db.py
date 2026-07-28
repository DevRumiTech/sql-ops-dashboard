"""SQLite connection and query helpers used across the application."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Iterable

from flask import Flask, current_app, g


def _database_path() -> Path:
    """Return the database path from the active Flask configuration."""
    return Path(current_app.config["DATABASE"])


def get_db() -> sqlite3.Connection:
    """Open one configured SQLite connection for the current request."""
    if "db" not in g:
        connection = sqlite3.connect(_database_path())
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection

    return g.db


def close_db(_error: BaseException | None = None) -> None:
    """Close the request-scoped SQLite connection, when present."""
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def query_all(
    statement: str, parameters: Iterable[Any] = ()
) -> list[dict[str, Any]]:
    """Execute a read query and return every row as a dictionary."""
    with closing(get_db().execute(statement, tuple(parameters))) as cursor:
        return [dict(row) for row in cursor.fetchall()]


def query_one(
    statement: str, parameters: Iterable[Any] = ()
) -> dict[str, Any] | None:
    """Execute a read query and return one row as a dictionary."""
    with closing(get_db().execute(statement, tuple(parameters))) as cursor:
        row = cursor.fetchone()
    return dict(row) if row is not None else None


def init_app(app: Flask) -> None:
    """Attach database cleanup to a Flask application."""
    app.teardown_appcontext(close_db)

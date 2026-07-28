"""Application factory for the SQL Ops Dashboard."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Mapping

from flask import Flask, jsonify, request

from . import db

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "ops.db"


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    """Create and configure a SQL Ops Dashboard Flask application."""
    app = Flask(__name__)
    app.config.from_mapping(DATABASE=DEFAULT_DATABASE)

    if test_config:
        app.config.update(test_config)

    app.config["DATABASE"] = Path(app.config["DATABASE"])
    db.init_app(app)

    from .routes import dashboard

    app.register_blueprint(dashboard)
    _register_error_handlers(app)
    app.logger.info("SQL Ops Dashboard application configured")
    return app


def _register_error_handlers(app: Flask) -> None:
    """Register controlled responses for database failures."""

    @app.errorhandler(sqlite3.Error)
    def handle_database_error(error: sqlite3.Error):
        app.logger.error("SQLite database operation failed", exc_info=error)

        if request.path == "/health":
            return (
                jsonify(
                    {
                        "application": "SQL Ops Dashboard",
                        "database": "unavailable",
                        "error": "Database unavailable.",
                        "status": "error",
                    }
                ),
                500,
            )

        return (
            jsonify(
                {
                    "error": {
                        "code": "database_error",
                        "message": "Dashboard data is temporarily unavailable.",
                    }
                }
            ),
            500,
        )

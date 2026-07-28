"""Application factory for the SQL Ops Dashboard."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Mapping

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import InternalServerError

from . import db
from .filters import FilterValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "ops.db"
PUBLIC_DIRECTORY = PROJECT_ROOT / "public"


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    """Create and configure the read-only dashboard application."""
    application = Flask(
        __name__,
        static_folder=str(PUBLIC_DIRECTORY),
        static_url_path="",
    )
    application.config.from_mapping(DATABASE=DEFAULT_DATABASE)
    if test_config:
        application.config.update(test_config)
    application.config["DATABASE"] = Path(application.config["DATABASE"])

    db.init_app(application)
    from .routes import dashboard

    application.register_blueprint(dashboard)
    _register_error_handlers(application)
    _register_security_headers(application)
    application.logger.info("SQL Ops Dashboard application configured")
    return application


def _register_error_handlers(application: Flask) -> None:
    """Register controlled validation and database error responses."""

    @application.errorhandler(FilterValidationError)
    def handle_filter_error(error: FilterValidationError) -> tuple[Response, int]:
        return (
            jsonify(
                {
                    "error": {
                        "code": "invalid_filter",
                        "message": str(error),
                    }
                }
            ),
            400,
        )

    @application.errorhandler(sqlite3.Error)
    def handle_database_error(error: sqlite3.Error) -> tuple[Response, int]:
        application.logger.error(
            "SQLite dashboard query failed", exc_info=error
        )
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

    @application.errorhandler(InternalServerError)
    def handle_internal_error(
        _error: InternalServerError,
    ) -> tuple[Response, int]:
        if request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "error": {
                            "code": "internal_error",
                            "message": (
                                "Dashboard data is temporarily unavailable."
                            ),
                        }
                    }
                ),
                500,
            )
        return jsonify({"error": "Application unavailable."}), 500


def _register_security_headers(application: Flask) -> None:
    """Apply conservative headers without requiring inline browser code."""

    @application.after_request
    def add_security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = (
            "camera=(), geolocation=(), microphone=(), payment=(), usb=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "base-uri 'self'; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "img-src 'self' data:; "
            "object-src 'none'; "
            "script-src 'self'; "
            "style-src 'self'"
        )
        return response

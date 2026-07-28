"""Local entry point for the SQL Ops Dashboard."""

from __future__ import annotations

import os

from app import create_app

app = create_app()


def _environment_flag(name: str, default: bool = False) -> bool:
    """Read a conventional true/false environment flag."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    app.logger.setLevel("INFO")
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = _environment_flag("FLASK_DEBUG")
    app.logger.info("Starting SQL Ops Dashboard on %s:%s", host, port)
    app.run(host=host, port=port, debug=debug)

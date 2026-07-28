"""Shared pytest fixtures using an isolated temporary SQLite database."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from scripts.init_db import initialize_database


@pytest.fixture()
def database_path(tmp_path: Path) -> Path:
    """Create a complete database without touching data/ops.db."""
    path = tmp_path / "ops-test.db"
    initialize_database(path)
    return path


@pytest.fixture()
def app(database_path: Path) -> Iterator[Flask]:
    """Create an application configured for the temporary database."""
    application = create_app(
        {
            "DATABASE": database_path,
            "TESTING": True,
        }
    )
    yield application


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """Return Flask's HTTP test client."""
    return app.test_client()

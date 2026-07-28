"""Command helper and failure-path tests for database generation scripts."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pytest

from scripts import generate_demo_data, init_db


def test_generation_date_helpers() -> None:
    ending_date = generate_demo_data.parse_iso_date("2026-06-30")

    assert ending_date == date(2026, 6, 30)
    assert generate_demo_data.first_month_date(ending_date, 24) == date(
        2024, 7, 1
    )
    assert generate_demo_data.month_starts(date(2025, 12, 1), 3) == [
        date(2025, 12, 1),
        date(2026, 1, 1),
        date(2026, 2, 1),
    ]


def test_invalid_generation_arguments_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        generate_demo_data.parse_iso_date("30-06-2026")
    with pytest.raises(ValueError, match="months"):
        generate_demo_data.first_month_date(date(2026, 6, 30), 0)
    with pytest.raises(ValueError, match="final day"):
        generate_demo_data.generate_demo_database(
            tmp_path / "invalid.db",
            ending_date=date(2026, 6, 29),
        )


def test_generation_cleans_up_after_missing_sql_files(tmp_path: Path) -> None:
    target = tmp_path / "generated.db"
    missing_sql_directory = tmp_path / "missing-sql"

    with pytest.raises(OSError):
        generate_demo_data.generate_demo_database(
            target,
            sql_directory=missing_sql_directory,
        )

    assert not target.exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_generator_and_initializer_main_success(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    generated = tmp_path / "generated.db"
    initialized = tmp_path / "initialized.db"

    assert generate_demo_data.main([str(generated), "--months", "2"]) == 0
    assert init_db.main([str(initialized), "--months", "2"]) == 0

    output = capsys.readouterr().out
    assert "demonstration database generated" in output
    assert "database initialized successfully" in output
    assert generated.is_file()
    assert initialized.is_file()


def test_generator_and_initializer_main_failures(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    invalid_date = "2026-06-29"

    assert (
        generate_demo_data.main(
            [str(tmp_path / "bad-generate.db"), "--ending-date", invalid_date]
        )
        == 1
    )
    assert (
        init_db.main(
            [str(tmp_path / "bad-init.db"), "--ending-date", invalid_date]
        )
        == 1
    )

    errors = capsys.readouterr().err
    assert "Database generation failed" in errors
    assert "Database initialization failed" in errors

"""Validated analytics filters shared by dashboard API routes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from flask import request

from .db import query_one

ALLOWED_FILTERS = {"start_date", "end_date", "category"}
MAX_FILTER_LENGTH = 80


class FilterValidationError(ValueError):
    """Raised when an analytics query parameter is invalid."""


@dataclass(frozen=True)
class AnalyticsFilters:
    """One validated set of optional dashboard filters."""

    start_date: date | None = None
    end_date: date | None = None
    category: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        """Return JSON-safe filter values."""
        return {
            "category": self.category,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "start_date": (
                self.start_date.isoformat() if self.start_date else None
            ),
        }

    def previous_period(self) -> AnalyticsFilters | None:
        """Return the immediately preceding period of equal inclusive length."""
        if self.start_date is None or self.end_date is None:
            return None
        duration = self.end_date - self.start_date + timedelta(days=1)
        previous_end = self.start_date - timedelta(days=1)
        return AnalyticsFilters(
            start_date=previous_end - duration + timedelta(days=1),
            end_date=previous_end,
            category=self.category,
        )


def parse_analytics_filters() -> AnalyticsFilters:
    """Validate supported request parameters without building SQL from values."""
    unexpected = set(request.args) - ALLOWED_FILTERS
    if unexpected:
        raise FilterValidationError("Unsupported analytics filter.")

    raw_values: dict[str, str | None] = {}
    for name in ALLOWED_FILTERS:
        values = request.args.getlist(name)
        if len(values) > 1:
            raise FilterValidationError(f"{name} may be supplied only once.")
        value = values[0].strip() if values else None
        if value and len(value) > MAX_FILTER_LENGTH:
            raise FilterValidationError(f"{name} is too long.")
        raw_values[name] = value or None

    start_date = _parse_date(raw_values["start_date"], "start_date")
    end_date = _parse_date(raw_values["end_date"], "end_date")
    if start_date and end_date and start_date > end_date:
        raise FilterValidationError(
            "start_date must be on or before end_date."
        )

    category = raw_values["category"]
    if category and not _category_exists(category):
        raise FilterValidationError("Unknown category.")

    return AnalyticsFilters(start_date, end_date, category)


def line_filter_sql(
    filters: AnalyticsFilters,
) -> tuple[str, tuple[Any, ...]]:
    """Build a fixed-column WHERE clause and parameter tuple."""
    conditions: list[str] = []
    parameters: list[Any] = []
    if filters.start_date:
        conditions.append("line.order_date >= ?")
        parameters.append(filters.start_date.isoformat())
    if filters.end_date:
        conditions.append("line.order_date <= ?")
        parameters.append(filters.end_date.isoformat())
    if filters.category:
        conditions.append("line.category_name = ?")
        parameters.append(filters.category)
    where_clause = (
        "WHERE " + " AND ".join(conditions) if conditions else ""
    )
    return where_clause, tuple(parameters)


def _parse_date(value: str | None, name: str) -> date | None:
    if value is None:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise FilterValidationError(
            f"{name} must use YYYY-MM-DD."
        ) from error
    if parsed.isoformat() != value:
        raise FilterValidationError(f"{name} must use YYYY-MM-DD.")
    return parsed


def _category_exists(category: str) -> bool:
    result = query_one(
        """
        SELECT 1 AS category_exists
        FROM categories
        WHERE category_name = ?
        """,
        (category,),
    )
    return result is not None

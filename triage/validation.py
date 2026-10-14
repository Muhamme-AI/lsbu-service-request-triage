"""Checks that required information is present and well-formed."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime
from typing import Any, Iterable

from .models import FIELD_ATTRIBUTES, Request, ValidationIssue


def parse_date(value: str, formats: Iterable[str]) -> date | None:
    """Parse a date using the configured formats (UK day-first by default)."""
    value = (value or "").strip()
    if not value:
        return None
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def canonical_value(value: str, allowed: Iterable[str]) -> str | None:
    """Return the allowed value matching ``value`` case-insensitively, if any."""
    folded = (value or "").strip().casefold()
    for option in allowed:
        if option.casefold() == folded:
            return option
    return None


def validate(request: Request, rules: dict[str, Any], as_of: date) -> list[ValidationIssue]:
    cfg = rules["validation"]
    issues: list[ValidationIssue] = []

    for label in cfg["required_fields"]:
        attr = FIELD_ATTRIBUTES.get(label)
        if attr is None:
            continue
        if not getattr(request, attr, "").strip():
            issues.append(ValidationIssue(label, "missing", f"{label} is required but empty"))

    if request.request_id:
        pattern = cfg.get("request_id_pattern")
        if pattern and not re.match(pattern, request.request_id):
            issues.append(
                ValidationIssue(
                    "Request ID", "invalid", f"Request ID '{request.request_id}' does not match the expected format (e.g. REQ-001)"
                )
            )

    if request.submitted_date:
        parsed = parse_date(request.submitted_date, cfg["date_formats"])
        if parsed is None:
            issues.append(
                ValidationIssue(
                    "Submitted Date", "invalid", f"Submitted Date '{request.submitted_date}' is not a valid date (expected DD/MM/YYYY)"
                )
            )
        elif parsed > as_of and not cfg.get("allow_future_dates", False):
            issues.append(
                ValidationIssue(
                    "Submitted Date", "invalid", f"Submitted Date {parsed.isoformat()} is after the assessment date {as_of.isoformat()}"
                )
            )

    minimum = int(cfg.get("minimum_summary_length", 0))
    if request.request_summary and len(request.request_summary) < minimum:
        issues.append(
            ValidationIssue(
                "Request Summary", "invalid", f"Request Summary is too short to act on ({len(request.request_summary)} characters; minimum {minimum})"
            )
        )

    for label, attr, key in (
        ("Priority", "priority", "allowed_priorities"),
        ("Channel", "channel", "allowed_channels"),
        ("Status", "status", "allowed_statuses"),
    ):
        value = getattr(request, attr)
        allowed = cfg.get(key, [])
        if value and allowed and canonical_value(value, allowed) is None:
            issues.append(
                ValidationIssue(label, "invalid", f"{label} '{value}' is not one of: {', '.join(allowed)}")
            )

    return issues


def find_duplicate_ids(requests: Iterable[Request]) -> set[str]:
    counts = Counter(r.request_id for r in requests if r.request_id)
    return {request_id for request_id, count in counts.items() if count > 1}
